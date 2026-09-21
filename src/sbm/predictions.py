"""Current-year schedule W/L takes. Never overwrites predicted_winner with results."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sbm.config import RESEARCH_WINDOWS
from sbm.paths import predictions_path
from sbm.schema import (
    Game,
    League,
    LineAudit,
    SeasonGameTake,
    SeasonPredictions,
    TeamSeasonTake,
)
from sbm.teams import NFL_CONFERENCE, NFL_DISPLAY, abbrev, cfb_p4_conference, is_p4_conference
from sbm.units import favorite_side

RECONSIDER_MIN_PICKED = 3
COVER_MOVE_POINTS = 3.0


def _book(
    book: SeasonPredictions,
    teams: list[TeamSeasonTake],
    audits: list[LineAudit] | None = None,
) -> SeasonPredictions:
    return SeasonPredictions(
        season=book.season,
        teams=teams,
        audits=book.audits if audits is None else audits,
    )
RECONSIDER_MAX_HIT_RATE = 0.4


CHICAGO = ZoneInfo("America/Chicago")
EASTERN = ZoneInfo("America/New_York")


def kickoff_in_chicago(kickoff: datetime | None, league: League | None = None) -> datetime | None:
    """Kickoff in America/Chicago. NFL times tagged UTC are Eastern wall clock."""
    if kickoff is None:
        return None
    if kickoff.tzinfo is None:
        attached = EASTERN if league == League.NFL else UTC
        aware = kickoff.replace(tzinfo=attached)
    elif league == League.NFL and kickoff.utcoffset() == timedelta(0):
        # nflverse gametime is Eastern; older ingest tagged it UTC.
        aware = kickoff.replace(tzinfo=EASTERN)
    else:
        aware = kickoff
    return aware.astimezone(CHICAGO)


def kickoff_iso(kickoff: datetime | None, league: League | None = None) -> str | None:
    """Corrected kickoff instant as UTC ISO, for the browser to format locally."""
    local = kickoff_in_chicago(kickoff, league)
    if local is None:
        return None
    return local.astimezone(UTC).isoformat()


def format_kickoff_cdt(kickoff: datetime | None, league: League | None = None) -> str | None:
    """Weekday and local kickoff in America/Chicago (CDT or CST)."""
    local = kickoff_in_chicago(kickoff, league)
    if local is None:
        return None
    hour = local.strftime("%I").lstrip("0") or "0"
    return f"{local:%a} {hour}:{local:%M %p %Z}"


def team_key(league: League, team: str) -> str:
    if league == League.NFL:
        return abbrev(league, team)
    return team.strip().lower()


def conference_for(game: Game, team: str) -> str | None:
    if game.league == League.NFL:
        return NFL_CONFERENCE.get(abbrev(League.NFL, team))
    mapped = cfb_p4_conference(team)
    if mapped:
        return mapped
    if team == game.home_team:
        return game.home_conference
    if team == game.away_team:
        return game.away_conference
    return None


def is_cfb_leftover(game: Game, team: str) -> bool:
    if game.league != League.CFB:
        return False
    mine = conference_for(game, team)
    opp = game.away_team if team == game.home_team else game.home_team
    theirs = conference_for(game, opp)
    if not is_p4_conference(mine) or not is_p4_conference(theirs):
        return True
    return mine != theirs


def load_book(season: int | None = None) -> SeasonPredictions | None:
    year = season if season is not None else RESEARCH_WINDOWS.hands_off
    path = predictions_path(year)
    if not path.exists():
        return None
    return SeasonPredictions.model_validate_json(path.read_text(encoding="utf-8"))


def save_book(book: SeasonPredictions) -> None:
    path = predictions_path(book.season)
    path.write_text(book.model_dump_json(indent=2), encoding="utf-8")


def winners_by_game(book: SeasonPredictions | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if book is None:
        return out
    for team in book.teams:
        for row in team.games:
            if row.predicted_winner:
                out[row.game_id] = row.predicted_winner
    return out


def _games_for_season(games: list[Game], season: int) -> list[Game]:
    return [g for g in games if g.season == season]


def _cfb_team_conference(games: list[Game], team: str) -> str | None:
    counts: Counter[str] = Counter()
    for game in games:
        conf = conference_for(game, team)
        if is_p4_conference(conf) and conf is not None:
            counts[conf] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _schedule_rows(games: list[Game], team: str, league: League) -> list[SeasonGameTake]:
    rows: list[SeasonGameTake] = []
    for game in games:
        if game.home_team != team and game.away_team != team:
            continue
        is_home = game.home_team == team
        opponent = game.away_team if is_home else game.home_team
        actual = None
        if game.is_final:
            if game.home_score == game.away_score:
                actual = None
            else:
                actual = (
                    game.home_team
                    if (game.home_score or 0) > (game.away_score or 0)
                    else game.away_team
                )
        rows.append(
            SeasonGameTake(
                game_id=game.game_id,
                week=game.week,
                opponent=opponent,
                is_home=is_home,
                actual_winner=actual,
                leftover=is_cfb_leftover(game, team),
                kickoff=game.kickoff,
            )
        )
    rows.sort(key=lambda r: (r.week, r.game_id))
    return rows


def init_book(games: list[Game], season: int | None = None) -> SeasonPredictions:
    year = season if season is not None else RESEARCH_WINDOWS.hands_off
    slate = _games_for_season(games, year)
    existing = load_book(year)
    kept: dict[tuple[str, str], TeamSeasonTake] = {}
    if existing is not None:
        for team in existing.teams:
            kept[(team.league.value, team_key(team.league, team.team))] = team

    teams: list[TeamSeasonTake] = []
    for code in NFL_DISPLAY:
        nfl_games = [g for g in slate if g.league == League.NFL]
        rows = _schedule_rows(nfl_games, code, League.NFL)
        if not rows:
            continue
        prior = kept.get((League.NFL.value, code))
        teams.append(_merge_team(prior, code, League.NFL, NFL_CONFERENCE[code], rows))

    cfb_games = [g for g in slate if g.league == League.CFB]
    cfb_names: set[str] = set()
    for game in cfb_games:
        for name, conf in (
            (game.home_team, game.home_conference),
            (game.away_team, game.away_conference),
        ):
            if is_p4_conference(cfb_p4_conference(name) or conf):
                cfb_names.add(name)
    for name in sorted(cfb_names, key=str.lower):
        conf = _cfb_team_conference(cfb_games, name)
        if not is_p4_conference(conf) or conf is None:
            continue
        rows = _schedule_rows(cfb_games, name, League.CFB)
        prior = kept.get((League.CFB.value, team_key(League.CFB, name)))
        teams.append(_merge_team(prior, name, League.CFB, conf, rows))

    audits = existing.audits if existing is not None else []
    book = SeasonPredictions(season=year, teams=teams, audits=audits)
    return annotate_heatmap(book)


def _merge_team(
    prior: TeamSeasonTake | None,
    team: str,
    league: League,
    conference: str,
    rows: list[SeasonGameTake],
) -> TeamSeasonTake:
    old_by_id: dict[str, SeasonGameTake] = {}
    if prior is not None:
        old_by_id = {g.game_id: g for g in prior.games}
    merged: list[SeasonGameTake] = []
    for row in rows:
        old = old_by_id.get(row.game_id)
        if old is not None:
            row = row.model_copy(
                update={
                    "predicted_winner": old.predicted_winner,
                    "pick_kind": old.pick_kind,
                    "cover_favorite": old.cover_favorite,
                    "cover_line": old.cover_line,
                    "leftover": row.leftover,
                }
            )
        merged.append(row)
    return TeamSeasonTake(
        team=team,
        league=league,
        conference=conference,
        note=prior.note if prior is not None else None,
        games=merged,
    )


def sync_actuals(book: SeasonPredictions, games: list[Game]) -> SeasonPredictions:
    by_id = {g.game_id: g for g in games if g.season == book.season}
    updated: list[TeamSeasonTake] = []
    for team in book.teams:
        rows: list[SeasonGameTake] = []
        for row in team.games:
            game = by_id.get(row.game_id)
            actual = row.actual_winner
            leftover = row.leftover
            if game is not None:
                leftover = leftover or is_cfb_leftover(game, team.team)
                if game.is_final and game.home_score != game.away_score:
                    actual = (
                        game.home_team
                        if (game.home_score or 0) > (game.away_score or 0)
                        else game.away_team
                    )
                elif game.is_final:
                    actual = None
                rows.append(
                    row.model_copy(
                        update={
                            "actual_winner": actual,
                            "leftover": leftover,
                            "predicted_winner": row.predicted_winner,
                            "kickoff": game.kickoff,
                            "week": game.week,
                        }
                    )
                )
            else:
                rows.append(row)
        updated.append(team.model_copy(update={"games": rows}))
    return annotate_heatmap(_book(book, updated))


def annotate_heatmap(book: SeasonPredictions) -> SeasonPredictions:
    teams: list[TeamSeasonTake] = []
    for team in book.teams:
        n_played = 0
        actual_wins = 0
        picked_to_win = 0
        picked_hits = 0
        for row in team.games:
            if not row.actual_winner:
                continue
            n_played += 1
            if row.actual_winner == team.team:
                actual_wins += 1
            if row.predicted_winner == team.team:
                picked_to_win += 1
                if row.actual_winner == team.team:
                    picked_hits += 1
        hit_rate = picked_hits / picked_to_win if picked_to_win else 1.0
        reconsider = (
            picked_to_win >= RECONSIDER_MIN_PICKED and hit_rate <= RECONSIDER_MAX_HIT_RATE
        )
        teams.append(
            team.model_copy(
                update={
                    "reconsider": reconsider,
                    "predicted_wins_played": picked_to_win,
                    "actual_wins": actual_wins,
                    "n_played": n_played,
                }
            )
        )
    return _book(book, teams)


def set_winner(book: SeasonPredictions, game_id: str, winner: str) -> SeasonPredictions:
    teams: list[TeamSeasonTake] = []
    found = False
    for team in book.teams:
        rows: list[SeasonGameTake] = []
        for row in team.games:
            if row.game_id == game_id:
                found = True
                allowed = {team.team, row.opponent}
                if winner not in allowed:
                    raise ValueError(f"{winner} is not playing in {game_id}")
                rows.append(
                    row.model_copy(
                        update={
                            "predicted_winner": winner,
                            "pick_kind": "outright",
                            "cover_favorite": None,
                            "cover_line": None,
                        }
                    )
                )
            else:
                rows.append(row)
        teams.append(team.model_copy(update={"games": rows}))
    if not found:
        raise ValueError(f"Unknown game {game_id}")
    return annotate_heatmap(_book(book, teams))


def bye_weeks(games: list[SeasonGameTake], league: League) -> list[int]:
    """Weeks with no game on this team's Predictions card."""
    weeks = sorted({row.week for row in games})
    if not weeks:
        return []
    if league == League.NFL:
        return [w for w in range(1, 19) if w not in weeks]
    lo, hi = weeks[0], weeks[-1]
    return [w for w in range(lo, hi + 1) if w not in weeks]


