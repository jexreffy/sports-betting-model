from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sbm.config import RESEARCH_WINDOWS
from sbm.mode import Mode
from sbm.schema import League

app = typer.Typer(
    help="NFL + CFB research model and 2026 Journal. Never places sportsbook wagers.",
    rich_markup_mode=None,
)
simulate_app = typer.Typer(
    help="Research lab: historical replay and the current-week model slate. Not your money.",
    rich_markup_mode=None,
)
journal_app = typer.Typer(
    help="2026 real-money Journal (logging only). Isolated from Simulation.",
    rich_markup_mode=None,
)
predictions_app = typer.Typer(
    help="Current-year W/L Predictions. Isolated from Journal.",
    rich_markup_mode=None,
)
app.add_typer(simulate_app, name="simulate")
app.add_typer(journal_app, name="journal")
app.add_typer(predictions_app, name="predictions")


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
        from sbm.data.nfl import download_nfl_games, download_nfl_team_stats
        from sbm.units import nfl_unit_weeks, save_units

        typer.echo(f"Ingesting NFL {seasons[0]}-{seasons[-1]}…")
        games = download_nfl_games(seasons)
        path = save_games(League.NFL, games, replace_seasons=set(seasons))
        typer.echo(f"Wrote {len(games)} NFL games to {path}")
        stats = download_nfl_team_stats(seasons)
        weeks = nfl_unit_weeks(stats, games)
        units = save_units(weeks, league=League.NFL, replace_seasons=set(seasons))
        typer.echo(f"Wrote {len(weeks)} NFL unit weeks to {units}")
    if League.CFB in targets:
        from sbm.data.cfb import download_cfb_advanced, download_cfb_games, download_cfb_talent
        from sbm.units import cfb_unit_weeks, save_units

        typer.echo(f"Ingesting CFB FBS {seasons[0]}-{seasons[-1]}…")
        games = download_cfb_games(seasons)
        path = save_games(League.CFB, games, replace_seasons=set(seasons))
        typer.echo(f"Wrote {len(games)} CFB games to {path}")
        advanced = download_cfb_advanced(seasons)
        talent = download_cfb_talent(seasons)
        weeks = cfb_unit_weeks(advanced, talent)
        units = save_units(weeks, league=League.CFB, replace_seasons=set(seasons))
        typer.echo(f"Wrote {len(weeks)} CFB unit weeks to {units}")


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
    from sbm.units import load_unit_book

    lg = _league(league)
    games = load_games(lg)
    if not games:
        raise typer.BadParameter("No games found. Run `sbm ingest` first.")
    ledger = Ledger(Mode.SIMULATION, path=historical_ledger_path(Mode.SIMULATION))
    if ledger.path.exists():
        ledger.path.unlink()
    apply_backtest_to_ledger(
        games, ledger, start_season=start, end_season=end, units=load_unit_book()
    )
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
    """Look-don't-book: print the current-week model slate. Does not write Journal."""
    _run_week_picks(Mode.SIMULATION, season, week, league)


