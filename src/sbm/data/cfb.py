from __future__ import annotations

from datetime import UTC, datetime

import httpx

from sbm.config import get_settings
from sbm.schema import Game, League
from sbm.teams import normalize_cfb_conference

CFBD_BASE = "https://api.collegefootballdata.com"


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def _parse_kickoff(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


def _is_fbs_game(game: dict) -> bool:
    """Keep games with at least one FBS team so P4 vs FCS week 0/1 still ingest."""
    home_class = (game.get("homeClassification") or game.get("home_classification") or "").lower()
    away_class = (game.get("awayClassification") or game.get("away_classification") or "").lower()
    if not home_class:
        home_class = (game.get("homeDivision") or game.get("home_division") or "").lower()
    if not away_class:
        away_class = (game.get("awayDivision") or game.get("away_division") or "").lower()
    if home_class or away_class:
        return home_class == "fbs" or away_class == "fbs"
    return False


def _consensus_line(lines: list[dict]) -> tuple[float | None, float | None, int | None, int | None]:
    if not lines:
        return None, None, None, None
    preferred = None
    for item in lines:
        provider = str(item.get("provider") or item.get("formattedSpread") or "")
        if "consensus" in provider.lower() or provider.lower() == "draftkings":
            preferred = item
            break
    item = preferred or lines[0]
    spread = item.get("spread")
    total = item.get("overUnder") or item.get("over_under")
    home_ml = item.get("homeMoneyline") or item.get("home_moneyline")
    away_ml = item.get("awayMoneyline") or item.get("away_moneyline")
    try:
        spread_f = float(spread) if spread is not None else None
    except (TypeError, ValueError):
        spread_f = None
    try:
        total_f = float(total) if total is not None else None
    except (TypeError, ValueError):
        total_f = None
    try:
        home_ml_i = int(home_ml) if home_ml is not None else None
    except (TypeError, ValueError):
        home_ml_i = None
    try:
        away_ml_i = int(away_ml) if away_ml is not None else None
    except (TypeError, ValueError):
        away_ml_i = None
    # CFBD spread is typically from the home team's perspective (negative = home favored).
    return spread_f, total_f, home_ml_i, away_ml_i


def games_from_cfbd_payloads(games_payload: list[dict], lines_payload: list[dict]) -> list[Game]:
    lines_by_id: dict[str, list[dict]] = {}
    for row in lines_payload:
        gid = str(row.get("id") or row.get("gameId") or "")
        raw_lines = row.get("lines") or []
        if gid:
            lines_by_id[gid] = raw_lines

    out: list[Game] = []
    for raw in games_payload:
        if not _is_fbs_game(raw):
            continue
        season_type = str(raw.get("seasonType") or raw.get("season_type") or "regular").lower()
        if season_type not in {"regular", "postseason"}:
            continue
        gid = str(raw.get("id"))
        season = int(raw["season"])
        week = int(raw.get("week") or 0)
        home = str(raw.get("homeTeam") or raw.get("home_team"))
        away = str(raw.get("awayTeam") or raw.get("away_team"))
        spread, total, home_ml, away_ml = _consensus_line(
            lines_by_id.get(gid, raw.get("lines") or [])
        )
        home_score = raw.get("homePoints")
        if home_score is None:
            home_score = raw.get("home_points")
        away_score = raw.get("awayPoints")
        if away_score is None:
            away_score = raw.get("away_points")
        venue_raw = raw.get("venue") or raw.get("venueName") or raw.get("venue_name")
        venue = str(venue_raw).strip() if venue_raw else None
        out.append(
            Game(
                game_id=f"cfb-{gid}",
                league=League.CFB,
                season=season,
                week=week,
                home_team=home,
                away_team=away,
                kickoff=_parse_kickoff(raw.get("startDate") or raw.get("start_date")),
                home_score=int(home_score) if home_score is not None else None,
                away_score=int(away_score) if away_score is not None else None,
                spread_close=spread,
                total_close=total,
                home_moneyline=home_ml,
                away_moneyline=away_ml,
                is_neutral=bool(raw.get("neutralSite") or raw.get("neutral_site") or False),
                venue=venue,
                home_conference=normalize_cfb_conference(
                    raw.get("homeConference") or raw.get("home_conference")
                ),
                away_conference=normalize_cfb_conference(
                    raw.get("awayConference") or raw.get("away_conference")
                ),
            )
        )
    return out


def download_cfb_advanced(seasons: list[int], api_key: str | None = None) -> list[dict]:
    """Per-game advanced stats. Callers cumulative-sum through the previous week only."""
    key = api_key if api_key is not None else get_settings().cfbd_api_key
    if not key:
        raise RuntimeError(
            "CFBD_API_KEY is required to ingest college football. Copy .env.example to .env."
        )
    rows: list[dict] = []
    with httpx.Client(timeout=60.0, headers=_headers(key)) as client:
        for season in seasons:
            resp = client.get(f"{CFBD_BASE}/stats/game/advanced", params={"year": season})
            resp.raise_for_status()
            payload = resp.json() or []
            for row in payload:
                if "season" not in row and "year" not in row:
                    row = {**row, "season": season}
                rows.append(row)
    return rows


def download_cfb_talent(seasons: list[int], api_key: str | None = None) -> list[dict]:
    key = api_key if api_key is not None else get_settings().cfbd_api_key
    if not key:
        raise RuntimeError(
            "CFBD_API_KEY is required to ingest college football. Copy .env.example to .env."
        )
    rows: list[dict] = []
    with httpx.Client(timeout=60.0, headers=_headers(key)) as client:
        for season in seasons:
            resp = client.get(f"{CFBD_BASE}/talent", params={"year": season})
            resp.raise_for_status()
            for row in resp.json() or []:
                rows.append({**row, "year": row.get("year", season)})
    return rows


def download_cfb_games(seasons: list[int], api_key: str | None = None) -> list[Game]:
    key = api_key if api_key is not None else get_settings().cfbd_api_key
    if not key:
        raise RuntimeError(
            "CFBD_API_KEY is required to ingest college football. Copy .env.example to .env."
        )
    games: list[Game] = []
    with httpx.Client(timeout=60.0, headers=_headers(key)) as client:
        for season in seasons:
            for season_type in ("regular", "postseason"):
                g_resp = client.get(
                    f"{CFBD_BASE}/games",
                    params={"year": season, "seasonType": season_type, "classification": "fbs"},
                )
                g_resp.raise_for_status()
                l_resp = client.get(
                    f"{CFBD_BASE}/lines",
                    params={"year": season, "seasonType": season_type},
                )
                l_resp.raise_for_status()
                games.extend(games_from_cfbd_payloads(g_resp.json() or [], l_resp.json() or []))
    return games
