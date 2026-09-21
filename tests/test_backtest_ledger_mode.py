from pathlib import Path

import pytest

from sbm.backtest import apply_backtest_to_ledger
from sbm.journal import Journal
from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.paths import historical_ledger_path, ledger_path
from sbm.sampledata import toy_nfl_season
from sbm.schema import League, LedgerEntry, Market, Pick, Side, Ticket, TicketKind


def test_backtest_does_not_touch_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    Journal().add(
        Ticket.model_validate(
            {
                "ticket_id": "keep-me",
                "season": 2026,
                "sportsbook": "Novig",
                "stake_dollars": 5.0,
                "american_odds": -110,
                "kind": TicketKind.STRAIGHT,
                "legs": [
                    {
                        "league": "nfl",
                        "season": 2026,
                        "week": 1,
                        "team_or_side": "KC",
                    }
                ],
            }
        )
    )
    hist = Ledger(Mode.SIMULATION, path=historical_ledger_path(Mode.SIMULATION))
    apply_backtest_to_ledger(toy_nfl_season(), hist)
    assert [t.ticket_id for t in Journal().load()] == ["keep-me"]
    assert hist.load()


def test_backtest_does_not_touch_weekly_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    weekly = Ledger(Mode.SIMULATION, path=ledger_path(Mode.SIMULATION))
    weekly.append(
        LedgerEntry(
            mode=Mode.SIMULATION,
            pick=Pick(
                mode=Mode.SIMULATION,
                game_id="week-now",
                league=League.NFL,
                season=2026,
                week=2,
                market=Market.TOTAL,
                side=Side.UNDER,
                team_or_side="under",
                edge=3.0,
            ),
        )
    )
    hist = Ledger(Mode.SIMULATION, path=historical_ledger_path(Mode.SIMULATION))
    apply_backtest_to_ledger(toy_nfl_season(), hist)
    assert [e.pick.game_id for e in weekly.load()] == ["week-now"]
    assert hist.load()
    assert weekly.path != hist.path
