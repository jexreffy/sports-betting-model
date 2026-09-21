from __future__ import annotations

from collections import defaultdict

from sbm.backtest import current_slate
from sbm.config import get_settings, params_for
from sbm.mode import Mode
from sbm.schema import Game, League, Pick, Prediction
from sbm.teams import abbrev_side, render_abbrev, render_display_name, search_blob

INTERNATIONAL_VENUE_MARKERS = (
    "wembley",
    "tottenham",
    "allianz arena",
    "azteca",
    "croke park",
    "deutsche bank",
    "corinthians",
    "olympiastadion",
    "twickenham",
    "munich",
    "london",
    "mexico city",
    "sao paulo",
    "são paulo",
    "frankfurt",
    "dublin",
    "berlin",
    "melbourne",
    "maracana",
    "maracanã",
    "stade de france",
    "bernabeu",
    "bernabéu",
    "banorte",
)


def is_international_venue(venue: str | None) -> bool:
    if not venue:
        return False
    hay = venue.lower()
    return any(marker in hay for marker in INTERNATIONAL_VENUE_MARKERS)


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
    international = game.league == League.NFL and is_international_venue(game.venue)
    return {
        "noisy": noisy,
        "early_season": early_season,
        "international": international,
        "warning": noisy or early_season or international,
    }


def market_favorite_team(game: Game) -> str | None:
    if game.spread_close is not None:
        if abs(game.spread_close) < 1e-9:
            return None
        return game.home_team if game.spread_close < 0 else game.away_team
    if game.home_moneyline is not None and game.away_moneyline is not None:
        if game.home_moneyline == game.away_moneyline:
            return None
        return game.home_team if game.home_moneyline < game.away_moneyline else game.away_team
    return None


def fade_fill(*, you_fade: bool, model_fade: bool) -> str:
    if you_fade and model_fade:
        return "both"
    if you_fade:
        return "you"
    if model_fade:
        return "model"
    return "none"


def game_cards(
    games: list[Game],
    mode: Mode,
    league: League | None = None,
    *,
    season: int | None = None,
    week: int | None = None,
    predicted_winners: dict[str, str] | None = None,
) -> tuple[list[dict], list[Pick]]:
    slate, picks, _ = current_slate(
        games, mode=mode, league=league, season=season, week=week
    )
    by_game: dict[str, list[Pick]] = defaultdict(list)
    for pick in picks:
        by_game[pick.game_id].append(pick)
    winners = predicted_winners or {}
    cards = [
        _card(game, pred, by_game.get(game.game_id, []), winners.get(game.game_id))
        for game, pred in slate
    ]
    return cards, picks


def _pick_view(game: Game, pick: Pick | None) -> dict | None:
    if pick is None:
        return None
    data = pick.model_dump(mode="json")
    data["ticket"] = abbrev_side(game.league, pick.team_or_side)
    return data


def _wager_options(game: Game, name: str) -> list[dict]:
    if name == "total":
        return [
            {
                "side": "over",
                "label": "Over",
                "team_or_side": "over",
                "opponent": "under",
                "market_line": game.total_close,
                "american_odds": None,
            },
            {
                "side": "under",
                "label": "Under",
                "team_or_side": "under",
                "opponent": "over",
                "market_line": game.total_close,
                "american_odds": None,
            },
        ]
    away_line = None
    home_line = None
    if name == "spread" and game.spread_close is not None:
        home_line = game.spread_close
        away_line = -game.spread_close
    away_ml = game.away_moneyline if name == "moneyline" else None
    home_ml = game.home_moneyline if name == "moneyline" else None
    return [
        {
            "side": "away",
            "label": render_abbrev(game.league, game.away_team),
            "team_or_side": game.away_team,
            "opponent": game.home_team,
            "market_line": away_line,
            "american_odds": away_ml,
        },
        {
            "side": "home",
            "label": render_abbrev(game.league, game.home_team),
            "team_or_side": game.home_team,
            "opponent": game.away_team,
            "market_line": home_line,
            "american_odds": home_ml,
        },
    ]


