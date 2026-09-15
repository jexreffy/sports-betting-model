from pathlib import Path

from sbm.config import RESEARCH_WINDOWS
from sbm.schema import Game, League
from sbm.tune import tune, write_tune_report


def _g(season: int, week: int, gid: str, home: int = 24, away: int = 17) -> Game:
    return Game(
        game_id=gid,
        league=League.NFL,
        season=season,
        week=week,
        home_team="AAA",
        away_team="BBB",
        home_score=home,
        away_score=away,
        spread_close=-3.0,
        total_close=44.0,
    )


def test_tune_search_holdout_split_skips_2026(tmp_path: Path) -> None:
    games = [
        _g(2020, 1, "warm"),
        _g(2022, 1, "search"),
        _g(2024, 1, "hold"),
        _g(2026, 1, "hands", home=99, away=0),
    ]
    report = tune(games, edge_grid=(1.5,), k_grid=(20.0,))
    assert report.search_seasons == (RESEARCH_WINDOWS.search_start, RESEARCH_WINDOWS.search_end)
    assert report.holdout_seasons == (RESEARCH_WINDOWS.holdout_start, RESEARCH_WINDOWS.holdout_end)
    without_2026 = tune(games[:-1], edge_grid=(1.5,), k_grid=(20.0,))
    assert report.chosen.search_units == without_2026.chosen.search_units
    assert report.chosen.holdout_units == without_2026.chosen.holdout_units
    path = write_tune_report(report, tmp_path / "tune.json")
    assert path.exists()
    assert "hands_off" not in path.read_text(encoding="utf-8")
