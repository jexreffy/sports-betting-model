from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
        {"href": "/predictions", "label": "Predictions", "key": "predictions"},
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
    predicted_winner: str


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
    from sbm.web.board import game_cards

    lg = League(league) if league in {item.value for item in League} else None
    catalog = load_games()
    games = [g for g in catalog if lg is None or g.league == lg]
    season = RESEARCH_WINDOWS.hands_off
    book = load_book(season)
    cards, picks = (
        game_cards(
            games,
            Mode.SIMULATION,
            lg,
            season=season,
            predicted_winners=winners_by_game(book),
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
            games, season=inferred[0], week=inferred[1], mode=Mode.SIMULATION, league=lg
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
    book = Journal()
    stats = book.year(season)
    return {
        "banner": (
            "Journal — 2026 real tickets (Novig). Logging only; SBM never places a wager. "
            "Championship futures are not tracked."
        ),
        "season": season,
        "summary": stats.model_dump(),
        "tickets": book.rows_for_year(season),
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


def _predictions_payload(season: int, conference: str | None = None) -> dict:
    from sbm.data.store import load_games
    from sbm.predictions import bye_weeks, format_kickoff_cdt, leftovers_for
    from sbm.teams import (
        render_abbrev,
        render_display_name,
        render_logo_mark,
        render_logo_url,
        search_blob,
        team_color,
    )
    from sbm.web.board import is_international_venue

    book = _ensure_predictions(season)
    games_by_id = {g.game_id: g for g in load_games() if g.season == season}
    teams = book.teams
    if conference:
        if conference.lower() == "nfl":
            teams = [t for t in teams if t.league == League.NFL]
        else:
            teams = [t for t in teams if t.conference == conference]
    views = []
    for team in teams:
        data = team.model_dump(mode="json")
        data["logo_url"] = render_logo_url(team.league, team.team)
        data["logo_mark"] = render_logo_mark(team.league, team.team)
        data["display_name"] = render_display_name(team.league, team.team)
        data["abbrev"] = render_abbrev(team.league, team.team)
        data["color"] = team_color(team.league, team.team, team.conference)
        data["search_text"] = " ".join(
            [
                search_blob(team.league, team.team),
                render_display_name(team.league, team.team),
                render_abbrev(team.league, team.team),
                team.conference,
            ]
        ).lower()
        for row in data["games"]:
            away = row["opponent"] if row["is_home"] else team.team
            home = team.team if row["is_home"] else row["opponent"]
            raw_kick = row.get("kickoff")
            kickoff = None
            if isinstance(raw_kick, datetime):
                kickoff = raw_kick
            elif isinstance(raw_kick, str) and raw_kick:
                kickoff = datetime.fromisoformat(raw_kick.replace("Z", "+00:00"))
            row["away_team"] = away
            row["home_team"] = home
            row["away_abbrev"] = render_abbrev(team.league, away)
            row["home_abbrev"] = render_abbrev(team.league, home)
            row["opp_display"] = render_display_name(team.league, row["opponent"])
            row["away_logo_url"] = render_logo_url(team.league, away)
            row["home_logo_url"] = render_logo_url(team.league, home)
            row["opp_logo_url"] = render_logo_url(team.league, row["opponent"])
            row["away_logo_mark"] = render_logo_mark(team.league, away)
            row["home_logo_mark"] = render_logo_mark(team.league, home)
            row["opp_logo_mark"] = render_logo_mark(team.league, row["opponent"])
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
        row["team"] = render_display_name(League.CFB, row["team"])
        row["opponent"] = render_display_name(League.CFB, row["opponent"])
    return {
        "banner": (
            "Predictions — current-year W/L takes. Results fill in; picks never auto-flip. "
            "Reconsider is a warning, not a grade."
        ),
        "season": season,
        "conference": conference or "all",
        "teams": views,
        "leftovers": leftovers,
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
    from sbm.predictions import save_book, set_winner

    book = _ensure_predictions(body.season)
    try:
        updated = set_winner(book, body.game_id, body.predicted_winner)
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