def _market_block(
    game: Game,
    name: str,
    label: str,
    model: str | None,
    market_line: str | None,
    detail: str,
    model_picks: list[Pick],
    predicted_winner: str | None,
) -> dict:
    model_pick = next((p for p in model_picks if p.market.value == name), None)
    flags = honesty_flags(game, model_pick)
    model_fade = model_pick is not None
    you_fade = False
    if name != "total" and predicted_winner:
        fav = market_favorite_team(game)
        you_fade = fav is not None and predicted_winner != fav
    fill = fade_fill(you_fade=you_fade, model_fade=model_fade)
    chips: list[str] = []
    if flags["warning"]:
        bits = []
        if flags["noisy"]:
            bits.append("Noisy |edge|")
        if flags["early_season"]:
            bits.append("Early CFB")
        if flags["international"]:
            bits.append("International")
        chips.append("Warning: " + ", ".join(bits))
    if fill == "both":
        chips.append("Both fade")
    elif fill == "you":
        chips.append("You fade")
    elif fill == "model":
        chips.append("Model fade")
    open_for_wager = False
    if name == "spread":
        open_for_wager = game.spread_close is not None
    elif name == "total":
        open_for_wager = game.total_close is not None
    else:
        open_for_wager = game.home_moneyline is not None and game.away_moneyline is not None
    return {
        "name": name,
        "label": label,
        "model": model,
        "market": market_line,
        "detail": detail,
        "pick": _pick_view(game, model_pick),
        "model_ticket": _pick_view(game, model_pick),
        "noisy": flags["noisy"],
        "early_season": flags["early_season"],
        "international": flags["international"],
        "warning": flags["warning"],
        "you_fade": you_fade,
        "model_fade": model_fade,
        "fill": fill,
        "chips": chips,
        "wager_options": _wager_options(game, name),
        "open_for_wager": open_for_wager,
    }


def _card(
    game: Game,
    pred: Prediction,
    model_picks: list[Pick],
    predicted_winner: str | None,
) -> dict:
    model_home_line = -pred.predicted_home_margin
    away_code = render_abbrev(game.league, game.away_team)
    home_code = render_abbrev(game.league, game.home_team)
    markets = [
        _market_block(
            game,
            "spread",
            "Spread",
            _fmt_spread(model_home_line),
            _fmt_spread(game.spread_close),
            f"{home_code} {_fmt_spread(game.spread_close) or '—'}",
            model_picks,
            predicted_winner,
        ),
        _market_block(
            game,
            "total",
            "Total",
            f"{pred.predicted_total:.1f}",
            f"{game.total_close:.1f}" if game.total_close is not None else None,
            f"O/U {game.total_close if game.total_close is not None else '—'}",
            model_picks,
            predicted_winner,
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
            predicted_winner,
        ),
    ]
    you_any = any(m["you_fade"] for m in markets)
    model_any = any(m["model_fade"] for m in markets)
    card_fill = fade_fill(you_fade=you_any, model_fade=model_any)
    warning = any(m["warning"] for m in markets)
    chips: list[str] = []
    if warning:
        extra = []
        if any(m["noisy"] for m in markets):
            extra.append("Noisy |edge|")
        if any(m["early_season"] for m in markets):
            extra.append("Early CFB")
        if any(m["international"] for m in markets):
            extra.append("International")
        chips.append("Warning: " + ", ".join(extra))
    if card_fill == "both":
        chips.append("Both fade")
    elif card_fill == "you":
        chips.append("You fade")
    elif card_fill == "model":
        chips.append("Model fade")
    return {
        "game_id": game.game_id,
        "league": game.league.value,
        "season": game.season,
        "week": game.week,
        "away_team": game.away_team,
        "home_team": game.home_team,
        "away_display": render_display_name(game.league, game.away_team),
        "home_display": render_display_name(game.league, game.home_team),
        "away_abbrev": away_code,
        "home_abbrev": home_code,
        "kickoff": game.kickoff.isoformat() if game.kickoff else None,
        "is_final": game.is_final,
        "away_score": game.away_score,
        "home_score": game.home_score,
        "venue": game.venue,
        "predicted_winner": predicted_winner,
        "fill": card_fill,
        "warning": warning,
        "chips": chips,
        "noisy": any(m["noisy"] for m in markets),
        "early_season": any(m["early_season"] for m in markets),
        "international": any(m["international"] for m in markets),
        "search_text": search_blob(game.league, game.away_team, game.home_team),
        "markets": markets,
        "picks": [p.model_dump(mode="json") for p in model_picks],
    }
