from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from sbm.config import RESEARCH_WINDOWS, get_settings
from sbm.mode import Mode, parse_mode
from sbm.paper import Ledger
from sbm.paths import ledger_path
from sbm.schema import League, Market, Side, StakeColumn
from sbm.teams import book_ticket_label

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

app = FastAPI(title="SBM", description="NFL + CFB paper betting model")
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


def _mode(value: str) -> Mode:
    try:
        return parse_mode(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _banner(mode: Mode) -> str:
    if mode == Mode.SIMULATION:
        return "Simulation — fake bets / research. Real-money wagers stay outside this app."
    settings = get_settings()
    if settings.live_practice:
        return "LIVE (practice) — 2027-shaped board. Not this year's real book."
    return "LIVE — practice complete; treat this as the 2027 workflow."


class MarkRequest(BaseModel):
    mode: str
    game_id: str
    market: str
    column: str
    skipped: bool = False
    side: str | None = Field(default=None)


class UnmarkRequest(BaseModel):
    mode: str
    game_id: str
    market: str
    column: str


def _board_payload(mode: Mode, league: str | None = None) -> dict:
    from sbm.backtest import infer_current_week
    from sbm.data.store import load_games
    from sbm.errors import week_error_report
    from sbm.web.board import game_cards

    lg = League(league) if league in {item.value for item in League} else None
    catalog = load_games()
    games = [g for g in catalog if lg is None or g.league == lg]
    ledger = Ledger(mode, path=ledger_path(mode))
    diary_season = RESEARCH_WINDOWS.hands_off if mode == Mode.SIMULATION else None
    cards, picks = (
        game_cards(games, mode, lg, ledger=ledger, season=diary_season) if games else ([], [])
    )
    slate_bits = []
    seen: set[tuple[str, int, int]] = set()
    for card in cards:
        key = (card["league"], card["season"], card["week"])
        if key in seen:
            continue
        seen.add(key)
        slate_bits.append(f"{card['league'].upper()} {card['season']} Week {card['week']}")
    summary = ledger.summary(season=diary_season)
    curve = ledger.curve(season=diary_season)
    games_by_id = {game.game_id: game for game in catalog}
    book = []
    for entry in ledger.load():
        if entry.pick.skipped:
            continue
        if diary_season is not None and entry.pick.season != diary_season:
            continue
        game = games_by_id.get(entry.pick.game_id)
        away = game.away_team if game is not None else ""
        home = game.home_team if game is not None else ""
        book.append(
            {
                "game_id": entry.pick.game_id,
                "column": entry.pick.column.value,
                "label": book_ticket_label(
                    column=entry.pick.column.value,
                    league=entry.pick.league,
                    week=entry.pick.week,
                    away_team=away,
                    home_team=home,
                    team_or_side=entry.pick.team_or_side,
                    market=entry.pick.market.value,
                ),
                "settled": entry.result is not None,
                "result": entry.result,
                "market": entry.pick.market.value,
            }
        )
    errors = None
    inferred = infer_current_week(games, season=diary_season) if games else None
    if inferred is not None:
        errors = week_error_report(
            games, season=inferred[0], week=inferred[1], mode=mode, league=lg
        ).model_dump(mode="json")
    return {
        "mode": mode.value,
        "banner": _banner(mode),
        "slate_label": " · ".join(slate_bits) if slate_bits else "No current slate",
        "cards": cards,
        "picks": [p.model_dump(mode="json") for p in picks],
        "summary": summary.model_dump(),
        "curve": [p.model_dump() for p in curve],
        "ledger": [e.model_dump(mode="json") for e in ledger.load()[-80:]],
        "errors": errors,
        "book": book,
        "has_games": bool(games),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request, mode: str = "simulation", league: str | None = None) -> HTMLResponse:
    parsed = _mode(mode)
    payload = _board_payload(parsed, league)
    return templates.TemplateResponse(
        request,
        "board.html",
        {
            **payload,
            "league": league or "all",
            "modes": [m.value for m in Mode],
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/board")
def api_board(mode: str = "simulation", league: str | None = None) -> JSONResponse:
    return JSONResponse(
        _board_payload(_mode(mode), league),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/mark")
def api_mark(body: MarkRequest) -> JSONResponse:
    from sbm.backtest import current_slate
    from sbm.data.store import games_by_id, load_games
    from sbm.picks import pick_from_market_side

    parsed = _mode(body.mode)
    try:
        market = Market(body.market)
        column = StakeColumn(body.column)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    side = None
    if body.side:
        try:
            side = Side(body.side)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    games = load_games()
    game = games_by_id(games).get(body.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if body.skipped:
        raise HTTPException(
            status_code=400,
            detail="Skip is unused; leave the market unmarked",
        )
    if side is None:
        raise HTTPException(status_code=400, detail="Side is required")
    pin_season = RESEARCH_WINDOWS.hands_off if parsed == Mode.SIMULATION else None
    slate, model_picks, _ = current_slate(games, mode=parsed, season=pin_season)
    pred = next((item[1] for item in slate if item[0].game_id == body.game_id), None)
    model_ticket = next(
        (p for p in model_picks if p.game_id == body.game_id and p.market == market),
        None,
    )
    try:
        if column == StakeColumn.SYSTEM:
            if model_ticket is None:
                raise ValueError("No model ticket on this market")
            if side != model_ticket.side:
                raise ValueError("System must follow the model ticket")
            source = model_ticket.model_copy(
                update={"mode": parsed, "column": StakeColumn.SYSTEM, "skipped": False}
            )
        else:
            source = pick_from_market_side(
                game,
                pred,
                mode=parsed,
                market=market,
                side=side,
                column=column,
                skipped=False,
            )
        entry = Ledger(parsed, path=ledger_path(parsed)).mark(
            game_id=body.game_id,
            market=market,
            column=column,
            skipped=False,
            side=source.side,
            team_or_side=source.team_or_side,
            source=source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(entry.model_dump(mode="json"))


@app.post("/api/unmark")
def api_unmark(body: UnmarkRequest) -> JSONResponse:
    parsed = _mode(body.mode)
    try:
        market = Market(body.market)
        column = StakeColumn(body.column)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        Ledger(parsed, path=ledger_path(parsed)).drop(
            game_id=body.game_id,
            market=market,
            column=column,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"ok": True})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
