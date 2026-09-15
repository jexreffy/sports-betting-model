from __future__ import annotations

from collections import defaultdict

from sbm.config import RESEARCH_WINDOWS, ResearchWindows
from sbm.mode import Mode
from sbm.models.engine import ModelEngine
from sbm.paper import Ledger
from sbm.picks import picks_from_prediction
from sbm.schema import Game, League, Pick, Prediction


def walk_forward(
    games: list[Game],
    *,
    mode: Mode = Mode.SIMULATION,
    start_season: int | None = None,
    end_season: int | None = None,
    record_picks: bool = True,
    windows: ResearchWindows | None = None,
) -> tuple[list[Pick], dict[League, ModelEngine]]:
    """
    Process games in time order. Ratings update only after each game is predicted.

    Default research split (NFL and CFB):
    warmup 2015-2020 (update only), search 2021-2023 + holdout 2024-2025 (paper),
    2026 hands-off for historical P&L.
    """
    split = windows or RESEARCH_WINDOWS
    ordered = sorted(
        games,
        key=lambda g: (g.season, g.week, g.kickoff.isoformat() if g.kickoff else "", g.game_id),
    )
    engines: dict[League, ModelEngine] = {}
    picks: list[Pick] = []

    for game in ordered:
        if start_season is not None and game.season < start_season:
            continue
        if end_season is not None and game.season > end_season:
            continue
        if split.window_for(game.season) is None:
            continue
        engine = engines.setdefault(game.league, ModelEngine(game.league))
        window = split.window_for(game.season)
        if window and not split.record_historical_picks(game.season):
            if game.is_final:
                engine.update(game)
            continue
        pred = engine.predict(game)
        if record_picks:
            for pick in picks_from_prediction(game, pred, mode):
                picks.append(pick.model_copy(update={"research_window": window}))
        if game.is_final:
            engine.update(game)
    return picks, engines


def infer_current_week(games: list[Game]) -> tuple[int, int] | None:
    """Latest season that still has open games, then that season's first open week.

    Ignores a stray cancelled historical game (e.g. 2024 with no score) so the
    board does not jump back two years.
    """
    unfinished = [g for g in games if not g.is_final]
    if unfinished:
        season = max(g.season for g in unfinished)
        week = min(g.week for g in unfinished if g.season == season)
        return season, week
    if not games:
        return None
    last = max(games, key=lambda g: (g.season, g.week))
    return last.season, last.week


def current_slate(
    games: list[Game],
    *,
    mode: Mode,
    season: int | None = None,
    week: int | None = None,
    league: League | None = None,
) -> tuple[list[tuple[Game, Prediction]], list[Pick], dict[League, ModelEngine]]:
    """Ratings from prior weeks, then this week's games + predictions. No intra-week leakage."""
    by_league: dict[League, list[Game]] = defaultdict(list)
    for game in games:
        if league and game.league != league:
            continue
        by_league[game.league].append(game)

    engines: dict[League, ModelEngine] = {}
    picks: list[Pick] = []
    slate: list[tuple[Game, Prediction]] = []

    for lg, lg_games in by_league.items():
        ordered = sorted(
            lg_games,
            key=lambda g: (g.season, g.week, g.kickoff.isoformat() if g.kickoff else "", g.game_id),
        )
        target_season, target_week = season, week
        if target_season is None or target_week is None:
            inferred = infer_current_week(ordered)
            if inferred is None:
                continue
            target_season = target_season or inferred[0]
            target_week = target_week or inferred[1]

        engine = engines.setdefault(lg, ModelEngine(lg))
        week_games: list[Game] = []
        for game in ordered:
            if (game.season, game.week) < (target_season, target_week):
                engine.update(game)
            elif (game.season, game.week) == (target_season, target_week):
                week_games.append(game)
        for game in week_games:
            pred = engine.predict(game)
            slate.append((game, pred))
            picks.extend(picks_from_prediction(game, pred, mode, apply_week_gate=False))
    slate.sort(
        key=lambda item: (
            item[0].kickoff.isoformat() if item[0].kickoff else "",
            item[0].game_id,
        )
    )
    return slate, picks, engines


def current_slate_picks(
    games: list[Game],
    *,
    mode: Mode,
    season: int | None = None,
    week: int | None = None,
    league: League | None = None,
) -> tuple[list[Pick], dict[League, ModelEngine]]:
    """Build ratings from prior weeks, then pick the target week. No intra-week leakage."""
    _slate, picks, engines = current_slate(
        games, mode=mode, season=season, week=week, league=league
    )
    return picks, engines


def apply_backtest_to_ledger(
    games: list[Game],
    ledger: Ledger,
    *,
    start_season: int | None = None,
    end_season: int | None = None,
) -> int:
    if ledger.mode != Mode.SIMULATION:
        raise ValueError("Historical backtests may only write the simulation ledger")
    # Caller must pass the historical ledger path, not the current-week paper book.
    picks, _ = walk_forward(
        games,
        mode=Mode.SIMULATION,
        start_season=start_season,
        end_season=end_season,
        windows=RESEARCH_WINDOWS,
    )
    added = ledger.record_picks(picks)
    by_id = {g.game_id: g for g in games}
    ledger.settle(by_id)
    return added


def picks_by_week(picks: list[Pick]) -> dict[tuple[int, int], list[Pick]]:
    grouped: dict[tuple[int, int], list[Pick]] = defaultdict(list)
    for pick in picks:
        grouped[(pick.season, pick.week)].append(pick)
    return grouped
