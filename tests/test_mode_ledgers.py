from pathlib import Path

import pytest

from sbm.mode import Mode, parse_mode
from sbm.paper import Ledger, ModeMismatchError
from sbm.schema import League, LedgerEntry, Market, Pick, Side


def _pick(game_id: str = "g1") -> Pick:
    return Pick(
        mode=Mode.SIMULATION,
        game_id=game_id,
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.SPREAD,
        side=Side.HOME,
        team_or_side="KC",
        edge=2.0,
    )


def test_live_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="Journal"):
        parse_mode("live")


def test_two_paths_do_not_mix(tmp_path: Path) -> None:
    sim = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    other = Ledger(Mode.SIMULATION, path=tmp_path / "other" / "ledger.jsonl")
    sim.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick("sim1")))
    other.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick("other1")))
    assert [e.pick.game_id for e in sim.load()] == ["sim1"]
    assert [e.pick.game_id for e in other.load()] == ["other1"]


def test_corrupted_live_row_in_simulation_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "simulation" / "ledger.jsonl"
    other = Ledger(Mode.SIMULATION, path=tmp_path / "other" / "ledger.jsonl")
    other.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick()))
    path.parent.mkdir(parents=True)
    path.write_text(
        other.path.read_text(encoding="utf-8").replace('"simulation"', '"live"'),
        encoding="utf-8",
    )
    sim = Ledger(Mode.SIMULATION, path=path)
    with pytest.raises((ModeMismatchError, ValueError)):
        sim.load()
