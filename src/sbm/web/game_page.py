"""Template payload for the Game page. Pricing stays in sbm.matchup."""

from __future__ import annotations

from sbm.backtest import infer_current_week
from sbm.config import RESEARCH_WINDOWS
from sbm.matchup import MatchupView, SitePrice, price_matchup, resolve_team
from sbm.mode import Mode
from sbm.predictions import kickoff_iso, load_book, team_key, winners_by_game
from sbm.rankings import load_rankings
from sbm.schema import Game, League, SeasonPredictions
from sbm.teams import TeamFace, team_face
from sbm.units import UnitBook, load_unit_book
from sbm.web.board import game_cards, is_international_venue


def empty_payload(
    *,
    league: str = "nfl",
    team_a: str = "",
    team_b: str = "",
    error: str | None = None,
) -> dict:
    return {
        "error": error,
        "league": league if league in {item.value for item in League} else "nfl",
        "team_a": team_a,
        "team_b": team_b,
        "ready": False,
        "team_a_name": "",
        "team_b_name": "",
        "as_of_label": "",
        "stats": [],
        "sites": [],
        "meetings": [],
    }


def payload_for_pull(games: list[Game], league_name: str, team_a: str, team_b: str) -> dict:
    if league_name not in {item.value for item in League}:
        return empty_payload(
            league=league_name, team_a=team_a, team_b=team_b, error="Pick NFL or CFB"
        )
    league = League(league_name)
    try:
        left = resolve_team(league, team_a, games)
        right = resolve_team(league, team_b, games)
    except ValueError as exc:
        return empty_payload(league=league_name, team_a=team_a, team_b=team_b, error=str(exc))
    scoped = [game for game in games if game.league == league]
    inferred = infer_current_week(scoped)
    season = inferred[0] if inferred is not None else RESEARCH_WINDOWS.hands_off
    try:
        view = price_matchup(games, league, season, left, right, load_unit_book())
    except ValueError as exc:
        return empty_payload(league=league_name, team_a=team_a, team_b=team_b, error=str(exc))
    return _view_payload(games, view, opened_id=None, team_a_text=team_a, team_b_text=team_b)


def payload_for_game(games: list[Game], game_id: str) -> dict | None:
    game = next((item for item in games if item.game_id == game_id), None)
    if game is None:
        return None
    left, right = _stable_pair(game)
    view = price_matchup(games, game.league, game.season, left, right, load_unit_book())
    return _view_payload(
        games,
        view,
        opened_id=game.game_id,
        team_a_text=left,
        team_b_text=right,
    )


def _face_fields(face: TeamFace, prefix: str) -> dict:
    return {
        f"{prefix}_logo_url": face.logo_url,
        f"{prefix}_logo_mark": face.logo_mark,
        f"{prefix}_color": face.color,
        f"{prefix}_place": face.place,
        f"{prefix}_nickname": face.nickname,
    }


def _site_payload(site: SitePrice, primary: TeamFace, secondary: TeamFace | None) -> dict:
    payload = {
        "label": site.label,
        "spread": site.spread,
        "total": site.total,
        "moneyline": site.moneyline,
        "neutral": secondary is not None,
        "logo_url": primary.logo_url,
        "logo_mark": primary.logo_mark,
        "color": primary.color,
        "logo_url_b": None,
        "logo_mark_b": None,
        "color_b": None,
    }
    if secondary is not None:
        payload["logo_url_b"] = secondary.logo_url
        payload["logo_mark_b"] = secondary.logo_mark
        payload["color_b"] = secondary.color
    return payload


def _stable_pair(game: Game) -> tuple[str, str]:
    left_key = team_key(game.league, game.away_team)
    right_key = team_key(game.league, game.home_team)
    if left_key <= right_key:
        return game.away_team, game.home_team
    return game.home_team, game.away_team


