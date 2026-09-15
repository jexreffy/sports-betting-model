from pathlib import Path

import pytest

from sbm.backtest import apply_backtest_to_ledger
from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.sampledata import toy_nfl_season


def test_backtest_refuses_live_ledger(tmp_path: Path) -> None:
    ledger = Ledger(Mode.LIVE, path=tmp_path / "live.jsonl")
    with pytest.raises(ValueError, match="simulation"):
        apply_backtest_to_ledger(toy_nfl_season(), ledger)
