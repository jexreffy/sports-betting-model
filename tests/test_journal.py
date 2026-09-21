from pathlib import Path

import pytest

from sbm.journal import (
    Journal,
    combine_leg_results,
    migrate_live_ledger,
    profit_dollars_for,
    settle_leg,
    ticket_from_live_payload,
)
from sbm.schema import Game, League, Leg, Market, Side, Ticket, TicketKind


def _leg(**kwargs: object) -> Leg:
    base: dict[str, object] = {
        "league": League.NFL,
        "season": 2026,
        "week": 1,
        "team_or_side": "KC",
        "game_id": "g1",
        "market": Market.MONEYLINE,
        "side": Side.HOME,
    }
    base.update(kwargs)
    return Leg.model_validate(base)


def _ticket(**kwargs: object) -> Ticket:
    base: dict[str, object] = {
        "ticket_id": "t1",
        "season": 2026,
        "sportsbook": "Novig",
        "stake_dollars": 5.0,
        "american_odds": -110,
        "kind": TicketKind.STRAIGHT,
        "legs": [_leg()],
    }
    base.update(kwargs)
    return Ticket.model_validate(base)


def _final() -> Game:
    return Game(
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=1,
        home_team="KC",
        away_team="DEN",
        home_score=27,
        away_score=20,
        spread_close=-3.0,
        total_close=45.0,
    )


def test_straight_win_loss_push_dollars() -> None:
    win = _ticket()
    assert settle_leg(win.legs[0], _final()) == "win"
    assert profit_dollars_for(win, "win") == 4.55
    assert profit_dollars_for(win, "loss") == -5.0
    assert profit_dollars_for(win, "push") == 0.0


def test_cashout_is_sticky(tmp_path: Path) -> None:
    book = Journal(path=tmp_path / "journal" / "tickets.jsonl")
    book.add(_ticket())
    cashed = book.cashout("t1", 8.09)
    assert cashed.result == "cashout"
    assert cashed.profit_dollars == 3.09
    n = book.settle({"g1": _final()}, season=2026)
    assert n == 0
    assert book.get("t1").result == "cashout"
    assert book.get("t1").profit_dollars == 3.09


def test_parlay_all_win_one_loss_push() -> None:
    assert combine_leg_results(["win", "win"]) == "win"
    assert combine_leg_results(["win", "loss"]) == "loss"
    assert combine_leg_results(["win", "push"]) == "push"


def test_parlay_settle(tmp_path: Path) -> None:
    book = Journal(path=tmp_path / "journal" / "tickets.jsonl")
    g2 = _final().model_copy(update={"game_id": "g2", "home_score": 10, "away_score": 17})
    book.add(
        _ticket(
            ticket_id="parlay",
            kind=TicketKind.PARLAY,
            american_odds=257,
            legs=[
                _leg(),
                _leg(game_id="g2", team_or_side="away", side=Side.AWAY),
            ],
        )
    )
    n = book.settle({"g1": _final(), "g2": g2}, season=2026)
    assert n == 1
    assert book.get("parlay").result == "win"


def test_journal_never_writes_simulation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.mode import Mode
    from sbm.paths import journal_tickets_path, ledger_path

    book = Journal()
    book.add(_ticket())
    assert journal_tickets_path().exists()
    assert not ledger_path(Mode.SIMULATION).exists()
    assert "simulation" not in str(journal_tickets_path())


def test_away_spread_uses_bettor_line() -> None:
    """PIT +4.5 as the away slip, not the home number."""
    game = _final()  # home won by 7
    away_plus = _leg(
        market=Market.SPREAD,
        side=Side.AWAY,
        team_or_side="DEN",
        market_line=4.5,
    )
    assert settle_leg(away_plus, game) == "loss"
    close = _leg(
        market=Market.SPREAD,
        side=Side.AWAY,
        team_or_side="DEN",
        market_line=7.5,
    )
    assert settle_leg(close, game) == "win"


def test_migrate_live_payload_keeps_result() -> None:
    raw = {
        "mode": "live",
        "pick": {
            "mode": "live",
            "game_id": "2026_02_CLE_TB",
            "league": "nfl",
            "season": 2026,
            "week": 2,
            "market": "spread",
            "side": "home",
            "team_or_side": "TB",
            "market_line": -8.5,
            "american_odds": -110,
            "units": 1.0,
            "column": "gut",
            "skipped": False,
        },
        "result": "loss",
        "profit_units": -1.0,
    }
    ticket = ticket_from_live_payload(raw)
    assert ticket is not None
    assert ticket.result == "loss"
    assert ticket.legs[0].team_or_side == "TB"
    assert ticket.stake_dollars == 1.0


def test_migrate_away_spread_flips_home_line_to_slip() -> None:
    raw = {
        "mode": "live",
        "pick": {
            "mode": "live",
            "game_id": "g1",
            "league": "nfl",
            "season": 2026,
            "week": 2,
            "market": "spread",
            "side": "away",
            "team_or_side": "PIT",
            "market_line": -4.5,
            "american_odds": -110,
            "units": 5.0,
            "column": "gut",
            "skipped": False,
        },
        "result": None,
    }
    ticket = ticket_from_live_payload(raw)
    assert ticket is not None
    assert ticket.legs[0].market_line == 4.5
    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=2,
        home_team="NE",
        away_team="PIT",
        home_score=24,
        away_score=17,
        spread_close=-4.5,
    )
    assert settle_leg(ticket.legs[0], game) == "loss"


def test_migrate_does_not_touch_simulation(tmp_path: Path) -> None:
    live = tmp_path / "live" / "ledger.jsonl"
    live.parent.mkdir()
    live.write_text(
        '{"mode":"live","pick":{"mode":"live","game_id":"g1","league":"nfl","season":2026,'
        '"week":1,"market":"moneyline","side":"home","team_or_side":"KC","edge":1,'
        '"american_odds":-110,"units":5,"column":"gut","skipped":false},"result":"win",'
        '"profit_units":4.55}\n',
        encoding="utf-8",
    )
    journal_path = tmp_path / "journal" / "tickets.jsonl"
    added = migrate_live_ledger(live_path=live, journal=Journal(path=journal_path))
    assert added == 1
    assert (tmp_path / "simulation").exists() is False
    assert Journal(path=journal_path).load()[0].result == "win"
