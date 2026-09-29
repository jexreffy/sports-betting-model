from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from sbm.backtest import current_slate
from sbm.config import LeagueParams, get_settings, params_for
from sbm.mode import Mode
from sbm.schema import Game, League, Prediction
from sbm.units import UnitBook

CALM_CLOSE_MAE = 2.0


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


def _fmt_points(value: float) -> str:
    text = f"{abs(value):.1f}"
    return text[:-2] if text.endswith(".0") else text


def _close_voice(mae: float | None, noisy: float) -> str:
    if mae is None:
        return "had no close to compare"
    if mae <= CALM_CLOSE_MAE:
        return "sat on the close"
    if mae >= noisy:
        return "was wild versus the close"
    return "was off the close"


def _home_lean(mean: float | None) -> str | None:
    if mean is None or abs(mean) < 0.45:
        return None
    side = "home team" if mean > 0 else "away side"
    return f"about {_fmt_points(mean)} points more toward the {side} than the market"


def _side_margin(value: float) -> str:
    if abs(value) < 0.05:
        return "a pick'em"
    if value > 0:
        return f"the home team {_fmt_points(value)} points better"
    return f"the away team {_fmt_points(value)} points better"


def early_season_leagues(rows: list[GameErrorRow]) -> set[League]:
    """Leagues whose finished games are all still inside the paper week gate."""
    weeks: dict[League, list[int]] = defaultdict(list)
    for row in rows:
        weeks[row.league].append(row.week)
    return {
        league
        for league, values in weeks.items()
        if values and all(week < params_for(league).min_week_to_score for week in values)
    }


def explain_league_bias(
    bias: LeagueBias,
    *,
    early_season: bool = False,
    prior: LeagueBias | None = None,
) -> list[str]:
    """English for one league's week. Numbers stay out of the lead clause."""
    noisy = get_settings().noisy_edge_points
    label = bias.league.value.upper()
    noun = "game" if bias.n == 1 else "games"
    voice = _close_voice(bias.mae_margin_vs_close, noisy)
    lean = _home_lean(bias.mean_margin_vs_close)
    typical = (
        f"typical miss {_fmt_points(bias.mae_margin_vs_close)}"
        if bias.mae_margin_vs_close is not None
        else None
    )
    lead = f"On {bias.n} {label} {noun}, the model {voice} for the spread"
    extras = [bit for bit in (lean, typical) if bit]
    if extras:
        lead += f" ({'; '.join(extras)})"
    sentences = [f"{lead}."]
    if early_season and bias.league == League.CFB:
        sentences.append(
            "That is expected in weeks 1–3. Do not treat a CFB card like an NFL one "
            "until that window is over."
        )
    elif voice == "sat on the close" and bias.league == League.NFL:
        sentences.append("Treat this week's NFL cards as the reliable slate.")
    if bias.mae_margin_vs_final is not None:
        bounce = _fmt_points(bias.mae_margin_vs_final)
        if bias.mae_margin_vs_final >= noisy:
            sentences.append(
                f"The final scores still moved about {bounce} points off the model's "
                "margin. That is ordinary football, not a reason to fade every home "
                "this week."
            )
        else:
            sentences.append(f"Final margins landed about {bounce} points off the model.")
    if bias.mae_total_vs_close is not None:
        miss = _fmt_points(bias.mae_total_vs_close)
        if bias.mae_total_vs_close <= CALM_CLOSE_MAE:
            sentences.append(f"Totals sat near the close (typical miss {miss}).")
        elif bias.mae_total_vs_close >= noisy:
            sentences.append(f"Totals were wild versus the close (typical miss {miss}).")
    if (
        prior is not None
        and prior.mae_margin_vs_close is not None
        and bias.mae_margin_vs_close is not None
        and bias.mae_margin_vs_close < prior.mae_margin_vs_close - 0.5
    ):
        sentences.append("The miss versus the close shrank from the week before.")
    return sentences


def explain_game_row(row: GameErrorRow) -> list[str]:
    """One finished game versus the ingested close and the final."""
    parts = [f"Model had {_side_margin(row.predicted_home_margin)}."]
    if row.close_home_margin is not None:
        parts.append(f"The ingested close was {_side_margin(row.close_home_margin)}.")
    if row.final_home_margin is not None:
        if abs(row.final_home_margin) < 0.05:
            parts.append("The game finished in a tie.")
        elif row.final_home_margin > 0:
            parts.append(f"Home won by {_fmt_points(row.final_home_margin)}.")
        else:
            parts.append(f"Away won by {_fmt_points(row.final_home_margin)}.")
    lines = [" ".join(parts)]
    total = [f"Model total {_fmt_points(row.predicted_total)}."]
    if row.close_total is not None:
        total.append(f"The ingested close was {_fmt_points(row.close_total)}.")
    if row.final_total is not None:
        total.append(f"They scored {_fmt_points(row.final_total)}.")
    if len(total) > 1:
        lines.append(" ".join(total))
    return lines


def present_league_errors(
    rows: list[GameErrorRow],
    prior_rows: list[GameErrorRow] | None = None,
) -> list[dict]:
    current = bias_by_league(rows)
    prior_map = {item.league: item for item in bias_by_league(prior_rows or [])}
    early = early_season_leagues(rows)
    return [
        {
            **item.model_dump(mode="json"),
            "sentences": explain_league_bias(
                item,
                early_season=item.league in early,
                prior=prior_map.get(item.league),
            ),
        }
        for item in current
    ]


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
    units: UnitBook | None = None,
) -> WeekErrorReport:
    slate, _, _ = current_slate(
        games, mode=mode, season=season, week=week, league=league, units=units
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
    units: UnitBook | None = None,
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
        engine = engines.setdefault(
            game.league, ModelEngine(game.league, params=extra, units=units)
        )
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
