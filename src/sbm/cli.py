from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sbm.config import RESEARCH_WINDOWS
from sbm.mode import Mode
from sbm.schema import League

app = typer.Typer(
    help="NFL + CFB paper betting model. Never places sportsbook wagers.",
    rich_markup_mode=None,
)
simulate_app = typer.Typer(
    help="Simulation lab: historical replay and paper bets on real games.",
    rich_markup_mode=None,
)
live_app = typer.Typer(
    help="Live 2027-shaped board (practice by default). Isolated ledger.",
    rich_markup_mode=None,
)
app.add_typer(simulate_app, name="simulate")
app.add_typer(live_app, name="live")


def _seasons(start: int, end: int) -> list[int]:
    if end < start:
        raise typer.BadParameter("end season must be >= start season")
    return list(range(start, end + 1))


def _league(value: str | None) -> League | None:
    if value is None:
        return None
    return League(value.lower())


@app.command()
def ingest(
    league: Annotated[str, typer.Option(help="nfl, cfb, or all")] = "all",
    start: Annotated[int, typer.Option(help="First season")] = RESEARCH_WINDOWS.warmup_start,
    end: Annotated[int, typer.Option(help="Last season inclusive")] = RESEARCH_WINDOWS.hands_off,
) -> None:
    """Download schedules, results, and closing lines into data/raw/."""
    from sbm.data.store import save_games

    seasons = _seasons(start, end)
    targets = [League.NFL, League.CFB] if league == "all" else [League(league.lower())]
    if League.NFL in targets:
        from sbm.data.nfl import download_nfl_games

        typer.echo(f"Ingesting NFL {seasons[0]}-{seasons[-1]}…")
        games = download_nfl_games(seasons)
        path = save_games(League.NFL, games, replace_seasons=set(seasons))
        typer.echo(f"Wrote {len(games)} NFL games to {path}")
    if League.CFB in targets:
        from sbm.data.cfb import download_cfb_games

        typer.echo(f"Ingesting CFB FBS {seasons[0]}-{seasons[-1]}…")
        games = download_cfb_games(seasons)
        path = save_games(League.CFB, games, replace_seasons=set(seasons))
        typer.echo(f"Wrote {len(games)} CFB games to {path}")


@simulate_app.command("backtest")
def simulate_backtest(
    start: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.warmup_start,
    end: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.holdout_end,
    league: Annotated[str | None, typer.Option()] = None,
    report_dir: Annotated[Path, typer.Option()] = Path("reports/sample"),
) -> None:
    """Walk-forward history into the historical ledger. Does not touch this week's paper book."""
    from sbm.backtest import apply_backtest_to_ledger
    from sbm.data.store import load_games
    from sbm.paper import Ledger
    from sbm.paths import historical_ledger_path
    from sbm.reports import write_bankroll_chart, write_picks_csv, write_summary_json

    lg = _league(league)
    games = load_games(lg)
    if not games:
        raise typer.BadParameter("No games found. Run `sbm ingest` first.")
    ledger = Ledger(Mode.SIMULATION, path=historical_ledger_path(Mode.SIMULATION))
    if ledger.path.exists():
        ledger.path.unlink()
    apply_backtest_to_ledger(games, ledger, start_season=start, end_season=end)
    summary = ledger.summary()
    typer.echo(
        f"Windows: warmup {RESEARCH_WINDOWS.warmup_start}-{RESEARCH_WINDOWS.warmup_end} "
        f"(ratings only), search {RESEARCH_WINDOWS.search_start}-{RESEARCH_WINDOWS.search_end}, "
        f"holdout {RESEARCH_WINDOWS.holdout_start}-{RESEARCH_WINDOWS.holdout_end}, "
        f"{RESEARCH_WINDOWS.hands_off} hands-off"
    )
    typer.echo(summary.model_dump_json(indent=2))
    by_window: dict[str, int] = {}
    for entry in ledger.load():
        key = entry.pick.research_window.value if entry.pick.research_window else "unset"
        by_window[key] = by_window.get(key, 0) + 1
    if by_window:
        typer.echo(f"Picks by window: {by_window}")
    write_summary_json(ledger, report_dir / "summary.json")
    write_picks_csv([e.pick for e in ledger.load()], report_dir / "picks.csv")
    chart = write_bankroll_chart(ledger, report_dir / "bankroll.png")
    if chart:
        typer.echo(f"Wrote {chart}")


