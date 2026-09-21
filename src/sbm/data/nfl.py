from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from sbm.schema import Game, League
from sbm.teams import NFL_CONFERENCE

EASTERN = ZoneInfo("America/New_York")


def _to_int(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _kickoff(row: pd.Series) -> datetime | None:
    day = row.get("gameday")
    time = row.get("gametime")
    if pd.isna(day) or day is None:
        return None
    day_s = str(day)
    time_s = "00:00" if time is None or pd.isna(time) else str(time)
    try:
        dt = datetime.fromisoformat(f"{day_s}T{time_s}")
        return dt.replace(tzinfo=EASTERN)
    except ValueError:
        try:
            return datetime.strptime(day_s, "%Y-%m-%d").replace(tzinfo=EASTERN)
        except ValueError:
            return None


def _home_spread(spread_line: object) -> float | None:
    """nflverse spread_line is predicted home margin (positive = home favored)."""
    margin = _to_float(spread_line)
    if margin is None:
        return None
    return -margin


def _venue(row: pd.Series) -> str | None:
    stadium = row.get("stadium")
    if stadium is None or (isinstance(stadium, float) and pd.isna(stadium)):
        return None
    text = str(stadium).strip()
    return text or None


def schedules_to_games(df: pd.DataFrame) -> list[Game]:
    """
    Convert nflverse schedules into Game rows.

    nflverse `spread_line` is the expected home margin (positive = home favored).
    We store `spread_close` as a sportsbook home line (negative = home favored).
    """
    games: list[Game] = []
    for _, row in df.iterrows():
        game_type = str(row.get("game_type") or "REG")
        if game_type not in {"REG", "WC", "DIV", "CON", "SB", "POST"}:
            continue
        season = int(row["season"])
        week = int(row["week"])
        home = str(row["home_team"])
        away = str(row["away_team"])
        raw_id = row.get("game_id")
        if raw_id is not None and not pd.isna(raw_id):
            game_id = str(raw_id)
        else:
            game_id = f"nfl-{season}-{week}-{away}-{home}"
        games.append(
            Game(
                game_id=game_id,
                league=League.NFL,
                season=season,
                week=week,
                home_team=home,
                away_team=away,
                kickoff=_kickoff(row),
                home_score=_to_int(row.get("home_score")),
                away_score=_to_int(row.get("away_score")),
                spread_close=_home_spread(row.get("spread_line")),
                total_close=_to_float(row.get("total_line")),
                home_moneyline=_to_int(row.get("home_moneyline")),
                away_moneyline=_to_int(row.get("away_moneyline")),
                home_rest_days=_to_int(row.get("home_rest")),
                away_rest_days=_to_int(row.get("away_rest")),
                venue=_venue(row),
                home_conference=NFL_CONFERENCE.get(home),
                away_conference=NFL_CONFERENCE.get(away),
            )
        )
    return games


NFLVERSE_GAMES_CSV = (
    "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
)


NFLVERSE_TEAM_STATS = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_team/stats_team_week_{season}.csv"
)


def download_nfl_team_stats(seasons: list[int]) -> list[dict]:
    """Weekly offense EPA and sack counts. Defense is the opponent's offense that week."""
    from urllib.error import HTTPError

    rows: list[dict] = []
    for season in seasons:
        url = NFLVERSE_TEAM_STATS.format(season=season)
        try:
            frame = pd.read_csv(url)
        except HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        frame["season"] = season
        rows.extend(frame.to_dict(orient="records"))
    return rows


def download_nfl_games(seasons: list[int]) -> list[Game]:
    """Pull official nflverse schedules (results + closing lines). No third-party wrapper."""
    df = pd.read_csv(NFLVERSE_GAMES_CSV)
    if "season" not in df.columns:
        raise RuntimeError("Unexpected nflverse games.csv schema")
    df = df[df["season"].isin(seasons)]
    return schedules_to_games(df)
