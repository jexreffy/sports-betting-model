from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from sbm.backtest import walk_forward
from sbm.config import CFB_PARAMS, NFL_PARAMS, RESEARCH_WINDOWS, LeagueParams, Settings
from sbm.errors import prediction_errors
from sbm.mode import Mode
from sbm.odds import settle_pick
from sbm.schema import Game, League


class TuneCandidate(BaseModel):
    spread_edge_points: float
    nfl_k: float
    search_units: float
    search_mae_margin: float | None
    holdout_units: float | None = None
    holdout_mae_margin: float | None = None


class TuneReport(BaseModel):
    search_seasons: tuple[int, int]
    holdout_seasons: tuple[int, int]
    chosen: TuneCandidate
    candidates: list[TuneCandidate] = Field(default_factory=list)


def _copy_params(params: LeagueParams, k: float) -> LeagueParams:
    return LeagueParams(
        hfa_points=params.hfa_points,
        elo_per_point=params.elo_per_point,
        k=k,
        revert=params.revert,
        base_elo=params.base_elo,
        margin_sigma=params.margin_sigma,
        total_sigma=params.total_sigma,
        league_avg_total=params.league_avg_total,
        min_week_to_score=params.min_week_to_score,
        rest_points_per_day=params.rest_points_per_day,
        rest_cap=params.rest_cap,
        off_k=params.off_k,
        def_k=params.def_k,
    )


def _paper_units(
    games: list[Game],
    *,
    start: int,
    end: int,
    settings: Settings,
    params_by_league: dict[League, LeagueParams],
) -> float:
    picks, _ = walk_forward(
        games,
        mode=Mode.SIMULATION,
        start_season=start,
        end_season=end,
        settings=settings,
        params_by_league=params_by_league,
    )
    by_id = {g.game_id: g for g in games}
    units = 0.0
    for pick in picks:
        if pick.season < start or pick.season > end:
            continue
        game = by_id.get(pick.game_id)
        if game is None or not game.is_final:
            continue
        _, profit = settle_pick(pick, game)
        units += profit
    return round(units, 3)


def _mae_margin(rows: list) -> float | None:
    vals = [r.margin_vs_final for r in rows if r.margin_vs_final is not None]
    if not vals:
        return None
    return round(sum(abs(v) for v in vals) / len(vals), 4)


def tune(
    games: list[Game],
    *,
    edge_grid: tuple[float, ...] = (1.5, 2.0),
    k_grid: tuple[float, ...] = (16.0, 20.0, 24.0),
) -> TuneReport:
    split = RESEARCH_WINDOWS
    if split.hands_off <= split.search_end:
        raise ValueError("Refusing to fit on the hands-off season")
    search_start, search_end = split.search_start, split.search_end
    holdout_start, holdout_end = split.holdout_start, split.holdout_end

    candidates: list[TuneCandidate] = []
    for edge in edge_grid:
        for k in k_grid:
            settings = Settings(spread_edge_points=edge, total_edge_points=edge)
            params = {
                League.NFL: _copy_params(NFL_PARAMS, k),
                League.CFB: _copy_params(CFB_PARAMS, k),
            }
            search_rows = prediction_errors(
                games,
                start_season=search_start,
                end_season=search_end,
                params_by_league=params,
            )
            if any(row.season == split.hands_off for row in search_rows):
                raise ValueError("Tune search included the hands-off season")
            search_units = _paper_units(
                games,
                start=search_start,
                end=search_end,
                settings=settings,
                params_by_league=params,
            )
            holdout_rows = prediction_errors(
                games,
                start_season=holdout_start,
                end_season=holdout_end,
                params_by_league=params,
            )
            holdout_units = _paper_units(
                games,
                start=holdout_start,
                end=holdout_end,
                settings=settings,
                params_by_league=params,
            )
            candidates.append(
                TuneCandidate(
                    spread_edge_points=edge,
                    nfl_k=k,
                    search_units=search_units,
                    search_mae_margin=_mae_margin(search_rows),
                    holdout_units=holdout_units,
                    holdout_mae_margin=_mae_margin(holdout_rows),
                )
            )

    def _key(c: TuneCandidate) -> tuple[float, float]:
        mae = c.search_mae_margin if c.search_mae_margin is not None else 1e9
        return (mae, -c.search_units)

    chosen = min(candidates, key=_key)
    return TuneReport(
        search_seasons=(search_start, search_end),
        holdout_seasons=(holdout_start, holdout_end),
        chosen=chosen,
        candidates=candidates,
    )


def write_tune_report(report: TuneReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path
