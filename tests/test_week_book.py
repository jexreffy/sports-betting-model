from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.paths import historical_ledger_path, ledger_path
from sbm.schema import League, LedgerEntry, Market, Pick, Side
from sbm.web.app import app


def test_board_does_not_surface_paper_ledgers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    diary = Ledger(Mode.SIMULATION, path=ledger_path(Mode.SIMULATION))
    hist = Ledger(Mode.SIMULATION, path=historical_ledger_path(Mode.SIMULATION))
    hist.append(
        LedgerEntry(
            mode=Mode.SIMULATION,
            pick=Pick(
                mode=Mode.SIMULATION,
                game_id="hist-1",
                league=League.NFL,
                season=2024,
                week=1,
                market=Market.SPREAD,
                side=Side.HOME,
                team_or_side="KC",
                edge=3.0,
                units=100.0,
            ),
            result="win",
            profit_units=90.91,
        )
    )
    diary.append(
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
            result="win",
            profit_units=0.91,
        )
    )
    client = TestClient(app)
    body = client.get("/api/board", params={"mode": "simulation"}).json()
    assert "summary" not in body
    assert "curve" not in body
    assert "book" not in body
    page = client.get("/research")
    assert b"bankroll" not in page.content
    assert b"Chart" not in page.content
