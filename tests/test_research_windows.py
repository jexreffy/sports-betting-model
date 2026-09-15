from sbm.backtest import walk_forward
from sbm.config import RESEARCH_WINDOWS
from sbm.mode import Mode
from sbm.schema import Game, League, ResearchWindow


def _g(season: int, week: int, gid: str) -> Game:
    return Game(
        game_id=gid,
        league=League.NFL,
        season=season,
        week=week,
        home_team="AAA",
        away_team="BBB",
        home_score=24,
        away_score=17,
        spread_close=-20,
        total_close=44,
    )


def test_canonical_windows() -> None:
    w = RESEARCH_WINDOWS
    assert w.window_for(2018) == ResearchWindow.WARMUP
    assert w.window_for(2021) == ResearchWindow.SEARCH
    assert w.window_for(2024) == ResearchWindow.HOLDOUT
    assert w.window_for(2026) == ResearchWindow.HANDS_OFF
    assert w.record_historical_picks(2019) is False
    assert w.record_historical_picks(2022) is True
    assert w.record_historical_picks(2025) is True
    assert w.record_historical_picks(2026) is False


def test_warmup_and_hands_off_do_not_create_picks() -> None:
    games = [
        _g(2018, 1, "w"),
        _g(2022, 1, "s"),
        _g(2024, 1, "h"),
        _g(2026, 1, "x"),
    ]
    picks, _ = walk_forward(games, mode=Mode.SIMULATION)
    seasons = {p.season for p in picks}
    assert 2018 not in seasons
    assert 2026 not in seasons
    assert 2022 in seasons
    assert 2024 in seasons
    assert {p.research_window for p in picks if p.season == 2022} == {ResearchWindow.SEARCH}
    assert {p.research_window for p in picks if p.season == 2024} == {ResearchWindow.HOLDOUT}