def _token_matches_team(league: League, team: str, token: str) -> bool:
    raw = token.strip()
    if not raw:
        return False
    if team_key(league, team) == team_key(league, raw):
        return True
    code = abbrev(league, team).upper()
    tok = raw.upper()
    if code == tok:
        return True
    return len(code) >= 3 and len(tok) >= 3 and (code.startswith(tok) or tok.startswith(code))


def _wrong_pick_for_row(
    league: League,
    team: str,
    opponent: str,
    wrong_matchups: list[tuple[str, str]],
) -> str | None:
    for left, right in wrong_matchups:
        left_team = _token_matches_team(league, team, left)
        left_opp = _token_matches_team(league, opponent, left)
        right_team = _token_matches_team(league, team, right)
        right_opp = _token_matches_team(league, opponent, right)
        if left_team and right_opp:
            return team
        if left_opp and right_team:
            return opponent
    return None


def fill_unpicked_finals(
    book: SeasonPredictions,
    conference: str,
    wrong_matchups: list[tuple[str, str]],
) -> tuple[SeasonPredictions, int, int]:
    """Blank finals in a conference: hit unless listed as a wrong call. Does not overwrite picks."""
    fills: dict[str, str] = {}
    misses = 0
    for team in book.teams:
        if team.conference != conference:
            continue
        for row in team.games:
            if row.predicted_winner or not row.actual_winner:
                continue
            if row.game_id in fills:
                continue
            wrong = _wrong_pick_for_row(team.league, team.team, row.opponent, wrong_matchups)
            if wrong:
                fills[row.game_id] = wrong
                misses += 1
            else:
                fills[row.game_id] = row.actual_winner
    updated = book
    for game_id, winner in fills.items():
        updated = set_winner(updated, game_id, winner)
    return updated, len(fills), misses


