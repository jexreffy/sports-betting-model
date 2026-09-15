from pathlib import Path

import pytest

from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.schema import League, LedgerEntry, Market, Pick, Side, StakeColumn


def _system(game_id: str = "g1") -> Pick:
    return Pick(
        mode=Mode.SIMULATION,
        game_id=game_id,
        league=League.NFL,
        season=2026,
        week=1,
        market=Market.SPREAD,
        side=Side.HOME,
        team_or_side="KC",
        edge=3.0,
        column=StakeColumn.SYSTEM,
    )


def test_skip_excluded_from_system_units(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "ledger.jsonl")
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=_system()))
    ledger.mark(
        game_id="g1",
        market=Market.SPREAD,
        column=StakeColumn.SYSTEM,
        skipped=True,
    )
    assert ledger.settle({}) == 1
    summary = ledger.summary()
    assert summary.system.n_picks == 0
    assert summary.system.units == 0
    assert summary.gut.n_picks == 0


def test_gut_column_is_separate_pnl(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "ledger.jsonl")
    system = _system()
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=system))
    ledger.mark(
        game_id="g1",
        market=Market.SPREAD,
        column=StakeColumn.GUT,
        skipped=False,
        side=Side.AWAY,
        team_or_side="BAL",
        source=system,
    )
    from sbm.schema import Game

    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=1,
        home_team="KC",
        away_team="BAL",
        home_score=24,
        away_score=17,
        spread_close=-3.0,
    )
    assert ledger.settle({game.game_id: game}) == 2
    summary = ledger.summary()
    assert summary.system.wins == 1
    assert summary.gut.losses == 1
    assert summary.system.units > 0
    assert summary.gut.units < 0


def test_mark_does_not_write_the_other_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    sim = Ledger(Mode.SIMULATION)
    live = Ledger(Mode.LIVE)
    pick = _system()
    sim.append(LedgerEntry(mode=Mode.SIMULATION, pick=pick))
    sim.mark(
        game_id="g1",
        market=Market.SPREAD,
        column=StakeColumn.SYSTEM,
        skipped=True,
    )
    assert live.load() == []
    assert sim.load()[0].pick.skipped is True


def test_drop_removes_open_ticket(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "ledger.jsonl")
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=_system()))
    ledger.drop(game_id="g1", market=Market.SPREAD, column=StakeColumn.SYSTEM)
    assert ledger.load() == []
