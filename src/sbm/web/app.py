from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from sbm.config import RESEARCH_WINDOWS
from sbm.journal import Journal, new_ticket_id
from sbm.mode import Mode, parse_mode
from sbm.schema import League, Leg, Ticket, TicketKind

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def _game_href(game_id: str) -> str:
    token = quote(str(game_id), safe="")
    return f"/game/{token}#game-{token}"


templates.env.filters["game_href"] = _game_href

app = FastAPI(title="SBM", description="NFL + CFB research, Predictions, and 2026 Journal")
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


def _mode(value: str) -> Mode:
    try:
        return parse_mode(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _nav() -> list[dict[str, str]]:
    return [
        {"href": "/research", "label": "Research", "key": "research"},
        {"href": "/game", "label": "Game", "key": "game"},
        {"href": "/predictions", "label": "Predictions", "key": "predictions"},
        {"href": "/ratings", "label": "Ratings", "key": "ratings"},
        {"href": "/rankings", "label": "Rankings", "key": "rankings"},
        {"href": "/journal", "label": "Journal", "key": "journal"},
    ]


class JournalAddRequest(BaseModel):
    sportsbook: str = "Novig"
    stake_dollars: float
    american_odds: int | None = None
    decimal_odds: float | None = None
    implied_prob: float | None = None
    kind: str = "straight"
    season: int = RESEARCH_WINDOWS.hands_off
    notes: str | None = None
    legs: list[dict]


class JournalCashoutRequest(BaseModel):
    ticket_id: str
    cashout_dollars: float


class JournalDropRequest(BaseModel):
    ticket_id: str


class PredictionsSetRequest(BaseModel):
    season: int = RESEARCH_WINDOWS.hands_off
    game_id: str
    predicted_winner: str | None = None
    choice: str | None = None


class PredictionsNoteRequest(BaseModel):
    season: int = RESEARCH_WINDOWS.hands_off
    team: str
    league: str
    note: str | None = None


def _board_payload(league: str | None = None) -> dict:
    from sbm.backtest import infer_current_week
    from sbm.data.store import load_games
    from sbm.errors import week_error_report
    from sbm.predictions import load_book, winners_by_game
    from sbm.rankings import load_rankings
    from sbm.units import load_unit_book
    from sbm.web.board import game_cards

    lg = League(league) if league in {item.value for item in League} else None
    catalog = load_games()
    games = [g for g in catalog if lg is None or g.league == lg]
    season = RESEARCH_WINDOWS.hands_off
    book = load_book(season)
    units = load_unit_book()
    ranks = load_rankings(season)
    you_ranks = {
        (group, team): index + 1
        for group, names in ranks.groups.items()
        for index, team in enumerate(names)
    }
    cards, picks = (
        game_cards(
            games,
            Mode.SIMULATION,
            lg,
            season=season,
            predicted_winners=winners_by_game(book),
            units=units,
            you_ranks=you_ranks,
        )
        if games
        else ([], [])
    )
    slate_bits = []
    seen: set[tuple[str, int, int]] = set()
    for card in cards:
        key = (card["league"], card["season"], card["week"])
        if key in seen:
            continue
        seen.add(key)
        slate_bits.append(f"{card['league'].upper()} {card['season']} Week {card['week']}")
    errors = None
    inferred = infer_current_week(games, season=season) if games else None
    if inferred is not None:
        errors = week_error_report(
            games,
            season=inferred[0],
            week=inferred[1],
            mode=Mode.SIMULATION,
            league=lg,
            units=units,
        ).model_dump(mode="json")
    return {
        "mode": Mode.SIMULATION.value,
        "banner": (
            "Research — this week's model vs market. Log tickets into Journal. "
            "This does not train Elo."
        ),
        "slate_label": " · ".join(slate_bits) if slate_bits else "No current slate",
        "cards": cards,
        "picks": [p.model_dump(mode="json") for p in picks],
        "errors": errors,
        "has_games": bool(games),
        "nav": _nav(),
        "active": "research",
        "season": season,
    }


def _journal_payload(season: int) -> dict:
    from sbm.data.store import load_games
    from sbm.journal import present_ticket_legs

    book = Journal()
    stats = book.year(season)
    games = load_games()
    tickets = book.rows_for_year(season)
    slate_weeks = present_ticket_legs(tickets, games)
    return {
        "banner": (
            "Journal — 2026 real tickets (Novig). Logging only; SBM never places a wager. "
            "Championship futures are not tracked."
        ),
        "season": season,
        "summary": stats.model_dump(),
        "tickets": tickets,
        "slate_weeks": slate_weeks,
        "nav": _nav(),
        "active": "journal",
    }


def _ensure_predictions(season: int):
    from sbm.data.store import load_games
    from sbm.predictions import init_book, load_book, save_book, sync_actuals

    book = load_book(season)
    games = load_games()
    if book is None:
        book = init_book(games, season)
        save_book(book)
        return book
    updated = sync_actuals(book, games)
    save_book(updated)
    return updated


def _button_label(abbrev: str, favorite: str | None, team: str, laying: float) -> str:
    if favorite is None or favorite != team:
        return abbrev
    return f"{abbrev} -{laying:.1f}"


def _predictions_payload(season: int, conference: str | None = None) -> dict:
    from sbm.backtest import pregame_predictions
    from sbm.data.store import load_games
    from sbm.predictions import (
        audit_covers,
        bye_weeks,
        format_kickoff_cdt,
        leftovers_for,
        save_book,
    )
    from sbm.teams import team_face
    from sbm.units import favorite_side, load_unit_book
    from sbm.web.board import is_international_venue

    book = _ensure_predictions(season)
    catalog = load_games()
    games_by_id = {g.game_id: g for g in catalog if g.season == season}
    preds, _engines = pregame_predictions(catalog, units=load_unit_book())
    margins = {
        game_id: pred.predicted_home_margin
        for game_id, pred in preds.items()
        if game_id in games_by_id
    }
    book, changed = audit_covers(book, margins, games_by_id)
    if changed:
        save_book(book)
    teams = book.teams
    if conference:
        if conference.lower() == "nfl":
            teams = [t for t in teams if t.league == League.NFL]
        else:
            teams = [t for t in teams if t.conference == conference]
    views = []
    for team in teams:
        face = team_face(team.league, team.team, team.conference)
        data = team.model_dump(mode="json")
        data["logo_url"] = face.logo_url
        data["logo_mark"] = face.logo_mark
        data["display_name"] = face.display_name
        data["place"] = face.place
        data["nickname"] = face.nickname
        data["abbrev"] = face.abbrev
        data["color"] = face.color
        data["search_text"] = face.search_text
        data["games"].sort(key=lambda row: (row["week"], row.get("kickoff") or "", row["game_id"]))
        for row in data["games"]:
            away = row["opponent"] if row["is_home"] else team.team
            home = team.team if row["is_home"] else row["opponent"]
            away_face = team_face(team.league, away)
            home_face = team_face(team.league, home)
            opp_face = team_face(team.league, row["opponent"])
            raw_kick = row.get("kickoff")
            kickoff = None
            if isinstance(raw_kick, datetime):
                kickoff = raw_kick
            elif isinstance(raw_kick, str) and raw_kick:
                kickoff = datetime.fromisoformat(raw_kick.replace("Z", "+00:00"))
            margin = margins.get(row["game_id"])
            favorite = None
            laying = 0.0
            if margin is not None:
                favorite, laying = favorite_side(margin, away, home)
            kind = row.get("pick_kind")
            winner = row.get("predicted_winner")
            if kind == "cover":
                selected = "cover"
            elif winner == away:
                selected = "away"
            elif winner == home:
                selected = "home"
            else:
                selected = ""
            row["away_team"] = away
            row["home_team"] = home
            row["away_abbrev"] = away_face.abbrev
            row["home_abbrev"] = home_face.abbrev
            row["away_label"] = _button_label(away_face.abbrev, favorite, away, laying)
            row["home_label"] = _button_label(home_face.abbrev, favorite, home, laying)
            row["cover_enabled"] = favorite is not None
            row["selected"] = selected
            row["opp_display"] = opp_face.display_name
            row["away_logo_url"] = away_face.logo_url
            row["home_logo_url"] = home_face.logo_url
            row["opp_logo_url"] = opp_face.logo_url
            row["away_logo_mark"] = away_face.logo_mark
            row["home_logo_mark"] = home_face.logo_mark
            row["opp_logo_mark"] = opp_face.logo_mark
            row["kickoff_label"] = format_kickoff_cdt(kickoff, team.league)
            stored = games_by_id.get(row["game_id"])
            row["international"] = bool(
                stored is not None and is_international_venue(stored.venue)
            )
            row["venue"] = stored.venue if stored is not None else None
        byes = bye_weeks(team.games, team.league)
        data["bye_weeks"] = byes
        open_games = [row for row in data["games"] if not row.get("actual_winner")]
        by_week: dict[int, list] = {}
        for row in open_games:
            by_week.setdefault(row["week"], []).append(row)
        open_schedule: list[dict] = []
        for week in sorted(set(byes) | set(by_week)):
            if week in byes:
                open_schedule.append({"kind": "bye", "week": week})
            for row in by_week.get(week, []):
                open_schedule.append({"kind": "game", **row})
        data["open_schedule"] = open_schedule
        views.append(data)
    leftovers = leftovers_for(book, None if not conference else conference)
    for row in leftovers:
        row["team"] = team_face(League.CFB, row["team"]).display_name
        row["opponent"] = team_face(League.CFB, row["opponent"]).display_name
    change_label = {
        "flip": "Favorite flipped",
        "move": "Line moved by 3+",
        "pickem": "Line inside half a point",
    }
    audits = []
    for item in reversed(book.audits):
        game = games_by_id.get(item.game_id)
        league = game.league if game is not None else League.NFL
        if game is not None:
            label = (
                f"{team_face(league, game.away_team).abbrev} @ "
                f"{team_face(league, game.home_team).abbrev}"
            )
        else:
            label = item.label
        if item.new_favorite is None:
            new_text = "pick'em"
        else:
            new_text = f"{team_face(league, item.new_favorite).abbrev} -{item.new_line:.1f}"
        audits.append(
            {
                "game_id": item.game_id,
                "label": label,
                "change": change_label.get(item.change, item.change),
                "old_text": f"{team_face(league, item.old_favorite).abbrev} -{item.old_line:.1f}",
                "new_text": new_text,
            }
        )
    return {
        "banner": (
            "Predictions — current-year W/L takes. Results fill in; picks never auto-flip. "
            "Reconsider is a warning, not a grade."
        ),
        "season": season,
        "conference": conference or "all",
        "teams": views,
        "leftovers": leftovers,
        "audits": audits,
        "nav": _nav(),
        "active": "predictions",
    }


def _ticket_from_request(body: JournalAddRequest) -> Ticket:
    from sbm.odds import decimal_to_american, implied_to_american

    odds = body.american_odds
    if odds is None and body.decimal_odds is not None:
        odds = decimal_to_american(body.decimal_odds)
    if odds is None and body.implied_prob is not None:
        odds = implied_to_american(body.implied_prob)
    if odds is None:
        raise ValueError("Provide american_odds, decimal_odds, or implied_prob")
    if not body.legs:
        raise ValueError("At least one leg is required")
    return Ticket(
        ticket_id=new_ticket_id(),
        season=body.season,
        sportsbook=body.sportsbook,
        stake_dollars=body.stake_dollars,
        american_odds=odds,
        kind=TicketKind(body.kind.lower()),
        legs=[Leg.model_validate(leg) for leg in body.legs],
        implied_prob=body.implied_prob,
        notes=body.notes,
        placed_at=datetime.now(UTC),
    )


@app.get("/", response_class=RedirectResponse)
def index() -> RedirectResponse:
    return RedirectResponse("/research", status_code=307)


@app.get("/research", response_class=HTMLResponse)
def research(request: Request, league: str | None = None) -> HTMLResponse:
    payload = _board_payload(league)
    return templates.TemplateResponse(
        request,
        "board.html",
        {
            **payload,
            "league": league or "all",
        },
        headers={"Cache-Control": "no-store"},
    )


def _live_model(season: int):
    from sbm.backtest import infer_current_week, pregame_predictions
    from sbm.data.store import load_games
    from sbm.units import load_unit_book

    games = load_games()
    units = load_unit_book()
    _preds, engines = pregame_predictions(games, units=units)
    found = infer_current_week(games, season=season)
    week = found[1] if found else 1
    return games, engines, units, week


def _teams_for_group(games, season: int, group: str) -> list[tuple]:
    from sbm.teams import cfb_p4_conference

    found: dict[str, League] = {}
    for game in games:
        if game.season != season:
            continue
        sides = (
            (game.home_team, game.home_conference),
            (game.away_team, game.away_conference),
        )
        for team, conference in sides:
            if group == "nfl" and game.league == League.NFL:
                found[team] = League.NFL
            elif game.league == League.CFB and group != "nfl":
                if (cfb_p4_conference(team) or conference) == group:
                    found[team] = League.CFB
    return list(found.items())


def _ordered_teams(games, engines, season: int, group: str) -> list[str]:
    rows = _teams_for_group(games, season, group)

    def _nff(item: tuple[str, League]) -> float:
        team, league = item
        engine = engines.get(league)
        if engine is None:
            return 0.0
        return engine.elo.favorability(team, season)

    rows.sort(key=lambda item: (-_nff(item), item[0]))
    return [team for team, _league in rows]


def _fmt_unit(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:+.{digits}f}"


def _ratings_payload(league: str | None) -> dict:
    from sbm.teams import team_face

    season = RESEARCH_WINDOWS.hands_off
    games, engines, units, week = _live_model(season)
    wanted = League(league) if league in {item.value for item in League} else League.NFL
    rows = []
    seen: set[tuple[str, str]] = set()
    for game in games:
        if game.season != season:
            continue
        if wanted is not None and game.league != wanted:
            continue
        for team, conference in (
            (game.home_team, game.home_conference),
            (game.away_team, game.away_conference),
        ):
            key = (game.league.value, team)
            if key in seen:
                continue
            seen.add(key)
            engine = engines.get(game.league)
            nff = engine.elo.favorability(team, season) if engine is not None else 0.0
            profile = units.profile_before(game.league, team, season, week)
            face = team_face(game.league, team, conference)
            if game.league == League.NFL:
                run = _fmt_unit(None if profile is None else profile.rush_off)
                passing = _fmt_unit(None if profile is None else profile.pass_off)
                talent = "—"
            else:
                run = _fmt_unit(None if profile is None else profile.line_yards, 1)
                passing = _fmt_unit(None if profile is None else profile.pass_success)
                if profile is None or profile.talent is None:
                    talent = "—"
                else:
                    talent = f"{profile.talent:.0f}"
            rows.append(
                {
                    "display_name": face.display_name,
                    "place": face.place,
                    "nickname": face.nickname,
                    "abbrev": face.abbrev,
                    "logo_url": face.logo_url,
                    "logo_mark": face.logo_mark,
                    "color": face.color or "#30363d",
                    "nff": nff,
                    "nff_text": f"{nff:+.1f}",
                    "run": run,
                    "passing": passing,
                    "talent": talent,
                }
            )
    rows.sort(key=lambda row: row["nff"], reverse=True)
    return {
        "banner": "Ratings — neutral-field favorability versus an average opponent.",
        "season": season,
        "league": wanted.value,
        "league_label": wanted.value.upper(),
        "rows": rows,
        "nav": _nav(),
        "active": "ratings",
    }


RANKING_GROUPS = ("nfl", "B1G", "SEC", "ACC", "Big 12")


def _rankings_payload(season: int, group: str) -> dict:
    from sbm.rankings import load_rankings, visible_order
    from sbm.teams import team_face

    chosen = group if group in RANKING_GROUPS else "nfl"
    games, engines, _units, _week = _live_model(season)
    book = load_rankings(season)
    model_order = _ordered_teams(games, engines, season, chosen)
    saved = book.groups.get(chosen, [])
    order = visible_order(saved, model_order)
    league = League.NFL if chosen == "nfl" else League.CFB
    rows = []
    for index, team in enumerate(order):
        face = team_face(league, team)
        rows.append(
            {
                "team": team,
                "rank": index + 1,
                "display_name": face.display_name,
                "place": face.place,
                "nickname": face.nickname,
                "abbrev": face.abbrev,
                "logo_url": face.logo_url,
                "logo_mark": face.logo_mark,
                "color": face.color or "#30363d",
                "saved": bool(saved),
            }
        )
    return {
        "banner": (
            "Rankings — your order. Research shows it beside the model and does not recolor cards."
        ),
        "season": season,
        "group": chosen,
        "groups": RANKING_GROUPS,
        "rows": rows,
        "saved": bool(saved),
        "nav": _nav(),
        "active": "rankings",
    }


class RankingsMoveRequest(BaseModel):
    season: int = RESEARCH_WINDOWS.hands_off
    group: str
    team: str
    direction: str


class RankingsPlaceRequest(BaseModel):
    season: int = RESEARCH_WINDOWS.hands_off
    group: str
    team: str
    index: int


@app.get("/ratings", response_class=HTMLResponse)
def ratings_page(request: Request, league: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "ratings.html",
        _ratings_payload(league),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/rankings", response_class=HTMLResponse)
def rankings_page(
    request: Request,
    season: int = RESEARCH_WINDOWS.hands_off,
    group: str = "nfl",
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "rankings.html",
        _rankings_payload(season, group),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/rankings/move")
def api_rankings_move(body: RankingsMoveRequest) -> JSONResponse:
    from sbm.rankings import load_rankings, move_team, save_rankings, visible_order

    if body.group not in RANKING_GROUPS:
        raise HTTPException(status_code=400, detail="Unknown group")
    games, engines, _units, _week = _live_model(body.season)
    book = load_rankings(body.season)
    model_order = _ordered_teams(games, engines, body.season, body.group)
    current = visible_order(book.groups.get(body.group, []), model_order)
    try:
        book.groups[body.group] = move_team(current, body.team, body.direction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_rankings(book)
    return JSONResponse(book.model_dump(mode="json"))


@app.post("/api/rankings/place")
def api_rankings_place(body: RankingsPlaceRequest) -> JSONResponse:
    from sbm.rankings import load_rankings, place_team, save_rankings, visible_order

    if body.group not in RANKING_GROUPS:
        raise HTTPException(status_code=400, detail="Unknown group")
    games, engines, _units, _week = _live_model(body.season)
    book = load_rankings(body.season)
    model_order = _ordered_teams(games, engines, body.season, body.group)
    current = visible_order(book.groups.get(body.group, []), model_order)
    try:
        book.groups[body.group] = place_team(current, body.team, body.index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_rankings(book)
    return JSONResponse(book.model_dump(mode="json"))


def _game_context(payload: dict) -> dict:
    return {
        **payload,
        "nav": _nav(),
        "active": "game",
        "banner": (
            "Game — pull two teams, or open a meeting from Research, Predictions, or Journal. "
            "Logging only; SBM never places a wager."
        ),
        "season": (
            payload["meetings"][0]["season"]
            if payload.get("meetings")
            else RESEARCH_WINDOWS.hands_off
        ),
    }


@app.get("/game", response_class=HTMLResponse)
def game_page(
    request: Request,
    league: str = "nfl",
    team_a: str = "",
    team_b: str = "",
) -> HTMLResponse:
    from sbm.data.store import load_games
    from sbm.web.game_page import empty_payload, payload_for_pull

    if team_a.strip() or team_b.strip():
        payload = payload_for_pull(load_games(), league, team_a, team_b)
    else:
        payload = empty_payload(league=league)
    return templates.TemplateResponse(
        request,
        "game.html",
        _game_context(payload),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/game/{game_id:path}", response_class=HTMLResponse)
def game_by_id(request: Request, game_id: str) -> HTMLResponse:
    from sbm.data.store import load_games
    from sbm.web.game_page import payload_for_game

    payload = payload_for_game(load_games(), game_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Unknown game {game_id}")
    return templates.TemplateResponse(
        request,
        "game.html",
        _game_context(payload),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/journal", response_class=HTMLResponse)
def journal_page(
    request: Request, season: int = RESEARCH_WINDOWS.hands_off
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "journal.html",
        _journal_payload(season),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/predictions", response_class=HTMLResponse)
def predictions_page(
    request: Request,
    season: int = RESEARCH_WINDOWS.hands_off,
    conference: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "predictions.html",
        _predictions_payload(season, conference),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/board")
def api_board(mode: str = "simulation", league: str | None = None) -> JSONResponse:
    _mode(mode)
    return JSONResponse(
        _board_payload(league),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/journal")
def api_journal(season: int = RESEARCH_WINDOWS.hands_off) -> JSONResponse:
    return JSONResponse(_journal_payload(season), headers={"Cache-Control": "no-store"})


@app.post("/api/journal/tickets")
def api_journal_add(body: JournalAddRequest) -> JSONResponse:
    try:
        ticket = _ticket_from_request(body)
        Journal().add(ticket)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(ticket.model_dump(mode="json"))


@app.post("/api/journal/cashout")
def api_journal_cashout(body: JournalCashoutRequest) -> JSONResponse:
    try:
        ticket = Journal().cashout(body.ticket_id, body.cashout_dollars)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(ticket.model_dump(mode="json"))


@app.post("/api/journal/drop")
def api_journal_drop(body: JournalDropRequest) -> JSONResponse:
    try:
        Journal().drop(body.ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"ok": True})


@app.get("/api/predictions")
def api_predictions(
    season: int = RESEARCH_WINDOWS.hands_off, conference: str | None = None
) -> JSONResponse:
    return JSONResponse(
        _predictions_payload(season, conference),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/predictions/set")
def api_predictions_set(body: PredictionsSetRequest) -> JSONResponse:
    from sbm.backtest import pregame_predictions
    from sbm.data.store import load_games
    from sbm.predictions import save_book, set_pick, set_winner
    from sbm.units import load_unit_book

    book = _ensure_predictions(body.season)
    try:
        if body.choice:
            catalog = load_games()
            game = next((g for g in catalog if g.game_id == body.game_id), None)
            if game is None:
                raise ValueError(f"Unknown game {body.game_id}")
            preds, _engines = pregame_predictions(catalog, units=load_unit_book())
            pred = preds.get(body.game_id)
            if pred is None:
                raise ValueError(f"No model number for {body.game_id}")
            updated = set_pick(
                book,
                body.game_id,
                body.choice,
                home_margin=pred.predicted_home_margin,
                away_team=game.away_team,
                home_team=game.home_team,
            )
        elif body.predicted_winner:
            updated = set_winner(book, body.game_id, body.predicted_winner)
        else:
            raise ValueError("Provide choice or predicted_winner")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_book(updated)
    return JSONResponse(updated.model_dump(mode="json"))


@app.post("/api/predictions/note")
def api_predictions_note(body: PredictionsNoteRequest) -> JSONResponse:
    from sbm.predictions import save_book, set_note

    book = _ensure_predictions(body.season)
    try:
        updated = set_note(book, body.team, League(body.league), body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_book(updated)
    return JSONResponse(updated.model_dump(mode="json"))


def _paper_gone() -> JSONResponse:
    return JSONResponse(
        {"detail": "Paper mark is gone. Log tickets with POST /api/journal/tickets."},
        status_code=410,
    )


@app.post("/api/mark")
def api_mark_gone() -> JSONResponse:
    return _paper_gone()


@app.post("/api/unmark")
def api_unmark_gone() -> JSONResponse:
    return _paper_gone()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