@simulate_app.command("bake-sample")
def simulate_bake_sample(
    report_dir: Annotated[Path, typer.Option()] = Path("reports/sample"),
) -> None:
    """Write checked-in toy backtest artifacts (no network)."""
    from sbm.reports import bake_sample_reports

    bake_sample_reports(report_dir)
    typer.echo(f"Wrote sample reports under {report_dir}")


@simulate_app.command("picks")
def simulate_picks(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
    league: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Paper the current (or specified) real week into the simulation diary."""
    _run_week_picks(Mode.SIMULATION, season, week, league)


@simulate_app.command("save-week")
def simulate_save_week(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
    league: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Alias for `simulate picks` — write this week's slate into the 2026 diary."""
    _run_week_picks(Mode.SIMULATION, season, week, league)


@simulate_app.command("settle")
def simulate_settle(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
) -> None:
    _settle(Mode.SIMULATION, season, week)


@simulate_app.command("settle-week")
def simulate_settle_week(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
) -> None:
    """Alias for `simulate settle` — grade only this week's diary rows."""
    _settle(Mode.SIMULATION, season, week)


@simulate_app.command("tune")
def simulate_tune(
    report_dir: Annotated[Path, typer.Option()] = Path("reports/tune"),
    league: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Fit on 2021–23 error metrics; confirm 2024–25. Never scores 2026 historical P&L."""
    from sbm.data.store import load_games
    from sbm.tune import tune, write_tune_report

    games = load_games(_league(league))
    if not games:
        raise typer.BadParameter("No games found. Run `sbm ingest` first.")
    report = tune(games)
    path = write_tune_report(report, report_dir / "tune.json")
    typer.echo(report.model_dump_json(indent=2))
    typer.echo(f"Wrote {path}")
    typer.echo("Suggested params are not applied automatically.")


@live_app.command("picks")
def live_picks(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
    league: Annotated[str | None, typer.Option()] = None,
) -> None:
    """2027-shaped board. Writes only the live ledger."""
    from sbm.config import get_settings

    settings = get_settings()
    if settings.live_practice:
        typer.echo("LIVE (practice) — not this year's real book.")
    _run_week_picks(Mode.LIVE, season, week, league)


@live_app.command("settle")
def live_settle(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
) -> None:
    _settle(Mode.LIVE, season, week)


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
    reload: Annotated[bool, typer.Option("--reload/--no-reload")] = False,
) -> None:
    """Local dashboard. Bind 127.0.0.1 by default; use --reload while editing Python."""
    import uvicorn

    if host in {"0.0.0.0", "::"}:
        typer.echo("Warning: dashboard has no auth and exposes paper ledgers on all interfaces.")
    uvicorn.run("sbm.web.app:app", host=host, port=port, reload=reload)


def _run_week_picks(mode: Mode, season: int | None, week: int | None, league: str | None) -> None:
    from sbm.backtest import current_slate_picks
    from sbm.data.store import load_games
    from sbm.paper import Ledger
    from sbm.providers.lines import default_provider

    if season is None and mode == Mode.SIMULATION:
        season = RESEARCH_WINDOWS.hands_off
    games = default_provider().attach_lines(load_games(_league(league)))
    if not games:
        raise typer.BadParameter("No games found. Run `sbm ingest` first.")
    picks, _ = current_slate_picks(
        games, mode=mode, season=season, week=week, league=_league(league)
    )
    ledger = Ledger(mode)
    added = ledger.record_picks(picks)
    typer.echo(f"{mode.value}: {len(picks)} candidate picks, {added} new diary rows")
    for pick in picks:
        typer.echo(
            f"  {pick.league} {pick.season}w{pick.week} {pick.market} "
            f"{pick.team_or_side} edge={pick.edge} odds={pick.american_odds}"
        )


def _settle(mode: Mode, season: int | None, week: int | None) -> None:
    from sbm.backtest import infer_current_week
    from sbm.data.store import games_by_id, load_games
    from sbm.errors import week_error_report
    from sbm.paper import Ledger

    ledger = Ledger(mode)
    games = load_games()
    if season is None or week is None:
        inferred = ledger.infer_open_week()
        if inferred is None:
            inferred = infer_current_week(games)
        if inferred is not None:
            season = season or inferred[0]
            week = week or inferred[1]
    n = ledger.settle(games_by_id(games), season=season, week=week)
    typer.echo(f"Settled {n} {mode.value} picks for {season}w{week}")
    typer.echo(ledger.summary(season=season, week=week).model_dump_json(indent=2))
    if season is not None and week is not None:
        report = week_error_report(games, season=season, week=week, mode=mode)
        typer.echo(report.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