def apply_called_misses(
    book: SeasonPredictions,
    matchups: list[tuple[str, str]],
) -> tuple[SeasonPredictions, int]:
    """Listed matchups were wrong: pick the actual loser. Overwrites existing takes."""
    fills: dict[str, str] = {}
    for team in book.teams:
        for row in team.games:
            if not row.actual_winner or row.game_id in fills:
                continue
            if not any(
                (
                    _token_matches_team(team.league, team.team, left)
                    and _token_matches_team(team.league, row.opponent, right)
                )
                or (
                    _token_matches_team(team.league, team.team, right)
                    and _token_matches_team(team.league, row.opponent, left)
                )
                for left, right in matchups
            ):
                continue
            loser = (
                row.opponent if row.actual_winner == team.team else team.team
            )
            fills[row.game_id] = loser
    updated = book
    for game_id, winner in fills.items():
        updated = set_winner(updated, game_id, winner)
    return updated, len(fills)


def set_note(
    book: SeasonPredictions, team: str, league: League, note: str | None
) -> SeasonPredictions:
    key = team_key(league, team)
    teams: list[TeamSeasonTake] = []
    found = False
    for item in book.teams:
        if item.league == league and team_key(item.league, item.team) == key:
            found = True
            teams.append(item.model_copy(update={"note": note}))
        else:
            teams.append(item)
    if not found:
        raise ValueError(f"Unknown team {team}")
    return _book(book, teams)


