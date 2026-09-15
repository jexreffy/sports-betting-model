from pathlib import Path

import pytest

from sbm.mode import Mode
from sbm.paper import Ledger, ModeMismatchError
from sbm.schema import League, LedgerEntry, Market, Pick, Side


def _pick(mode: Mode, game_id: str = "g1") -> Pick:
    return Pick(
        mode=mode,
        game_id=game_id,
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.SPREAD,
        side=Side.HOME,
        team_or_side="KC",
        edge=2.0,
    )


def test_ledger_rejects_other_mode(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    with pytest.raises(ModeMismatchError):
        ledger.append(LedgerEntry(mode=Mode.LIVE, pick=_pick(Mode.LIVE)))


def test_entry_mode_must_match_pick() -> None:
    with pytest.raises(ValueError):
        LedgerEntry(mode=Mode.SIMULATION, pick=_pick(Mode.LIVE))


def test_two_ledgers_do_not_mix(tmp_path: Path) -> None:
    sim = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    live = Ledger(Mode.LIVE, path=tmp_path / "live" / "ledger.jsonl")
    sim.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick(Mode.SIMULATION, "sim1")))
    live.append(LedgerEntry(mode=Mode.LIVE, pick=_pick(Mode.LIVE, "live1")))
    assert [e.pick.game_id for e in sim.load()] == ["sim1"]
    assert [e.pick.game_id for e in live.load()] == ["live1"]


def test_corrupted_cross_mode_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "simulation" / "ledger.jsonl"
    live = Ledger(Mode.LIVE, path=tmp_path / "live" / "ledger.jsonl")
    live.append(LedgerEntry(mode=Mode.LIVE, pick=_pick(Mode.LIVE)))
    # Copy live row into a simulation path
    path.parent.mkdir(parents=True)
    path.write_text(live.path.read_text(), encoding="utf-8")
    sim = Ledger(Mode.SIMULATION, path=path)
    with pytest.raises(ModeMismatchError):
        sim.load()
