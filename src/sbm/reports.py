from __future__ import annotations

from pathlib import Path

from sbm.paper import Ledger
from sbm.schema import Pick


def write_picks_csv(picks: list[Pick], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    rows = [p.model_dump() for p in picks]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def write_bankroll_chart(ledger: Ledger, path: Path) -> Path | None:
    curve = ledger.curve()
    if not curve:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [p.index for p in curve]
    ys = [p.cumulative_units for p in curve]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(xs, ys, color="#1f6feb", linewidth=2)
    ax.axhline(0, color="#8b949e", linewidth=1)
    ax.set_title(f"{ledger.mode.value.title()} paper bankroll (units)")
    ax.set_xlabel("Settled pick #")
    ax.set_ylabel("Cumulative units")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def bake_sample_reports(report_dir: Path) -> None:
    """Frozen historical toy run for README screenshots — simulation ledger only."""
    from sbm.backtest import apply_backtest_to_ledger
    from sbm.mode import Mode
    from sbm.paper import Ledger
    from sbm.sampledata import toy_nfl_season

    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "toy_ledger.jsonl"
    ledger = Ledger(Mode.SIMULATION, path=path)
    if path.exists():
        path.unlink()
    apply_backtest_to_ledger(toy_nfl_season(), ledger)
    write_summary_json(ledger, report_dir / "summary.json")
    write_picks_csv([e.pick for e in ledger.load()], report_dir / "picks.csv")
    write_bankroll_chart(ledger, report_dir / "bankroll.png")


def write_summary_json(ledger: Ledger, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ledger.summary().model_dump_json(indent=2), encoding="utf-8")
    return path
