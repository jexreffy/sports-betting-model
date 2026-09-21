from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sbm.odds import cover_home_spread, cover_total, profit_units
from sbm.paths import journal_tickets_path, live_ledger_legacy_path
from sbm.predictions import kickoff_in_chicago, team_key
from sbm.schema import (
    Game,
    JournalYearStats,
    League,
    LedgerEntry,
    Leg,
    Market,
    Side,
    Ticket,
    TicketKind,
)
from sbm.teams import TeamFace, abbrev, team_face


def _status_label(result: str | None) -> str:
    if result is None:
        return "open"
    if result == "win":
        return "hit"
    if result == "loss":
        return "miss"
    if result == "cashout":
        return "chased"
    return result


def _token_matches_team(league: League, team: str, token: str) -> bool:
    raw = token.strip()
    if not raw or raw.lower() in {"over", "under"}:
        return False
    if team_key(league, team) == team_key(league, raw):
        return True
    code = abbrev(league, team).upper()
    tok = raw.upper()
    if code == tok or team.strip().upper() == tok:
        return True
    return len(code) >= 3 and len(tok) >= 3 and (code.startswith(tok) or tok.startswith(code))


def _game_has_token(game: Game, token: str) -> bool:
    return _token_matches_team(game.league, game.home_team, token) or _token_matches_team(
        game.league, game.away_team, token
    )


def _pair_matches(game: Game, left: str, right: str) -> bool:
    home_left = _token_matches_team(game.league, game.home_team, left)
    away_left = _token_matches_team(game.league, game.away_team, left)
    home_right = _token_matches_team(game.league, game.home_team, right)
    away_right = _token_matches_team(game.league, game.away_team, right)
    return (home_left and away_right) or (away_left and home_right)


def resolve_leg_game(leg: Leg, games: list[Game]) -> str | None:
    """Game this leg is about. Stored ids win. Otherwise match the two teams.

    The logged week picks the meeting when they play more than once. A week that
    matches nothing still links when the season has only one game between them.
    """
    if leg.game_id:
        return leg.game_id
    left = (leg.team_or_side or "").strip()
    right = (leg.opponent or "").strip()
    if not left or not right:
        return None
    season_games = [
        game
        for game in games
        if game.league == leg.league
        and game.season == leg.season
        and _pair_matches(game, left, right)
    ]
    week_hits = [game for game in season_games if game.week == leg.week]
    if len(week_hits) == 1:
        return week_hits[0].game_id
    if len(week_hits) > 1:
        return None
    if len(season_games) == 1:
        return season_games[0].game_id
    return None


def link_ticket_legs(legs: list[Leg], games: list[Game]) -> list[str | None]:
    """Resolve every leg. A prop uses a sibling leg's game when that game includes its opponent."""
    linked = [resolve_leg_game(leg, games) for leg in legs]
    by_id = {game.game_id: game for game in games}
    for index, leg in enumerate(legs):
        if linked[index]:
            continue
        token = (leg.opponent or "").strip()
        if not token:
            continue
        sibling_ids = {
            game_id
            for game_id in linked
            if game_id
            and (game := by_id.get(game_id)) is not None
            and _game_has_token(game, token)
        }
        if len(sibling_ids) == 1:
            linked[index] = sibling_ids.pop()
    return linked


def slate_bounds(moment: datetime) -> tuple[date, date]:
    """Tuesday–Monday window that contains this local moment."""
    day = moment.date()
    start = day - timedelta(days=(day.weekday() - 1) % 7)
    return start, start + timedelta(days=6)


def format_slate(start: date, end: date) -> str:
    return f"{start:%a %b} {start.day} – {end:%a %b} {end.day}"


def slate_for_game(game: Game) -> tuple[date, date] | None:
    local = kickoff_in_chicago(game.kickoff, game.league)
    if local is None:
        return None
    return slate_bounds(local)


def _empty_marks() -> dict[str, str | None]:
    return {
        "side_logo_url": None,
        "side_logo_mark": None,
        "side_color": None,
        "opp_logo_url": None,
        "opp_logo_mark": None,
        "opp_color": None,
        "mate_logo_url": None,
        "mate_logo_mark": None,
    }


