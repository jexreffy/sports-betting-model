from pathlib import Path

from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.reports import bake_sample_reports, write_summary_json
from sbm.sampledata import toy_nfl_season


def test_toy_season_is_holdout_only() -> None:
    seasons = {g.season for g in toy_nfl_season()}
    assert seasons == {2024}


def test_bake_sample_and_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "sample"
    bake_sample_reports(report_dir)
    ledger = Ledger(Mode.SIMULATION, path=report_dir / "toy_ledger.jsonl")
    summary = ledger.summary()
    assert summary.mode == Mode.SIMULATION
    assert summary.n_picks > 0
    assert summary.n_settled == summary.n_picks
    out = write_summary_json(ledger, tmp_path / "summary.json")
    assert out.exists()
    assert "n_picks" in out.read_text(encoding="utf-8")
