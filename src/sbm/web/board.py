from __future__ import annotations

from collections import defaultdict

from sbm.backtest import current_slate
from sbm.mode import Mode
from sbm.schema import Game, League, Pick, Prediction
from sbm.teams import search_blob


def _fmt_spread(line: float | None) -> str | None:
    if line is None:
        return None
    if abs(line) < 1e-9:
        return "pk"
    return f"{line:+.1f}"


def game_cards(
    games: list[Game],
    mode: Mode,
    league: League | None = None,
) -> tuple[list[dict], list[Pick]]:
    slate, picks, _ = current_slate(games, mode=mode, league=league)
    by_game: dict[str, list[Pick]] = defaultdict(list)
    for pick in picks:
        by_game[pick.game_id].append(pick)

    cards = [_card(game, pred, by_game.get(game.game_id, [])) for game, pred in slate]
    return cards, picks


def _card(game: Game, pred: Prediction, picks: list[Pick]) -> dict:
    pick_by_market = {p.market.value: p.model_dump(mode="json") for p in picks}
    model_home_line = -pred.predicted_home_margin
    return {
        "game_id": game.game_id,
        "league": game.league.value,
        "season": game.season,
        "week": game.week,
        "away_team": game.away_team,
        "home_team": game.home_team,
        "kickoff": game.kickoff.isoformat() if game.kickoff else None,
        "is_final": game.is_final,
        "away_score": game.away_score,
        "home_score": game.home_score,
        "has_pick": bool(picks),
        "search_text": search_blob(game.league, game.away_team, game.home_team),
        "markets": [
            {
                "name": "spread",
                "label": "Spread",
                "model": _fmt_spread(model_home_line),
                "market": _fmt_spread(game.spread_close),
                "detail": f"{game.home_team} {_fmt_spread(game.spread_close) or '—'}",
                "pick": pick_by_market.get("spread"),
            },
            {
                "name": "total",
                "label": "Total",
                "model": f"{pred.predicted_total:.1f}",
                "market": f"{game.total_close:.1f}" if game.total_close is not None else None,
                "detail": f"O/U {game.total_close if game.total_close is not None else '—'}",
                "pick": pick_by_market.get("total"),
            },
            {
                "name": "moneyline",
                "label": "Moneyline",
                "model": f"{pred.home_win_prob:.0%} {game.home_team}",
                "market": (
                    f"{game.home_moneyline:+d}/{game.away_moneyline:+d}"
                    if game.home_moneyline is not None and game.away_moneyline is not None
                    else None
                ),
                "detail": f"{game.away_team} / {game.home_team}",
                "pick": pick_by_market.get("moneyline"),
            },
        ],
        "picks": [p.model_dump(mode="json") for p in picks],
    }
