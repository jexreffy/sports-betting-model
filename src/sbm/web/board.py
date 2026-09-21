from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sbm.backtest import current_slate, pregame_predictions
from sbm.config import get_settings, params_for
from sbm.errors import WeekErrorReport, bias_by_league, row_from_prediction
from sbm.journal import format_slate, slate_bounds, slate_for_game, windows_between
from sbm.mode import Mode
from sbm.models.engine import ModelEngine
from sbm.odds import expected_value, home_cover_prob, total_over_prob
from sbm.picks import picks_from_prediction
from sbm.postseason import PostseasonSlot, slots_for_season
from sbm.predictions import CHICAGO, kickoff_in_chicago, kickoff_iso
from sbm.schema import Game, League, Pick, Prediction
from sbm.teams import abbrev_side, cfb_p4_conference, team_face
from sbm.units import UnitBook, favorite_side, home_adjustment

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


def _favorite_spread(home_margin: float | None, game: Game) -> str | None:
    """Favorite and the points they lay. Stored lines stay home-perspective."""
    if home_margin is None:
        return None
    favorite, points = favorite_side(home_margin, game.away_team, game.home_team)
    if favorite is None:
        return "Pick'em"
    return f"{team_face(game.league, favorite).abbrev} -{points:.1f}"


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
    units: UnitBook | None = None,
    you_ranks: dict[tuple[str, str], int] | None = None,
) -> tuple[list[dict], list[Pick]]:
    slate, picks, engines = current_slate(
        games, mode=mode, league=league, season=season, week=week, units=units
    )
    by_game: dict[str, list[Pick]] = defaultdict(list)
    for pick in picks:
        by_game[pick.game_id].append(pick)
    winners = predicted_winners or {}
    target_season = season
    if target_season is None and slate:
        target_season = slate[0][0].season
    model_ranks = _model_ranks(engines, games, target_season) if target_season else {}
    cards = [
        _card(
            game,
            pred,
            by_game.get(game.game_id, []),
            winners.get(game.game_id),
            engine=engines.get(game.league),
            units=units,
            model_ranks=model_ranks,
            you_ranks=you_ranks or {},
        )
        for game, pred in slate
    ]
    return cards, picks


def _group_for(game: Game, team: str, *, home: bool) -> str:
    if game.league == League.NFL:
        return "nfl"
    conference = game.home_conference if home else game.away_conference
    return cfb_p4_conference(team) or conference or ""


def _model_ranks(
    engines: dict[League, ModelEngine], games: list[Game], season: int
) -> dict[str, dict[str, int]]:
    buckets: dict[str, set[str]] = defaultdict(set)
    leagues: dict[str, League] = {}
    for game in games:
        if game.season != season:
            continue
        for team, home in ((game.home_team, True), (game.away_team, False)):
            group = _group_for(game, team, home=home)
            if not group:
                continue
            buckets[group].add(team)
            leagues[group] = game.league
    ranks: dict[str, dict[str, int]] = {}
    for group, teams in buckets.items():
        engine = engines.get(leagues[group])
        if engine is None:
            continue
        ordered = sorted(
            teams,
            key=lambda team: (-engine.elo.favorability(team, season), team),
        )
        ranks[group] = {team: index + 1 for index, team in enumerate(ordered)}
    return ranks