def _mark_fields(face: TeamFace | None, prefix: str) -> dict[str, str | None]:
    if face is None:
        return {
            f"{prefix}_logo_url": None,
            f"{prefix}_logo_mark": None,
            f"{prefix}_color": None,
        }
    return {
        f"{prefix}_logo_url": face.logo_url,
        f"{prefix}_logo_mark": face.logo_mark,
        f"{prefix}_color": face.color,
    }


def leg_club_marks(leg: Leg, game: Game | None) -> dict[str, str | None]:
    """Logos for the club on the slip, its opponent, and the other club on a prop."""
    marks = _empty_marks()
    if game is None:
        return marks
    home = team_face(game.league, game.home_team, game.home_conference)
    away = team_face(game.league, game.away_team, game.away_conference)
    side = (leg.team_or_side or "").strip()
    opponent = (leg.opponent or "").strip()
    if _token_matches_team(game.league, game.home_team, side):
        chosen, other = home, away
    elif _token_matches_team(game.league, game.away_team, side):
        chosen, other = away, home
    else:
        chosen = None
        if _token_matches_team(game.league, game.home_team, opponent):
            other = home
            mate = away
        elif _token_matches_team(game.league, game.away_team, opponent):
            other = away
            mate = home
        else:
            other = None
            mate = None
        marks.update(_mark_fields(other, "opp"))
        marks["mate_logo_url"] = None if mate is None else mate.logo_url
        marks["mate_logo_mark"] = None if mate is None else mate.logo_mark
        return marks
    marks.update(_mark_fields(chosen, "side"))
    marks.update(_mark_fields(other, "opp"))
    return marks


def present_ticket_legs(tickets: list[dict], games: list[Game]) -> list[dict]:
    """Attach the linked game, its Tuesday–Monday window, and club marks.

    The logged week number stays on the ticket. The window comes from kickoff,
    so NFL and CFB share a week when the games fall on the same dates.
    """
    by_id = {game.game_id: game for game in games}
    windows: dict[str, str] = {}
    for ticket in tickets:
        legs = [Leg.model_validate(leg) for leg in ticket["legs"]]
        linked = link_ticket_legs(legs, games)
        keys: set[str] = set()
        label = None
        for raw, leg, game_id in zip(ticket["legs"], legs, linked, strict=True):
            raw["link_game_id"] = game_id
            game = by_id.get(game_id) if game_id else None
            window = slate_for_game(game) if game is not None else None
            if window is None:
                raw["slate_key"] = None
                raw["slate_label"] = None
            else:
                raw["slate_key"] = window[0].isoformat()
                raw["slate_label"] = format_slate(*window)
                keys.add(raw["slate_key"])
                label = raw["slate_label"]
                windows[raw["slate_key"]] = raw["slate_label"]
            raw.update(leg_club_marks(leg, game))
        ticket["slate_key"] = " ".join(sorted(keys))
        ticket["slate_label"] = label if len(keys) == 1 else None
    return [{"key": key, "label": windows[key]} for key in sorted(windows)]


def settle_leg(leg: Leg, game: Game) -> str:
    if not game.is_final:
        raise ValueError(f"Game {game.game_id} is not final")
    if leg.market is None or leg.side is None:
        raise ValueError("Cannot auto-grade a prop or unpriced leg")
    if leg.market == Market.SPREAD:
        stored = leg.market_line
        if stored is None:
            line = game.spread_close
        else:
            line = -stored if leg.side == Side.AWAY else stored
        if line is None:
            raise ValueError(f"No spread to settle {game.game_id}")
        home_result = cover_home_spread(game.home_margin or 0.0, line)
        if leg.side == Side.HOME:
            return home_result
        if leg.side == Side.AWAY:
            return {"win": "loss", "loss": "win", "push": "push"}[home_result]
        raise ValueError("Spread leg must be home or away")
    if leg.market == Market.TOTAL:
        line = leg.market_line if leg.market_line is not None else game.total_close
        if line is None or game.total_points is None:
            raise ValueError(f"No total to settle {game.game_id}")
        return cover_total(game.total_points, line, leg.side)
    if leg.market == Market.MONEYLINE:
        if game.home_margin is None:
            raise ValueError(f"No score to settle {game.game_id}")
        if game.home_margin == 0:
            return "push"
        if leg.side == Side.HOME:
            return "win" if game.home_margin > 0 else "loss"
        if leg.side == Side.AWAY:
            return "win" if game.home_margin < 0 else "loss"
        raise ValueError("Moneyline leg must be home or away")
    raise ValueError(f"Unknown market {leg.market}")