@simulate_app.command("save-week")
def simulate_save_week(
    season: Annotated[int | None, typer.Option()] = None,
    week: Annotated[int | None, typer.Option()] = None,
    league: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Alias for `simulate picks` — print this week's model slate. Does not write a paper book."""
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
    from sbm.units import load_unit_book

    units = load_unit_book()
    if units.weeks:
        from sbm.tune import tune_factors

        factors = tune_factors(games, units)
        factor_path = write_tune_report(factors, report_dir / "factors.json")
        typer.echo(factors.model_dump_json(indent=2))
        typer.echo(f"Wrote {factor_path}")
    typer.echo("Suggested params are not applied automatically.")


@journal_app.command("add")
def journal_add(
    sportsbook: Annotated[str, typer.Option()] = "Novig",
    stake: Annotated[float, typer.Option(help="Stake in dollars")] = ...,
    american_odds: Annotated[int | None, typer.Option()] = None,
    decimal_odds: Annotated[float | None, typer.Option()] = None,
    implied: Annotated[float | None, typer.Option(help="Implied win probability 0-1")] = None,
    kind: Annotated[str, typer.Option()] = "straight",
    league: Annotated[str, typer.Option()] = "nfl",
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
    week: Annotated[int, typer.Option()] = 1,
    team: Annotated[str, typer.Option()] = ...,
    opponent: Annotated[str | None, typer.Option()] = None,
    market: Annotated[str | None, typer.Option()] = None,
    side: Annotated[str | None, typer.Option()] = None,
    line: Annotated[float | None, typer.Option()] = None,
    game_id: Annotated[str | None, typer.Option()] = None,
    notes: Annotated[str | None, typer.Option()] = None,
    extra_leg: Annotated[
        list[str] | None, typer.Option(help="JSON object for another parlay leg")
    ] = None,
) -> None:
    """Log a real ticket. Does not place a wager."""
    import json
    from datetime import UTC, datetime

    from sbm.journal import Journal, new_ticket_id
    from sbm.odds import decimal_to_american, implied_to_american
    from sbm.schema import Leg, Market, Side, Ticket, TicketKind

    if american_odds is None and decimal_odds is not None:
        american_odds = decimal_to_american(decimal_odds)
    if american_odds is None and implied is not None:
        american_odds = implied_to_american(implied)
    if american_odds is None:
        raise typer.BadParameter("Provide --american-odds, --decimal-odds, or --implied")
    parsed_kind = TicketKind(kind.lower())
    lg = League(league.lower())
    parsed_market = Market(market) if market else None
    parsed_side = Side(side) if side else None
    legs = [
        Leg(
            league=lg,
            season=season,
            week=week,
            team_or_side=team,
            game_id=game_id,
            market=parsed_market,
            side=parsed_side,
            market_line=line,
            american_odds=american_odds,
            opponent=opponent,
        )
    ]
    for raw in extra_leg or []:
        payload = json.loads(raw)
        legs.append(Leg.model_validate(payload))
    ticket = Ticket(
        ticket_id=new_ticket_id(),
        season=season,
        sportsbook=sportsbook,
        stake_dollars=stake,
        american_odds=american_odds,
        kind=parsed_kind,
        legs=legs,
        implied_prob=implied,
        notes=notes,
        placed_at=datetime.now(UTC),
    )
    Journal().add(ticket)
    typer.echo(ticket.model_dump_json(indent=2))


@journal_app.command("cashout")
def journal_cashout(
    ticket_id: Annotated[str, typer.Argument()],
    amount: Annotated[float, typer.Option(help="Dollars returned by the book")],
) -> None:
    from sbm.journal import Journal

    ticket = Journal().cashout(ticket_id, amount)
    typer.echo(ticket.model_dump_json(indent=2))


@journal_app.command("settle")
def journal_settle(
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
) -> None:
    from sbm.data.store import games_by_id, load_games
    from sbm.journal import Journal

    book = Journal()
    n = book.settle(games_by_id(load_games()), season=season)
    typer.echo(f"Settled {n} journal tickets for {season}")
    typer.echo(book.year(season).model_dump_json(indent=2))


@journal_app.command("year")
def journal_year(
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
) -> None:
    from sbm.journal import Journal

    typer.echo(Journal().year(season).model_dump_json(indent=2))


@journal_app.command("seed-novig")
def journal_seed_novig() -> None:
    """Load the 2026 Novig tickets already recorded (idempotent)."""
    from sbm.journal import Journal

    added = Journal().seed_novig()
    typer.echo(f"Added {added} Novig tickets")


@journal_app.command("migrate-live")
def journal_migrate_live() -> None:
    """Copy leftover paper rows from data/live/ledger.jsonl into Journal."""
    from sbm.journal import migrate_live_ledger

    n = migrate_live_ledger()
    typer.echo(f"Migrated {n} live paper rows")


@predictions_app.command("init")
def predictions_init(
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
) -> None:
    from sbm.data.store import load_games
    from sbm.predictions import init_book, save_book

    book = init_book(load_games(), season)
    save_book(book)
    typer.echo(f"Initialized {len(book.teams)} team cards for {season}")


@predictions_app.command("sync")
def predictions_sync(
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
) -> None:
    from sbm.data.store import load_games
    from sbm.predictions import load_book, save_book, sync_actuals

    book = load_book(season)
    if book is None:
        raise typer.BadParameter("No predictions file. Run `sbm predictions init`.")
    updated = sync_actuals(book, load_games())
    save_book(updated)
    typer.echo(f"Synced actuals for {season}; picks unchanged")


@predictions_app.command("set")
def predictions_set(
    game_id: Annotated[str, typer.Option()],
    winner: Annotated[str, typer.Option()],
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
) -> None:
    from sbm.predictions import load_book, save_book, set_winner

    book = load_book(season)
    if book is None:
        raise typer.BadParameter("No predictions file. Run `sbm predictions init`.")
    updated = set_winner(book, game_id, winner)
    save_book(updated)
    typer.echo(f"{game_id} -> {winner}")


@predictions_app.command("apply-ranks")
def predictions_apply_ranks(
    file: Annotated[Path, typer.Option(help="JSON object of group -> ranked team names")],
    season: Annotated[int, typer.Option()] = RESEARCH_WINDOWS.hands_off,
) -> None:
    import json

    from sbm.data.store import load_games
    from sbm.predictions import apply_ranks, load_book, save_book

    book = load_book(season)
    if book is None:
        raise typer.BadParameter("No predictions file. Run `sbm predictions init`.")
    ranks = json.loads(file.read_text(encoding="utf-8"))
    updated, filled, leftovers = apply_ranks(book, ranks, load_games())
    save_book(updated)
    typer.echo(f"Filled {filled} remaining games")
    for row in leftovers:
        typer.echo(f"  leftover w{row['week']} {row['matchup']}")


@app.command("live")
def live_renamed() -> None:
    """Renamed to `sbm journal`."""
    typer.echo("Live was renamed to Journal. Use `sbm journal --help`.")
    raise typer.Exit(0)


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
    from sbm.providers.lines import default_provider

    if season is None and mode == Mode.SIMULATION:
        season = RESEARCH_WINDOWS.hands_off
    games = default_provider().attach_lines(load_games(_league(league)))
    if not games:
        raise typer.BadParameter("No games found. Run `sbm ingest` first.")
    picks, _ = current_slate_picks(
        games, mode=mode, season=season, week=week, league=_league(league)
    )
    typer.echo(f"{mode.value}: {len(picks)} model tickets (not booked)")
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
    from sbm.units import load_unit_book

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
        report = week_error_report(
            games, season=season, week=week, mode=mode, units=load_unit_book()
        )
        typer.echo(report.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
