from pathlib import Path

import pytest

from sbm.backtest import apply_backtest_to_ledger
from sbm.journal import Journal
from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.paths import historical_ledger_path, ledger_path
from sbm.sampledata import toy_nfl_season
from sbm.schema import Game, League, LedgerEntry, Market, Pick, Side, Ticket, TicketKind
from sbm.units import UnitBook, UnitWeek


def test_backtest_applies_the_unit_adjustment(tmp_path: Path) -> None:
    game = Game(
        game_id="g",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="AAA",
        away_team="BBB",
        home_score=24,
        away_score=17,
        spread_close=0.0,
    )
    book = UnitBook(
        [
            UnitWeek(
                league=League.NFL,
                season=2023,
                week=18,
                team="AAA",
                rush_off=1.0,
                rush_allowed=0.0,
                pass_off=0.0,
                pass_allowed=0.0,
            ),
            UnitWeek(
                league=League.NFL,
                season=2023,
                week=18,
                team="BBB",
                rush_off=-1.0,
                rush_allowed=0.0,
                pass_off=0.0,
                pass_allowed=0.0,
            ),
        ]
    )
    bare = Ledger(Mode.SIMULATION, path=tmp_path / "bare.jsonl")
    moved = Ledger(Mode.SIMULATION, path=tmp_path / "moved.jsonl")
    apply_backtest_to_ledger([game], bare)
    apply_backtest_to_ledger([game], moved, units=book)

    def spread_line(ledger: Ledger) -> float:
        return next(
            entry.pick.model_line
            for entry in ledger.load()
            if entry.pick.market == Market.SPREAD and entry.pick.model_line is not None
        )

    assert spread_line(moved) == spread_line(bare) - 4.0


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
