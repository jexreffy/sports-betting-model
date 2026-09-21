from pathlib import Path

import pytest

from sbm.errors import row_from_prediction, week_error_report
from sbm.mode import Mode
from sbm.schema import Game, League, Prediction
from sbm.units import UnitBook, UnitWeek


def test_signed_errors_vs_close_and_final() -> None:
    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=2,
        home_team="KC",
        away_team="BAL",
        home_score=27,
        away_score=20,
        spread_close=-3.0,
        total_close=45.0,
    )
    pred = Prediction(
        game_id="g1",
        predicted_home_margin=7.0,
        predicted_total=41.0,
        home_win_prob=0.7,
    )
    row = row_from_prediction(game, pred)
    assert row.margin_vs_close == 4.0
    assert row.margin_vs_final == 0.0
    assert row.total_vs_close == -4.0
    assert row.total_vs_final == -6.0


def test_week_error_report_uses_the_unit_book() -> None:
    game = Game(
        game_id="g",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="AAA",
        away_team="BBB",
        spread_close=0.0,
    )
    book = UnitBook(
        [
            UnitWeek(
                league=League.NFL,
                season=2023,
                week=18,
                team="AAA",
                rush_off=1.0,
                rush_allowed=0.0,
                pass_off=0.0,
                pass_allowed=0.0,
            ),
            UnitWeek(
                league=League.NFL,
                season=2023,
                week=18,
                team="BBB",
                rush_off=-1.0,
                rush_allowed=0.0,
                pass_off=0.0,
                pass_allowed=0.0,
            ),
        ]
    )
    bare = week_error_report([game], season=2024, week=1)
    moved = week_error_report([game], season=2024, week=1, units=book)
    assert moved.games[0].margin_vs_close == bare.games[0].margin_vs_close + 4.0


def test_week_error_report_empty_slate() -> None:
    report = week_error_report([], season=2026, week=1, mode=Mode.SIMULATION)
    assert report.n_games == 0
    assert report.by_league == []


def test_simulation_errors_do_not_need_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.journal import Journal

    book = Journal()
    book.year(2026)
    games = [
        Game(
            game_id="g1",
            league=League.NFL,
            season=2026,
            week=1,
            home_team="KC",
            away_team="BAL",
            home_score=24,
            away_score=17,
            spread_close=-3.0,
            total_close=44.0,
        )
    ]
    report = week_error_report(games, season=2026, week=1, mode=Mode.SIMULATION)
    assert report.n_games == 1
    assert report.by_league[0].league == League.NFL
    assert book.load() == []
