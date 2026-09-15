from __future__ import annotations

from collections import defaultdict

from sbm.backtest import current_slate
from sbm.config import get_settings, params_for
from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.schema import Game, League, Pick, Prediction, StakeColumn
from sbm.teams import abbrev, abbrev_side, display_name, search_blob


def _fmt_spread(line: float | None) -> str | None:
    if line is None:
        return None
    if abs(line) < 1e-9:
        return "pk"
    return f"{line:+.1f}"


def honesty_flags(game: Game, pick: Pick | None) -> dict[str, bool]:
    settings = get_settings()
    params = params_for(game.league)
    noisy = bool(pick is not None and abs(pick.edge) > settings.noisy_edge_points)
    early_season = game.league == League.CFB and game.week < params.min_week_to_score
    return {"noisy": noisy, "early_season": early_season}


def game_cards(
    games: list[Game],
    mode: Mode,
    league: League | None = None,
    ledger: Ledger | None = None,
    *,
    season: int | None = None,
    week: int | None = None,
) -> tuple[list[dict], list[Pick]]:
    slate, picks, _ = current_slate(
        games, mode=mode, league=league, season=season, week=week
    )
    by_game: dict[str, list[Pick]] = defaultdict(list)
    for pick in picks:
        by_game[pick.game_id].append(pick)
    diary_by_game: dict[str, list[Pick]] = defaultdict(list)
    if ledger is not None:
        for entry in ledger.load():
            if entry.mode != mode:
                continue
            diary_by_game[entry.pick.game_id].append(entry.pick)

    cards = [
        _card(game, pred, by_game.get(game.game_id, []), diary_by_game.get(game.game_id, []))
        for game, pred in slate
    ]
    return cards, picks


def _pick_for(picks: list[Pick], market: str, column: StakeColumn) -> Pick | None:
    return next((p for p in picks if p.market.value == market and p.column == column), None)


def _pick_view(game: Game, pick: Pick | None) -> dict | None:
    if pick is None:
        return None
    data = pick.model_dump(mode="json")
    data["ticket"] = abbrev_side(game.league, pick.team_or_side)
    return data


def _market_block(
    game: Game,
    name: str,
    label: str,
    model: str | None,
    market_line: str | None,
    detail: str,
    model_picks: list[Pick],
    diary_picks: list[Pick],
    *,
    open_for_marks: bool,
) -> dict:
    model_pick = next((p for p in model_picks if p.market.value == name), None)
    system = _pick_for(diary_picks, name, StakeColumn.SYSTEM)
    gut = _pick_for(diary_picks, name, StakeColumn.GUT)
    flags = honesty_flags(game, model_pick or system)
    if name == "total":
        side_options = [
            {"side": "over", "label": "Over"},
            {"side": "under", "label": "Under"},
        ]
    else:
        side_options = [
            {"side": "away", "label": abbrev(game.league, game.away_team)},
            {"side": "home", "label": abbrev(game.league, game.home_team)},
        ]
    return {
        "name": name,
        "label": label,
        "model": model,
        "market": market_line,
        "detail": detail,
        "pick": _pick_view(game, model_pick),
        "model_ticket": _pick_view(game, model_pick),
        "system": _pick_view(game, system),
        "gut": _pick_view(game, gut),
        "noisy": flags["noisy"],
        "early_season": flags["early_season"],
        "side_options": side_options,
        "open_for_marks": open_for_marks,
    }


def _card(
    game: Game,
    pred: Prediction,
    model_picks: list[Pick],
    diary_picks: list[Pick],
) -> dict:
    model_home_line = -pred.predicted_home_margin
    away_code = abbrev(game.league, game.away_team)
    home_code = abbrev(game.league, game.home_team)
    markets = [
        _market_block(
            game,
            "spread",
            "Spread",
            _fmt_spread(model_home_line),
            _fmt_spread(game.spread_close),
            f"{home_code} {_fmt_spread(game.spread_close) or '—'}",
            model_picks,
            diary_picks,
            open_for_marks=game.spread_close is not None,
        ),
        _market_block(
            game,
            "total",
            "Total",
            f"{pred.predicted_total:.1f}",
            f"{game.total_close:.1f}" if game.total_close is not None else None,
            f"O/U {game.total_close if game.total_close is not None else '—'}",
            model_picks,
            diary_picks,
            open_for_marks=game.total_close is not None,
        ),
        _market_block(
            game,
            "moneyline",
            "Moneyline",
            f"{pred.home_win_prob:.0%} {home_code}",
            (
                f"{game.home_moneyline:+d}/{game.away_moneyline:+d}"
                if game.home_moneyline is not None and game.away_moneyline is not None
                else None
            ),
            f"{away_code} / {home_code}",
            model_picks,
            diary_picks,
            open_for_marks=game.home_moneyline is not None and game.away_moneyline is not None,
        ),
    ]
    noisy = any(m["noisy"] for m in markets)
    early = any(m["early_season"] for m in markets)
    has_pick = any(m["system"] and not m["system"].get("skipped") for m in markets)
    gut_bits = [
        f"{m['gut']['ticket']} {m['label'].lower()}"
        for m in markets
        if m["gut"] and not m["gut"].get("skipped")
    ]
    return {
        "game_id": game.game_id,
        "league": game.league.value,
        "season": game.season,
        "week": game.week,
        "away_team": game.away_team,
        "home_team": game.home_team,
        "away_display": display_name(game.league, game.away_team),
        "home_display": display_name(game.league, game.home_team),
        "away_abbrev": away_code,
        "home_abbrev": home_code,
        "kickoff": game.kickoff.isoformat() if game.kickoff else None,
        "is_final": game.is_final,
        "away_score": game.away_score,
        "home_score": game.home_score,
        "has_pick": has_pick,
        "has_gut": bool(gut_bits),
        "gut_label": " · ".join(gut_bits),
        "noisy": noisy,
        "early_season": early,
        "search_text": search_blob(game.league, game.away_team, game.home_team),
        "markets": markets,
        "picks": [p.model_dump(mode="json") for p in model_picks],
    }
