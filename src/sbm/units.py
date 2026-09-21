"""Season-to-date unit stats. A game only sees weeks strictly before it."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from sbm.config import LeagueParams
from sbm.paths import units_path
from sbm.schema import Game, League

PICKEM_BAND = 0.5


class UnitWeek(BaseModel):
    """Cumulative unit profile through `week` inclusive. Never includes that week's game."""

    league: League
    season: int
    week: int
    team: str
    rush_off: float | None = None
    rush_allowed: float | None = None
    pass_off: float | None = None
    pass_allowed: float | None = None
    sack_off: float | None = None
    sack_def: float | None = None
    line_yards: float | None = None
    stuff_def: float | None = None
    pass_success: float | None = None
    havoc_def: float | None = None
    talent: float | None = None


class UnitBook:
    def __init__(self, weeks: list[UnitWeek] | None = None) -> None:
        self.weeks = list(weeks or [])
        self._by_team: dict[tuple[str, int, str], list[UnitWeek]] = defaultdict(list)
        self._talent: dict[tuple[str, int, str], float] = {}
        for row in self.weeks:
            key = (row.league.value, row.season, row.team)
            self._by_team[key].append(row)
            if row.talent is not None:
                self._talent[key] = row.talent
        for rows in self._by_team.values():
            rows.sort(key=lambda row: row.week)

    def profile_before(self, league: League, team: str, season: int, week: int) -> UnitWeek | None:
        """Stats through the previous week, else last season, else nothing (league average)."""
        current = self._by_team.get((league.value, season, team), [])
        prior = [row for row in current if row.week < week]
        snap = prior[-1] if prior else None
        if snap is None:
            last = self._by_team.get((league.value, season - 1, team), [])
            snap = last[-1] if last else None
        talent = self._talent.get((league.value, season, team))
        if talent is None:
            talent = self._talent.get((league.value, season - 1, team))
        if snap is None and talent is None:
            return None
        if snap is None:
            return UnitWeek(league=league, season=season, week=0, team=team, talent=talent)
        if talent is None or snap.talent == talent:
            return snap
        return snap.model_copy(update={"talent": talent})