def set_pick(
    book: SeasonPredictions,
    game_id: str,
    choice: str,
    *,
    home_margin: float,
    away_team: str,
    home_team: str,
) -> SeasonPredictions:
    """Store an outright team or a Cover snapshot against the live model number."""
    if choice not in {"away", "home", "cover"}:
        raise ValueError(f"Unknown choice {choice}")
    favorite, laying = favorite_side(home_margin, away_team, home_team)
    if choice == "cover":
        if favorite is None:
            raise ValueError("Cover is not a pick inside half a point")
        update = {
            "predicted_winner": favorite,
            "pick_kind": "cover",
            "cover_favorite": favorite,
            "cover_line": round(laying, 4),
        }
    else:
        winner = away_team if choice == "away" else home_team
        update = {
            "predicted_winner": winner,
            "pick_kind": "outright",
            "cover_favorite": None,
            "cover_line": None,
        }
    teams: list[TeamSeasonTake] = []
    found = False
    for team in book.teams:
        rows: list[SeasonGameTake] = []
        for row in team.games:
            if row.game_id == game_id:
                found = True
                rows.append(row.model_copy(update=update))
            else:
                rows.append(row)
        teams.append(team.model_copy(update={"games": rows}))
    if not found:
        raise ValueError(f"Unknown game {game_id}")
    return annotate_heatmap(_book(book, teams))


def audit_covers(
    book: SeasonPredictions,
    margins: dict[str, float],
    games: dict[str, Game],
) -> tuple[SeasonPredictions, bool]:
    """Rewrite a Cover when the favorite flips, the line moves 3+, or it becomes a pick'em."""
    seen: set[str] = set()
    audits = list(book.audits)
    rewrites: dict[str, str] = {}
    changed = False
    for team in book.teams:
        for row in team.games:
            if row.game_id in seen or row.pick_kind != "cover":
                continue
            if row.cover_favorite is None or row.cover_line is None:
                continue
            seen.add(row.game_id)
            margin = margins.get(row.game_id)
            game = games.get(row.game_id)
            if margin is None or game is None:
                continue
            favorite, laying = favorite_side(margin, game.away_team, game.home_team)
            change: Literal["flip", "move", "pickem"] | None = None
            if favorite is None:
                change = "pickem"
            elif favorite != row.cover_favorite:
                change = "flip"
            elif abs(laying - row.cover_line) >= COVER_MOVE_POINTS:
                change = "move"
            if change is None:
                continue
            changed = True
            rewrites[row.game_id] = row.cover_favorite
            audits.append(
                LineAudit(
                    game_id=row.game_id,
                    label=f"{game.away_team} @ {game.home_team}",
                    old_favorite=row.cover_favorite,
                    old_line=row.cover_line,
                    new_favorite=favorite,
                    new_line=round(laying, 4),
                    change=change,
                )
            )
    if not changed:
        return book, False
    teams: list[TeamSeasonTake] = []
    for team in book.teams:
        rows: list[SeasonGameTake] = []
        for row in team.games:
            favorite = rewrites.get(row.game_id)
            if favorite is None:
                rows.append(row)
                continue
            rows.append(
                row.model_copy(
                    update={
                        "predicted_winner": favorite,
                        "pick_kind": "outright",
                        "cover_favorite": None,
                        "cover_line": None,
                    }
                )
            )
        teams.append(team.model_copy(update={"games": rows}))
    return annotate_heatmap(_book(book, teams, audits)), True