def _view_payload(
    games: list[Game],
    view: MatchupView,
    *,
    opened_id: str | None,
    team_a_text: str,
    team_b_text: str,
) -> dict:
    book = load_book(view.season)
    units = load_unit_book()
    ranks = load_rankings(view.season)
    you_ranks = {
        (group, team): index + 1
        for group, names in ranks.groups.items()
        for index, team in enumerate(names)
    }
    winners = winners_by_game(book)
    cards = _cards_by_id(games, view, units, winners, you_ranks)
    left_face = team_face(view.league, view.team_a)
    right_face = team_face(view.league, view.team_b)
    return {
        "error": None,
        "league": view.league.value,
        "team_a": team_a_text,
        "team_b": team_b_text,
        "ready": True,
        "team_a_name": left_face.display_name,
        "team_b_name": right_face.display_name,
        "team_a_abbrev": left_face.abbrev,
        "team_b_abbrev": right_face.abbrev,
        **_face_fields(left_face, "team_a"),
        **_face_fields(right_face, "team_b"),
        "as_of_label": f"{view.season} Week {view.week}",
        "stats": [{"label": row.label, "left": row.left, "right": row.right} for row in view.stats],
        # Site order is team_a at home, team_b at home, then neutral.
        "sites": [
            _site_payload(site, primary, secondary)
            for site, primary, secondary in zip(
                view.sites,
                (left_face, right_face, left_face),
                (None, None, right_face),
                strict=True,
            )
        ],
        "meetings": [
            _meeting_payload(item.game, item.factors, cards.get(item.game.game_id), book, opened_id)
            for item in view.meetings
        ],
        "opened_id": opened_id,
    }


def _cards_by_id(
    games: list[Game],
    view: MatchupView,
    units: UnitBook,
    winners: dict[str, str],
    you_ranks: dict[tuple[str, str], int],
) -> dict[str, dict]:
    league_games = [game for game in games if game.league == view.league]
    cards: dict[str, dict] = {}
    seen_weeks: set[int] = set()
    for meeting in view.meetings:
        if meeting.game.week in seen_weeks:
            continue
        seen_weeks.add(meeting.game.week)
        week_cards, _picks = game_cards(
            league_games,
            Mode.SIMULATION,
            view.league,
            season=view.season,
            week=meeting.game.week,
            predicted_winners=winners,
            units=units,
            you_ranks=you_ranks,
        )
        for card in week_cards:
            cards[card["game_id"]] = card
    return cards


def _meeting_payload(
    game: Game,
    factors: list,
    card: dict | None,
    book: SeasonPredictions | None,
    opened_id: str | None,
) -> dict:
    away = team_face(game.league, game.away_team)
    home = team_face(game.league, game.home_team)
    if game.home_rest_days is None or game.away_rest_days is None:
        rest = "Not stored"
    else:
        rest = (
            f"{away.abbrev} {game.away_rest_days} days · {home.abbrev} {game.home_rest_days} days"
        )
    return {
        "game_id": game.game_id,
        "opened": game.game_id == opened_id,
        "week": game.week,
        "season": game.season,
        "away_name": away.display_name,
        "home_name": home.display_name,
        **_face_fields(away, "away"),
        **_face_fields(home, "home"),
        "kickoff_iso": kickoff_iso(game.kickoff, game.league),
        "venue": game.venue or "Not stored",
        "site": "Neutral" if game.is_neutral else f"{home.display_name} home",
        "international": game.league == League.NFL and is_international_venue(game.venue),
        "rest": rest,
        "factors": [{"label": row.label, "points": f"{row.points:+.1f}"} for row in factors],
        "take": _take_text(book, game),
        "card": card,
    }


def _take_text(book: SeasonPredictions | None, game: Game) -> str:
    if book is None:
        return "No pick"
    for team in book.teams:
        for row in team.games:
            if row.game_id != game.game_id or not row.predicted_winner:
                continue
            if row.pick_kind == "cover" and row.cover_favorite:
                name = team_face(game.league, row.cover_favorite).abbrev
                if row.cover_line is None:
                    return f"Cover {name}"
                return f"Cover {name} -{row.cover_line:.1f}"
            return f"{team_face(game.league, row.predicted_winner).display_name} outright"
    return "No pick"
