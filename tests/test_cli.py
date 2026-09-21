import re
from pathlib import Path

from typer.testing import CliRunner

from sbm.cli import app

runner = CliRunner()


def _plain(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_help() -> None:
    result = runner.invoke(app, ["--help"], color=False)
    assert result.exit_code == 0
    stdout = _plain(result.stdout)
    assert "simulate" in stdout
    assert "journal" in stdout
    live = runner.invoke(app, ["live"], color=False)
    assert live.exit_code == 0
    assert "Journal" in _plain(live.stdout)
    sim = runner.invoke(app, ["simulate", "--help"], color=False)
    sim_out = _plain(sim.stdout)
    assert "save-week" in sim_out
    assert "settle-week" in sim_out
    assert "tune" in sim_out


def test_serve_help_documents_reload() -> None:
    result = runner.invoke(
        app,
        ["serve", "--help"],
        color=False,
        env={"COLUMNS": "120", "TERM": "dumb"},
    )
    assert result.exit_code == 0
    assert "--reload" in _plain(result.stdout)


def test_bake_sample_writes_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    result = runner.invoke(app, ["simulate", "bake-sample", "--report-dir", str(report_dir)])
    assert result.exit_code == 0, result.stdout
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "picks.csv").exists()
    assert (report_dir / "toy_ledger.jsonl").exists()
