from sbm.models.engine import ModelEngine
from sbm.odds import margin_to_win_prob
from sbm.schema import Game, League


def _game(home: str = "AAA", away: str = "BBB") -> Game:
    return Game(
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        home_team=home,
        away_team=away,
    )


def test_equal_clubs_home_is_favored_by_hfa() -> None:
    pred = ModelEngine(League.NFL).predict(_game())
    assert pred.predicted_home_margin > 0
    assert pred.home_win_prob > 0.5
    assert pred.predicted_total > 0


def test_margin_to_win_prob_is_symmetric() -> None:
    assert abs(margin_to_win_prob(0.0) - 0.5) < 1e-9
    assert margin_to_win_prob(7.0) > 0.5
    assert abs(margin_to_win_prob(7.0) + margin_to_win_prob(-7.0) - 1.0) < 1e-9
