from pathlib import Path

import pytest

from sbm.errors import (
    LeagueBias,
    bias_by_league,
    explain_game_row,
    explain_league_bias,
    row_from_prediction,
    week_error_report,
)
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
    lines = explain_game_row(row)
    assert lines[0] == (
        "Model had the home team 7 points better. "
        "The ingested close was the home team 3 points better. "
        "Home won by 7."
    )
    assert lines[1] == "Model total 41. The ingested close was 45. They scored 47."
    bias = bias_by_league([row])[0]
    assert bias.mean_margin_vs_close == 4.0
    assert bias.mae_margin_vs_close == 4.0
    nfl = explain_league_bias(bias)
    assert nfl[0].startswith("On 1 NFL game, the model was off the close for the spread")
    assert "typical miss 4" in nfl[0]


def test_league_bias_reads_as_reliable_nfl_or_early_cfb() -> None:
    nfl = explain_league_bias(
        LeagueBias(
            league=League.NFL,
            n=16,
            mean_margin_vs_close=0.3,
            mae_margin_vs_close=1.6,
            mae_margin_vs_final=12.3,
            mae_total_vs_close=3.1,
        )
    )
    assert "sat on the close" in nfl[0]
    assert any("reliable slate" in line for line in nfl)
    assert any("ordinary football" in line for line in nfl)
    cfb = explain_league_bias(
        LeagueBias(
            league=League.CFB,
            n=71,
            mean_margin_vs_close=-6.4,
            mae_margin_vs_close=11.7,
            mae_margin_vs_final=17.4,
            mae_total_vs_close=3.8,
        ),
        early_season=True,
        prior=LeagueBias(league=League.CFB, n=75, mae_margin_vs_close=15.7),
    )
    assert "wild versus the close" in cfb[0]
    assert any("weeks 1–3" in line for line in cfb)
    assert any("shrank" in line for line in cfb)


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