def _rank_text(you: int | None, model: int | None) -> str | None:
    parts: list[str] = []
    if you is not None:
        parts.append(f"You: {you}")
    if model is not None:
        parts.append(f"Model: {model}")
    if not parts:
        return None
    return " / ".join(parts)


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
            "label": team_face(game.league, game.away_team).abbrev,
            "team_or_side": game.away_team,
            "opponent": game.home_team,
            "market_line": away_line,
            "american_odds": away_ml,
        },
        {
            "side": "home",
            "label": team_face(game.league, game.home_team).abbrev,
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
    *,
    engine: ModelEngine | None = None,
    units: UnitBook | None = None,
    model_ranks: dict[str, dict[str, int]] | None = None,
    you_ranks: dict[tuple[str, str], int] | None = None,
) -> dict:
    away_face = team_face(game.league, game.away_team, game.away_conference)
    home_face = team_face(game.league, game.home_team, game.home_conference)
    away_code = away_face.abbrev
    home_code = home_face.abbrev
    market_spread = _favorite_spread(
        None if game.spread_close is None else -game.spread_close,
        game,
    )
    markets = [
        _market_block(
            game,
            "spread",
            "Spread",
            _favorite_spread(pred.predicted_home_margin, game),
            market_spread,
            market_spread or "—",
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
    if engine is None:
        neutral = pred.predicted_home_margin
        edge = None
    else:
        neutral = engine.elo.neutral_home_margin(game)
        _points, edge = home_adjustment(game, units, engine.params)
    full = _favorite_spread(pred.predicted_home_margin, game)
    neutral_text = _favorite_spread(neutral, game)
    model_context = f"Model {full} · Neutral {neutral_text}"
    if edge:
        model_context = f"{model_context} · {edge}"
    ranks = model_ranks or {}
    yours = you_ranks or {}
    away_group = _group_for(game, game.away_team, home=False)
    home_group = _group_for(game, game.home_team, home=True)
    away_model = ranks.get(away_group, {}).get(game.away_team)
    home_model = ranks.get(home_group, {}).get(game.home_team)
    return {
        "game_id": game.game_id,
        "league": game.league.value,
        "season": game.season,
        "week": game.week,
        "away_team": game.away_team,
        "home_team": game.home_team,
        "away_display": away_face.display_name,
        "home_display": home_face.display_name,
        "away_place": away_face.place,
        "away_nickname": away_face.nickname,
        "home_place": home_face.place,
        "home_nickname": home_face.nickname,
        "away_abbrev": away_code,
        "home_abbrev": home_code,
        "away_logo_url": away_face.logo_url,
        "away_logo_mark": away_face.logo_mark,
        "away_color": away_face.color,
        "home_logo_url": home_face.logo_url,
        "home_logo_mark": home_face.logo_mark,
        "home_color": home_face.color,
        "kickoff_iso": kickoff_iso(game.kickoff, game.league),
        "model_context": model_context,
        "away_rank": _rank_text(yours.get((away_group, game.away_team)), away_model),
        "home_rank": _rank_text(yours.get((home_group, game.home_team)), home_model),
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
        "search_text": f"{away_face.search_text} {home_face.search_text}",
        "markets": markets,
        "picks": [p.model_dump(mode="json") for p in model_picks],
    }


# Card fill is the research heatmap: both agree the market is wrong, then the model, then you.
_HEAT_RANK = {"both": 0, "model": 1, "you": 2, "none": 3}


def research_sort_key(card: dict) -> tuple:
    """Heatmap color, then best expected value. A game with no line sorts last."""
    value = card.get("value")
    return (
        0 if value is not None else 1,
        _HEAT_RANK.get(card.get("fill"), 3),
        -(value if isinstance(value, int | float) else 0.0),
        card.get("game_id") or card.get("slot_id") or "",
    )


def best_market_ev(game: Game, pred: Prediction) -> float | None:
    """Best side's expected value across spread, total, and moneyline."""
    settings = get_settings()
    params = params_for(game.league)
    values: list[float] = []
    if game.spread_close is not None:
        cover = home_cover_prob(
            pred.predicted_home_margin, game.spread_close, params.margin_sigma
        )
        values.append(expected_value(cover, settings.juice))
        values.append(expected_value(1.0 - cover, settings.juice))
    if game.total_close is not None:
        over = total_over_prob(pred.predicted_total, game.total_close, params.total_sigma)
        values.append(expected_value(over, settings.juice))
        values.append(expected_value(1.0 - over, settings.juice))
    if game.home_moneyline is not None and game.away_moneyline is not None:
        values.append(expected_value(pred.home_win_prob, game.home_moneyline))
        values.append(expected_value(1.0 - pred.home_win_prob, game.away_moneyline))
    if not values:
        return None
    return max(values)


def _engines_through(
    games: list[Game],
    units: UnitBook | None,
    window_end: date,
    *,
    include_undated: bool,
) -> dict[League, ModelEngine]:
    """Finals on or before the window. Undated games count only on the default week."""
    ordered = sorted(
        games,
        key=lambda game: (
            game.season,
            game.week,
            game.kickoff.isoformat() if game.kickoff else "",
            game.game_id,
        ),
    )
    engines: dict[League, ModelEngine] = {}
    for game in ordered:
        local = kickoff_in_chicago(game.kickoff, game.league)
        if local is None:
            if not include_undated:
                continue
        elif local.date() > window_end:
            continue
        engine = engines.setdefault(game.league, ModelEngine(game.league, units=units))
        if game.is_final:
            engine.update(game)
    return engines


def season_windows(games: list[Game], season: int) -> list[tuple[date, date]]:
    moments: list[datetime] = []
    for game in games:
        if game.season != season:
            continue
        local = kickoff_in_chicago(game.kickoff, game.league)
        if local is not None:
            moments.append(local)
    for slot in slots_for_season(season):
        moments.append(slot.sort_at)
    if not moments:
        return [slate_bounds(datetime.now(CHICAGO))]
    return windows_between(min(moments), max(moments))


def _window_for(windows: list[tuple[date, date]], today: date) -> tuple[date, date]:
    for window in windows:
        if window[0] <= today <= window[1]:
            return window
    if today < windows[0][0]:
        return windows[0]
    return windows[-1]


def _slot_card(slot: PostseasonSlot) -> dict:
    bits = [slot.round_name, slot.day_label or "", slot.venue or ""]
    return {
        "kind": "slot",
        "slot_id": slot.slot_id,
        "league": slot.league.value,
        "round_name": slot.round_name,
        "kickoff_iso": slot.kickoff_iso(),
        "day_label": slot.day_label,
        "venue": slot.venue,
        "sort_at": slot.sort_at.isoformat(),
        "search_text": " ".join(bit for bit in bits if bit),
    }


def research_board(
    games: list[Game],
    *,
    season: int,
    league: League | None = None,
    week: date | None = None,
    predicted_winners: dict[str, str] | None = None,
    units: UnitBook | None = None,
    you_ranks: dict[tuple[str, str], int] | None = None,
    today: date | None = None,
) -> dict:
    """One Tuesday–Monday window, priced from games that are already final."""
    windows = season_windows(games, season)
    current = today or datetime.now(CHICAGO).date()
    selected = _window_for(windows, current)
    if week is not None:
        match = next((item for item in windows if item[0] == week), None)
        if match is not None:
            selected = match
    start, end = selected
    default_start = _window_for(windows, current)[0]
    preds, _engines = pregame_predictions(games, units=units)
    rank_engines = _engines_through(
        games, units, end, include_undated=start == default_start
    )
    model_ranks = _model_ranks(rank_engines, games, season)
    winners = predicted_winners or {}
    yours = you_ranks or {}
    week_cards: list[dict] = []
    finals: list[tuple[Game, Prediction]] = []
    for game in games:
        if game.season != season:
            continue
        if league is not None and game.league != league:
            continue
        slate = slate_for_game(game)
        if slate is None:
            if start != default_start:
                continue
        elif slate[0] != start:
            continue
        pred = preds.get(game.game_id)
        if pred is None:
            continue
        if game.is_final:
            finals.append((game, pred))
        picks = picks_from_prediction(game, pred, Mode.SIMULATION, apply_week_gate=False)
        card = _card(
            game,
            pred,
            picks,
            winners.get(game.game_id),
            engine=rank_engines.get(game.league),
            units=units,
            model_ranks=model_ranks,
            you_ranks=yours,
        )
        card["kind"] = "game"
        card["value"] = best_market_ev(game, pred)
        week_cards.append(card)
    week_cards.sort(key=research_sort_key)
    slot_cards = [
        _slot_card(slot)
        for slot in slots_for_season(season)
        if slot.window_start() == start and (league is None or slot.league == league)
    ]
    slot_cards.sort(key=lambda card: (card["sort_at"], card["slot_id"]))
    rows = [row_from_prediction(game, pred) for game, pred in finals]
    errors = WeekErrorReport(
        season=season,
        week=0,
        n_games=len(rows),
        games=rows,
        by_league=bias_by_league(rows),
    )
    return {
        "weeks": [
            {"start": window[0].isoformat(), "label": format_slate(*window)} for window in windows
        ],
        "week": start.isoformat(),
        "slate_label": format_slate(start, end),
        "cards": week_cards + slot_cards,
        "errors": errors,
    }