def combine_leg_results(results: list[str]) -> str:
    if any(item == "loss" for item in results):
        return "loss"
    if any(item == "push" for item in results):
        return "push"
    if results and all(item == "win" for item in results):
        return "win"
    raise ValueError("Cannot combine empty or unknown leg results")


def profit_dollars_for(ticket: Ticket, result: str) -> float:
    if result == "cashout":
        if ticket.cashout_dollars is None:
            raise ValueError("Cash-out tickets need cashout_dollars")
        return round(ticket.cashout_dollars - ticket.stake_dollars, 2)
    if result == "push":
        return 0.0
    if result == "loss":
        return round(-ticket.stake_dollars, 2)
    if result == "win":
        return round(
            profit_units(ticket.american_odds, ticket.stake_dollars, True, False),
            2,
        )
    raise ValueError(f"Unknown result {result}")


def ticket_from_live_payload(data: dict) -> Ticket | None:
    pick = data.get("pick") or {}
    if pick.get("skipped") or data.get("result") == "skip":
        return None
    result = data.get("result")
    profit = data.get("profit_units")
    if result not in {None, "win", "loss", "push"}:
        result = None
        profit = None
    market = Market(pick["market"])
    side = Side(pick["side"])
    market_line = pick.get("market_line")
    if market == Market.SPREAD and side == Side.AWAY and market_line is not None:
        market_line = -float(market_line)

    return Ticket(
        ticket_id=str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"live:{pick['game_id']}:{pick['market']}:{pick.get('column', 'gut')}",
            )
        ),
        season=int(pick["season"]),
        sportsbook="unknown",
        stake_dollars=float(pick.get("units") or 1.0),
        american_odds=int(pick.get("american_odds") or -110),
        kind=TicketKind.STRAIGHT,
        legs=[
            Leg(
                league=League(pick["league"]),
                season=int(pick["season"]),
                week=int(pick["week"]),
                team_or_side=str(pick["team_or_side"]),
                game_id=str(pick["game_id"]),
                market=market,
                side=side,
                market_line=market_line,
                american_odds=pick.get("american_odds"),
            )
        ],
        result=result,
        profit_dollars=None if profit is None else round(float(profit), 2),
        placed_at=pick.get("placed_at"),
        settled_at=data.get("settled_at"),
        notes="Migrated from live paper ledger",
    )


def ticket_from_live_entry(entry: LedgerEntry) -> Ticket | None:
    return ticket_from_live_payload(json.loads(entry.model_dump_json()))


