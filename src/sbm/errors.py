from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from sbm.backtest import current_slate
from sbm.config import LeagueParams
from sbm.mode import Mode
from sbm.schema import Game, League, Prediction


class GameErrorRow(BaseModel):
    game_id: str
    league: League
    season: int
    week: int
    predicted_home_margin: float
    predicted_total: float
    close_home_margin: float | None = None
    final_home_margin: float | None = None
    close_total: float | None = None
    final_total: float | None = None
    margin_vs_close: float | None = None
    margin_vs_final: float | None = None
    total_vs_close: float | None = None
    total_vs_final: float | None = None


class LeagueBias(BaseModel):
    league: League
    n: int = 0
    mean_margin_vs_close: float | None = None
    mae_margin_vs_close: float | None = None
    mean_margin_vs_final: float | None = None
    mae_margin_vs_final: float | None = None
    mean_total_vs_close: float | None = None
    mae_total_vs_close: float | None = None
    mean_total_vs_final: float | None = None
    mae_total_vs_final: float | None = None


class WeekErrorReport(BaseModel):
    season: int
    week: int
    n_games: int = 0
    games: list[GameErrorRow] = Field(default_factory=list)
    by_league: list[LeagueBias] = Field(default_factory=list)


def row_from_prediction(game: Game, pred: Prediction) -> GameErrorRow:
    close_home = None if game.spread_close is None else -game.spread_close
    margin_vs_close = (
        None if close_home is None else round(pred.predicted_home_margin - close_home, 4)
    )
    margin_vs_final = (
        None
        if game.home_margin is None
        else round(pred.predicted_home_margin - game.home_margin, 4)
    )
    total_vs_close = (
        None
        if game.total_close is None
        else round(pred.predicted_total - game.total_close, 4)
    )
    total_vs_final = (
        None
        if game.total_points is None
        else round(pred.predicted_total - game.total_points, 4)
    )
    return GameErrorRow(
        game_id=game.game_id,
        league=game.league,
        season=game.season,
        week=game.week,
        predicted_home_margin=round(pred.predicted_home_margin, 4),
        predicted_total=round(pred.predicted_total, 4),
        close_home_margin=close_home,
        final_home_margin=game.home_margin,
        close_total=game.total_close,
        final_total=game.total_points,
        margin_vs_close=margin_vs_close,
        margin_vs_final=margin_vs_final,
        total_vs_close=total_vs_close,
        total_vs_final=total_vs_final,
    )


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _mae(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(abs(v) for v in values) / len(values), 4)


def bias_by_league(rows: list[GameErrorRow]) -> list[LeagueBias]:
    grouped: dict[League, list[GameErrorRow]] = defaultdict(list)
    for row in rows:
        grouped[row.league].append(row)
    out: list[LeagueBias] = []
    for league, group in sorted(grouped.items(), key=lambda item: item[0].value):
        out.append(
            LeagueBias(
                league=league,
                n=len(group),
                mean_margin_vs_close=_mean(
                    [r.margin_vs_close for r in group if r.margin_vs_close is not None]
                ),
                mae_margin_vs_close=_mae(
                    [r.margin_vs_close for r in group if r.margin_vs_close is not None]
                ),
                mean_margin_vs_final=_mean(
                    [r.margin_vs_final for r in group if r.margin_vs_final is not None]
                ),
                mae_margin_vs_final=_mae(
                    [r.margin_vs_final for r in group if r.margin_vs_final is not None]
                ),
                mean_total_vs_close=_mean(
                    [r.total_vs_close for r in group if r.total_vs_close is not None]
                ),
                mae_total_vs_close=_mae(
                    [r.total_vs_close for r in group if r.total_vs_close is not None]
                ),
                mean_total_vs_final=_mean(
                    [r.total_vs_final for r in group if r.total_vs_final is not None]
                ),
                mae_total_vs_final=_mae(
                    [r.total_vs_final for r in group if r.total_vs_final is not None]
                ),
            )
        )
    return out


def week_error_report(
    games: list[Game],
    *,
    season: int,
    week: int,
    mode: Mode = Mode.SIMULATION,
    league: League | None = None,
) -> WeekErrorReport:
    slate, _, _ = current_slate(
        games, mode=mode, season=season, week=week, league=league
    )
    rows = [row_from_prediction(game, pred) for game, pred in slate]
    return WeekErrorReport(
        season=season,
        week=week,
        n_games=len(rows),
        games=rows,
        by_league=bias_by_league(rows),
    )


def prediction_errors(
    games: list[Game],
    *,
    start_season: int,
    end_season: int,
    params_by_league: dict[League, LeagueParams] | None = None,
) -> list[GameErrorRow]:
    """Walk-forward prediction errors. Does not read any ledger."""
    from sbm.config import RESEARCH_WINDOWS
    from sbm.models.engine import ModelEngine

    split = RESEARCH_WINDOWS
    ordered = sorted(
        games,
        key=lambda g: (g.season, g.week, g.kickoff.isoformat() if g.kickoff else "", g.game_id),
    )
    engines: dict[League, ModelEngine] = {}
    rows: list[GameErrorRow] = []
    for game in ordered:
        window = split.window_for(game.season)
        if window is None:
            continue
        extra = (params_by_league or {}).get(game.league)
        engine = engines.setdefault(game.league, ModelEngine(game.league, params=extra))
        if game.season < start_season:
            if game.is_final:
                engine.update(game)
            continue
        if game.season > end_season:
            continue
        if not split.record_historical_picks(game.season):
            if game.is_final:
                engine.update(game)
            continue
        pred = engine.predict(game)
        rows.append(row_from_prediction(game, pred))
        if game.is_final:
            engine.update(game)
    return rows
