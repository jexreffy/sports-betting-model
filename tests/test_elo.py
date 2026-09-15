from sbm.config import NFL_PARAMS
from sbm.models.elo import EloBook
from sbm.models.totals import ScoringBook
from sbm.schema import Game, League


def _game(week: int, home_score: int, away_score: int, gid: str) -> Game:
    return Game(
        game_id=gid,
        league=League.NFL,
        season=2024,
        week=week,
        home_team="AAA",
        away_team="BBB",
        home_score=home_score,
        away_score=away_score,
        spread_close=-3,
        total_close=44,
    )


def test_favorite_gains_elo_after_cover() -> None:
    book = EloBook(NFL_PARAMS)
    before_home = book.rating("AAA")
    book.update(_game(1, 31, 10, "w1"))
    assert book.rating("AAA") > before_home
    assert book.rating("BBB") < NFL_PARAMS.base_elo


def test_predict_does_not_persist_season_revert() -> None:
    book = EloBook(NFL_PARAMS)
    book.update(_game(1, 31, 10, "w1"))
    stored = book.rating("AAA")
    next_year = Game(
        game_id="w2",
        league=League.NFL,
        season=2025,
        week=1,
        home_team="AAA",
        away_team="BBB",
    )
    first = book.predicted_home_margin(next_year)
    assert book.rating("AAA") == stored
    second = book.predicted_home_margin(next_year)
    assert first == second
    assert book.rating("AAA") == stored


def test_totals_predict_does_not_persist_revert() -> None:
    book = ScoringBook(NFL_PARAMS)
    book.update(_game(1, 40, 35, "w1"))
    stored_off = book.off["AAA"]
    next_year = Game(
        game_id="w2",
        league=League.NFL,
        season=2025,
        week=1,
        home_team="AAA",
        away_team="BBB",
    )
    book.predicted_total(next_year)
    assert book.off["AAA"] == stored_off


def test_totals_move_toward_observed_scoring() -> None:
    book = ScoringBook(NFL_PARAMS)
    pred_before = book.predicted_total(
        Game(
            game_id="x",
            league=League.NFL,
            season=2024,
            week=1,
            home_team="AAA",
            away_team="BBB",
        )
    )
    book.update(_game(1, 40, 35, "w1"))
    pred_after = book.predicted_total(
        Game(
            game_id="y",
            league=League.NFL,
            season=2024,
            week=2,
            home_team="AAA",
            away_team="BBB",
        )
    )
    assert pred_after > pred_before