def _rank_index(ranks: dict[str, list[str]], league: League, team: str) -> int | None:
    if league == League.NFL:
        ordered = ranks.get("nfl") or ranks.get("NFL") or []
        want = team_key(League.NFL, team)
        for i, name in enumerate(ordered):
            if team_key(League.NFL, name) == want:
                return i
        return None
    want = team_key(League.CFB, team)
    for group in ("B1G", "SEC", "ACC", "Big 12", "P4", "cfb"):
        for i, name in enumerate(ranks.get(group) or []):
            if team_key(League.CFB, name) == want:
                return i
    return None


def apply_ranks(
    book: SeasonPredictions,
    ranks: dict[str, list[str]],
    games: list[Game],
) -> tuple[SeasonPredictions, int, list[dict[str, str]]]:
    """Fill blank remaining games. Does not overwrite clicks. Skips CFB non-conference."""
    by_id = {g.game_id: g for g in games if g.season == book.season}
    existing = winners_by_game(book)
    leftovers: list[dict[str, str]] = []
    fills: dict[str, str] = {}
    seen_games: set[str] = set()
    for team in book.teams:
        for row in team.games:
            if row.game_id in seen_games:
                continue
            seen_games.add(row.game_id)
            game = by_id.get(row.game_id)
            if game is None:
                continue
            if existing.get(row.game_id) or row.predicted_winner:
                continue
            leftover = is_cfb_leftover(game, team.team)
            if leftover:
                leftovers.append(
                    {
                        "game_id": game.game_id,
                        "conference": team.conference,
                        "matchup": f"{game.away_team} @ {game.home_team}",
                        "week": str(game.week),
                    }
                )
                continue
            away_i = _rank_index(ranks, game.league, game.away_team)
            home_i = _rank_index(ranks, game.league, game.home_team)
            if away_i is None or home_i is None:
                leftovers.append(
                    {
                        "game_id": game.game_id,
                        "conference": team.conference,
                        "matchup": f"{game.away_team} @ {game.home_team}",
                        "week": str(game.week),
                    }
                )
                continue
            fills[game.game_id] = game.away_team if away_i < home_i else game.home_team

    teams: list[TeamSeasonTake] = []
    for team in book.teams:
        rows: list[SeasonGameTake] = []
        for row in team.games:
            winner = fills.get(row.game_id)
            leftover = row.leftover
            game = by_id.get(row.game_id)
            if game is not None:
                leftover = leftover or is_cfb_leftover(game, team.team)
            update: dict = {"leftover": leftover}
            if winner and not row.predicted_winner:
                update["predicted_winner"] = winner
            rows.append(row.model_copy(update=update))
        teams.append(team.model_copy(update={"games": rows}))
    updated = annotate_heatmap(_book(book, teams))
    return updated, len(fills), leftovers


def leftovers_for(book: SeasonPredictions, conference: str | None = None) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for team in book.teams:
        if conference and team.conference != conference and not (
            conference.lower() == "nfl" and team.league == League.NFL
        ):
            continue
        for row in team.games:
            if not row.leftover or row.predicted_winner or row.actual_winner:
                continue
            if row.game_id in seen:
                continue
            seen.add(row.game_id)
            out.append(
                {
                    "game_id": row.game_id,
                    "team": team.team,
                    "opponent": row.opponent,
                    "week": str(row.week),
                    "conference": team.conference,
                    "kickoff_iso": kickoff_iso(row.kickoff, team.league) or "",
                }
            )
    return out