def _num(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def _pair(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    return left - right


def _run_edge(league: League, home: UnitWeek, away: UnitWeek) -> float:
    if league == League.NFL:
        return _pair(home.rush_off, away.rush_off) + _pair(away.rush_allowed, home.rush_allowed)
    yards = _pair(home.line_yards, away.line_yards) / 2.0
    stuff = _pair(home.stuff_def, away.stuff_def) * 4.0
    return yards + stuff


def _pass_edge(league: League, home: UnitWeek, away: UnitWeek) -> float:
    if league == League.NFL:
        epa = _pair(home.pass_off, away.pass_off) + _pair(away.pass_allowed, home.pass_allowed)
        sacks = 2.0 * (
            _pair(home.sack_def, away.sack_def) + _pair(away.sack_off, home.sack_off)
        )
        return epa + sacks
    return _pair(home.pass_success, away.pass_success) * 4.0 + _pair(
        home.havoc_def, away.havoc_def
    ) * 4.0


def _edge_label(league: League, name: str) -> str:
    if name == "talent":
        return "talent"
    if league == League.CFB and name == "run":
        return "run line yards vs stuff"
    if league == League.CFB and name == "pass":
        return "pass success vs havoc"
    if name == "run":
        return "run EPA"
    return "pass EPA"


def home_adjustment(
    game: Game, book: UnitBook | None, params: LeagueParams
) -> tuple[float, str | None]:
    """Points added to the home margin, and the largest unit edge, if any."""
    if book is None:
        return 0.0, None
    home = book.profile_before(game.league, game.home_team, game.season, game.week)
    away = book.profile_before(game.league, game.away_team, game.season, game.week)
    if home is None or away is None:
        return 0.0, None
    run = _run_edge(game.league, home, away)
    passing = _pass_edge(game.league, home, away)
    talent = 0.0
    if game.league == League.CFB and home.talent is not None and away.talent is not None:
        talent = (home.talent - away.talent) / 100.0
    weighted = {
        "run": params.run_weight * run,
        "pass": params.pass_weight * passing,
        "talent": params.talent_weight * talent,
    }
    raw = weighted["run"] + weighted["pass"] + weighted["talent"]
    cap = params.unit_cap
    capped = max(-cap, min(cap, raw))
    if any(abs(value) > 1e-9 for value in weighted.values()):
        best_name = max(weighted, key=lambda name: abs(weighted[name]))
    else:
        unweighted = {"run": run, "pass": passing}
        best_name = max(unweighted, key=lambda name: abs(unweighted[name]))
        if abs(unweighted[best_name]) < 1e-9:
            return 0.0, None
    return capped, _edge_label(game.league, best_name)


def load_unit_book(path: Path | None = None) -> UnitBook:
    dest = path or units_path()
    if not dest.exists():
        return UnitBook([])
    rows: list[UnitWeek] = []
    for line in dest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(UnitWeek.model_validate_json(line))
    return UnitBook(rows)


def save_units(
    weeks: list[UnitWeek],
    *,
    league: League,
    replace_seasons: set[int],
    path: Path | None = None,
) -> Path:
    dest = path or units_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = load_unit_book(dest).weeks if dest.exists() else []
    kept = [
        row
        for row in existing
        if not (row.league == league and row.season in replace_seasons)
    ]
    merged = sorted(
        kept + list(weeks),
        key=lambda row: (row.league.value, row.season, row.week, row.team),
    )
    with dest.open("w", encoding="utf-8") as fh:
        for row in merged:
            fh.write(row.model_dump_json() + "\n")
    return dest


class _Acc(BaseModel):
    n: float = 0.0
    total: float = 0.0

    def add(self, value: float | None, weight: float = 1.0) -> None:
        if value is None or weight <= 0:
            return
        self.n += weight
        self.total += value * weight

    def mean(self) -> float | None:
        if self.n <= 0:
            return None
        return self.total / self.n


def _mean_rows(samples: list[dict[str, float | None]]) -> dict[str, float | None]:
    keys = (
        "rush_off",
        "rush_allowed",
        "pass_off",
        "pass_allowed",
        "sack_off",
        "sack_def",
        "line_yards",
        "stuff_def",
        "pass_success",
        "havoc_def",
    )
    acc = {key: _Acc() for key in keys}
    for sample in samples:
        weight = float(sample.get("weight") or 1.0)
        for key in keys:
            acc[key].add(sample.get(key), weight)  # type: ignore[arg-type]
    return {key: acc[key].mean() for key in keys}


def _emit_cumulative(
    league: League,
    grouped: dict[tuple[int, str], dict[int, list[dict[str, float | None]]]],
    talent: dict[tuple[int, str], float],
) -> list[UnitWeek]:
    out: list[UnitWeek] = []
    for (season, team), by_week in grouped.items():
        running: list[dict[str, float | None]] = []
        for week in sorted(by_week):
            running.extend(by_week[week])
            means = _mean_rows(running)
            out.append(
                UnitWeek(
                    league=league,
                    season=season,
                    week=week,
                    team=team,
                    talent=talent.get((season, team)),
                    **means,
                )
            )
    return out


def nfl_unit_weeks(rows: list[dict], games: list[Game]) -> list[UnitWeek]:
    """Cumulative NFL EPA and sack rate from weekly offense rows plus the schedule."""
    opponents: dict[tuple[int, int, str], str] = {}
    for game in games:
        if game.league != League.NFL:
            continue
        opponents[(game.season, game.week, game.home_team)] = game.away_team
        opponents[(game.season, game.week, game.away_team)] = game.home_team

    offense: dict[tuple[int, int, str], dict[str, float | None]] = {}
    for row in rows:
        season_type = str(row.get("season_type") or row.get("seasonType") or "REG").upper()
        if season_type not in {"REG", "REGULAR"}:
            continue
        season = _num(row.get("season"))
        week = _num(row.get("week"))
        team = row.get("team") or row.get("team_abbr")
        if season is None or week is None or not team:
            continue
        raw_attempts = row.get("attempts")
        if raw_attempts is None:
            raw_attempts = row.get("passing_attempts")
        attempts = _num(raw_attempts)
        sacks = _num(row.get("sacks_suffered") if "sacks_suffered" in row else row.get("sacks"))
        carries = _num(row.get("carries"))
        dropbacks = None
        if attempts is not None:
            dropbacks = attempts + (sacks or 0.0)
        sack_rate = sacks / dropbacks if sacks is not None and dropbacks else None
        rush_total = _num(row.get("rushing_epa"))
        pass_total = _num(row.get("passing_epa"))
        rush_off = rush_total / carries if rush_total is not None and carries else rush_total
        pass_off = pass_total / dropbacks if pass_total is not None and dropbacks else pass_total
        offense[(int(season), int(week), str(team))] = {
            "rush_off": rush_off,
            "pass_off": pass_off,
            "sack_off": sack_rate,
        }

    grouped: dict[tuple[int, str], dict[int, list[dict[str, float | None]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (season, week, team), off in offense.items():
        foe = opponents.get((season, week, team))
        allowed = offense.get((season, week, foe)) if foe else None
        sample: dict[str, float | None] = {
            "rush_off": off.get("rush_off"),
            "pass_off": off.get("pass_off"),
            "sack_off": off.get("sack_off"),
            "rush_allowed": None if allowed is None else allowed.get("rush_off"),
            "pass_allowed": None if allowed is None else allowed.get("pass_off"),
            "sack_def": None if allowed is None else allowed.get("sack_off"),
            "weight": 1.0,
        }
        grouped[(season, team)][week].append(sample)
    return _emit_cumulative(League.NFL, grouped, {})


def _dig(payload: dict, *path: str) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def cfb_unit_weeks(games: list[dict], talent_rows: list[dict]) -> list[UnitWeek]:
    """Cumulative CFB advanced stats. Talent is the preseason composite for that season."""
    talent: dict[tuple[int, str], float] = {}
    for row in talent_rows:
        year = _num(row.get("year") if row.get("year") is not None else row.get("season"))
        team = row.get("team") or row.get("school")
        value = _num(row.get("talent"))
        if year is None or not team or value is None:
            continue
        talent[(int(year), str(team))] = value

    grouped: dict[tuple[int, str], dict[int, list[dict[str, float | None]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for game in games:
        season = _num(game.get("season") if game.get("season") is not None else game.get("year"))
        week = _num(game.get("week"))
        team = game.get("team")
        if season is None or week is None or not team:
            continue
        off_plays = _num(_dig(game, "offense", "plays")) or 1.0
        def_plays = _num(_dig(game, "defense", "plays")) or off_plays
        sample: dict[str, float | None] = {
            "line_yards": _num(_dig(game, "offense", "lineYards")),
            "stuff_def": _num(_dig(game, "defense", "stuffRate")),
            "pass_success": _num(_dig(game, "offense", "passingPlays", "successRate")),
            "havoc_def": _num(_dig(game, "defense", "havoc", "frontSeven")),
            "weight": max(off_plays, def_plays, 1.0),
        }
        grouped[(int(season), str(team))][int(week)].append(sample)
    return _emit_cumulative(League.CFB, grouped, talent)


def favorite_side(home_margin: float, away_team: str, home_team: str) -> tuple[str | None, float]:
    """Favorite and the points they lay. Favorite is unset inside half a point."""
    if abs(home_margin) < PICKEM_BAND:
        return None, abs(home_margin)
    if home_margin > 0:
        return home_team, home_margin
    return away_team, -home_margin
