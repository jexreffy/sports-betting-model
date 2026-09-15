from pathlib import Path

from typer.testing import CliRunner

from sbm.cli import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "simulate" in result.stdout
    assert "live" in result.stdout


def test_bake_sample_writes_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    result = runner.invoke(app, ["simulate", "bake-sample", "--report-dir", str(report_dir)])
    assert result.exit_code == 0, result.stdout
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "picks.csv").exists()
    assert (report_dir / "toy_ledger.jsonl").exists()
