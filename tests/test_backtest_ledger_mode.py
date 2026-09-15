from pathlib import Path

import pytest

from sbm.backtest import apply_backtest_to_ledger
from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.paths import historical_ledger_path, ledger_path
from sbm.sampledata import toy_nfl_season
from sbm.schema import League, LedgerEntry, Market, Pick, Side


def test_backtest_refuses_live_ledger(tmp_path: Path) -> None:
    ledger = Ledger(Mode.LIVE, path=tmp_path / "live.jsonl")
    with pytest.raises(ValueError, match="simulation"):
        apply_backtest_to_ledger(toy_nfl_season(), ledger)


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
