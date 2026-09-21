"""Season records from ingested finals. Not the league's official tiebreaker sheet."""

from __future__ import annotations

from dataclasses import dataclass, field

from sbm.schema import Game, League
from sbm.teams import cfb_p4_conference, nfl_conference, team_face

GROUPS = ("nfl", "B1G", "SEC", "ACC", "Big 12")


@dataclass
class TeamRecord:
    team: str
    league: League
    wins: int = 0
    losses: int = 0
    ties: int = 0
    conf_wins: int = 0
    conf_losses: int = 0
    conf_ties: int = 0
    points_for: int = 0
    points_against: int = 0
    opponents: list[tuple[str, int, int]] = field(default_factory=list)

    @property
    def played(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def win_pct(self) -> float:
        if self.played == 0:
            return -1.0
        return (self.wins + 0.5 * self.ties) / self.played

    @property
    def conf_played(self) -> int:
        return self.conf_wins + self.conf_losses + self.conf_ties

    @property
    def conf_pct(self) -> float:
        if self.conf_played == 0:
            return -1.0
        return (self.conf_wins + 0.5 * self.conf_ties) / self.conf_played

    @property
    def diff(self) -> int:
        return self.points_for - self.points_against


def _group_of(game: Game, team: str, *, home: bool) -> str | None:
    if game.league == League.NFL:
        return "nfl" if nfl_conference(team) else None
    conference = game.home_conference if home else game.away_conference
    mapped = cfb_p4_conference(team) or conference
    if mapped in GROUPS:
        return mapped
    return None


def _format_record(wins: int, losses: int, ties: int) -> str:
    if ties:
        return f"{wins}-{losses}-{ties}"
    return f"{wins}-{losses}"


def _h2h_pct(row: TeamRecord, group: set[str]) -> float | None:
    wins = losses = ties = 0
    others = group - {row.team}
    for opponent, scored, allowed in row.opponents:
        if opponent not in others:
            continue
        if scored > allowed:
            wins += 1
        elif scored < allowed:
            losses += 1
        else:
            ties += 1
    played = wins + losses + ties
    if played == 0:
        return None
    return (wins + 0.5 * ties) / played


def _partition(
    group: list[TeamRecord],
    key,
    names: dict[str, str],
    step: int,
) -> list[TeamRecord]:
    buckets: dict[float, list[TeamRecord]] = {}
    for row in group:
        buckets.setdefault(round(float(key(row)), 6), []).append(row)
    if len(buckets) == 1:
        return _break(group, names, step)
    ordered: list[TeamRecord] = []
    for bucket_key in sorted(buckets, reverse=True):
        chunk = buckets[bucket_key]
        if len(chunk) == 1:
            ordered.extend(chunk)
        else:
            ordered.extend(_break(chunk, names, step))
    return ordered


def _break(group: list[TeamRecord], names: dict[str, str], step: int) -> list[TeamRecord]:
    if len(group) <= 1:
        return list(group)
    if step == 0:
        teams = {row.team for row in group}
        pcts = [_h2h_pct(row, teams) for row in group]
        distinct = {round(pct, 6) for pct in pcts if pct is not None}
        if any(pct is None for pct in pcts) or len(distinct) <= 1:
            return _break(group, names, 1)
        buckets: dict[float, list[TeamRecord]] = {}
        for row, pct in zip(group, pcts, strict=True):
            assert pct is not None
            buckets.setdefault(round(pct, 6), []).append(row)
        ordered: list[TeamRecord] = []
        for pct in sorted(buckets, reverse=True):
            chunk = buckets[pct]
            ordered.extend(chunk if len(chunk) == 1 else _break(chunk, names, 1))
        return ordered
    if step == 1:
        return _partition(group, lambda row: row.conf_pct, names, 2)
    if step == 2:
        return _partition(group, lambda row: row.diff, names, 3)
    if step == 3:
        return _partition(group, lambda row: row.points_for, names, 4)
    return sorted(group, key=lambda row: names.get(row.team, row.team))


def standings(games: list[Game], season: int, group: str) -> list[TeamRecord]:
    """Order one group from finals already on hand."""
    if group not in GROUPS:
        return []
    rows: dict[str, TeamRecord] = {}
    for game in games:
        if game.season != season:
            continue
        sides = (
            (game.home_team, True, game.home_score, game.away_score),
            (game.away_team, False, game.away_score, game.home_score),
        )
        present = []
        for team, home, _scored, _allowed in sides:
            if _group_of(game, team, home=home) == group:
                present.append(team)
                rows.setdefault(team, TeamRecord(team, game.league))
        if not game.is_final or game.home_score is None or game.away_score is None:
            continue
        conference_game = len(present) == 2
        for team, home, scored, allowed in sides:
            row = rows.get(team)
            if row is None or scored is None or allowed is None:
                continue
            if scored > allowed:
                row.wins += 1
            elif scored < allowed:
                row.losses += 1
            else:
                row.ties += 1
            row.points_for += scored
            row.points_against += allowed
            opponent = game.away_team if home else game.home_team
            row.opponents.append((opponent, scored, allowed))
            if conference_game and group == "nfl":
                side = nfl_conference(team)
                other = nfl_conference(opponent)
                conference_game_for_team = side is not None and side == other
            else:
                conference_game_for_team = conference_game
            if conference_game_for_team:
                if scored > allowed:
                    row.conf_wins += 1
                elif scored < allowed:
                    row.conf_losses += 1
                else:
                    row.conf_ties += 1
    names = {
        team: team_face(row.league, team).display_name for team, row in rows.items()
    }
    played = [row for row in rows.values() if row.played]
    idle = [row for row in rows.values() if not row.played]
    buckets: dict[float, list[TeamRecord]] = {}
    for row in played:
        buckets.setdefault(round(row.win_pct, 6), []).append(row)
    ordered: list[TeamRecord] = []
    for pct in sorted(buckets, reverse=True):
        chunk = buckets[pct]
        ordered.extend(chunk if len(chunk) == 1 else _break(chunk, names, 0))
    idle.sort(key=lambda row: names.get(row.team, row.team))
    return ordered + idle


def record_text(row: TeamRecord) -> tuple[str, str]:
    overall = _format_record(row.wins, row.losses, row.ties)
    conference = _format_record(row.conf_wins, row.conf_losses, row.conf_ties)
    return overall, conference
