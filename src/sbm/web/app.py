from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sbm.config import get_settings
from sbm.mode import Mode, parse_mode
from sbm.paper import Ledger
from sbm.schema import League

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


def _board_payload(mode: Mode, league: str | None = None) -> dict:
    from sbm.data.store import load_games
    from sbm.web.board import game_cards

    lg = League(league) if league in {item.value for item in League} else None
    games = load_games(lg)
    cards, picks = game_cards(games, mode, lg) if games else ([], [])
    slate_bits = []
    seen: set[tuple[str, int, int]] = set()
    for card in cards:
        key = (card["league"], card["season"], card["week"])
        if key in seen:
            continue
        seen.add(key)
        slate_bits.append(f"{card['league'].upper()} {card['season']} Week {card['week']}")
    ledger = Ledger(mode)
    summary = ledger.summary()
    curve = ledger.curve()
    return {
        "mode": mode.value,
        "banner": _banner(mode),
        "slate_label": " · ".join(slate_bits) if slate_bits else "No current slate",
        "cards": cards,
        "picks": [p.model_dump(mode="json") for p in picks],
        "summary": summary.model_dump(),
        "curve": [p.model_dump() for p in curve],
        "ledger": [e.model_dump(mode="json") for e in ledger.load()[-80:]],
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