class Journal:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or journal_tickets_path()

    def load(self) -> list[Ticket]:
        if not self.path.exists():
            return []
        tickets: list[Ticket] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            tickets.append(Ticket.model_validate_json(line))
        return tickets

    def _rewrite(self, tickets: list[Ticket]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for ticket in tickets:
                fh.write(ticket.model_dump_json() + "\n")

    def add(self, ticket: Ticket) -> Ticket:
        tickets = self.load()
        if any(row.ticket_id == ticket.ticket_id for row in tickets):
            raise ValueError(f"Ticket {ticket.ticket_id} already exists")
        tickets.append(ticket)
        self._rewrite(tickets)
        return ticket

    def get(self, ticket_id: str) -> Ticket:
        for ticket in self.load():
            if ticket.ticket_id == ticket_id:
                return ticket
        raise ValueError(f"No ticket {ticket_id}")

    def drop(self, ticket_id: str) -> None:
        tickets = self.load()
        kept: list[Ticket] = []
        removed = False
        for ticket in tickets:
            if ticket.ticket_id != ticket_id:
                kept.append(ticket)
                continue
            if ticket.result is not None:
                raise ValueError("Cannot drop a settled ticket")
            removed = True
        if not removed:
            raise ValueError("No open ticket to drop")
        self._rewrite(kept)

    def cashout(self, ticket_id: str, cashout_dollars: float) -> Ticket:
        tickets = self.load()
        updated: list[Ticket] = []
        found: Ticket | None = None
        now = datetime.now(UTC)
        for ticket in tickets:
            if ticket.ticket_id != ticket_id:
                updated.append(ticket)
                continue
            if ticket.result is not None and ticket.result != "cashout":
                raise ValueError("Cannot cash out a graded ticket")
            cashed = ticket.model_copy(
                update={
                    "result": "cashout",
                    "cashout_dollars": cashout_dollars,
                    "settled_at": now,
                }
            )
            found = cashed.model_copy(
                update={"profit_dollars": profit_dollars_for(cashed, "cashout")}
            )
            updated.append(found)
        if found is None:
            raise ValueError(f"No ticket {ticket_id}")
        self._rewrite(updated)
        return found

    def settle(self, games: dict[str, Game], *, season: int | None = None) -> int:
        tickets = self.load()
        settled = 0
        now = datetime.now(UTC)
        updated: list[Ticket] = []
        for ticket in tickets:
            if season is not None and ticket.season != season:
                updated.append(ticket)
                continue
            if ticket.result == "cashout":
                updated.append(ticket)
                continue
            if ticket.result is not None:
                updated.append(ticket)
                continue
            try:
                results: list[str] = []
                ready = True
                for leg in ticket.legs:
                    if not leg.game_id or leg.market is None:
                        ready = False
                        break
                    game = games.get(leg.game_id)
                    if game is None or not game.is_final:
                        ready = False
                        break
                    results.append(settle_leg(leg, game))
                if not ready:
                    updated.append(ticket)
                    continue
                result = combine_leg_results(results)
                updated.append(
                    ticket.model_copy(
                        update={
                            "result": result,
                            "profit_dollars": profit_dollars_for(ticket, result),
                            "settled_at": now,
                        }
                    )
                )
                settled += 1
            except ValueError:
                updated.append(ticket)
        self._rewrite(updated)
        return settled

    def year(self, season: int) -> JournalYearStats:
        rows = [t for t in self.load() if t.season == season]
        open_n = sum(1 for t in rows if t.result is None)
        hits = sum(1 for t in rows if t.result == "win")
        misses = sum(1 for t in rows if t.result == "loss")
        pushes = sum(1 for t in rows if t.result == "push")
        cashed = sum(1 for t in rows if t.result == "cashout")
        decided = [t for t in rows if t.result is not None]
        staked = sum(t.stake_dollars for t in decided if t.result != "push")
        profit = sum(t.profit_dollars or 0.0 for t in decided)
        roi = (profit / staked) if staked else None
        return JournalYearStats(
            season=season,
            n_tickets=len(rows),
            n_open=open_n,
            hits=hits,
            misses=misses,
            pushes=pushes,
            cashed_early=cashed,
            staked_dollars=round(staked, 2),
            profit_dollars=round(profit, 2),
            roi=None if roi is None else round(roi, 4),
        )

    def seed_novig(self) -> int:
        from sbm.journal_seed import novig_2026_tickets

        existing = {t.ticket_id for t in self.load()}
        added = 0
        for ticket in novig_2026_tickets():
            if ticket.ticket_id in existing:
                continue
            self.add(ticket)
            added += 1
        return added

    def rows_for_year(self, season: int) -> list[dict]:
        out: list[dict] = []
        for ticket in self.load():
            if ticket.season != season:
                continue
            payload = ticket.model_dump(mode="json")
            payload["status"] = _status_label(ticket.result)
            out.append(payload)
        return out


def migrate_live_ledger(
    *,
    live_path: Path | None = None,
    journal: Journal | None = None,
) -> int:
    """Copy pre-Journal live paper rows into tickets. Never writes simulation."""
    src = live_path or live_ledger_legacy_path()
    book = journal or Journal()
    if not src.exists():
        return 0
    existing = {t.ticket_id for t in book.load()}
    added = 0
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ticket = ticket_from_live_payload(json.loads(line))
        if ticket is None or ticket.ticket_id in existing:
            continue
        book.add(ticket)
        existing.add(ticket.ticket_id)
        added += 1
    return added


def new_ticket_id() -> str:
    return str(uuid.uuid4())
