from sbm.schema import Game, League


def test_final_margin_and_total() -> None:
    game = Game(
        game_id="g",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
        home_score=27,
        away_score=20,
    )
    assert game.is_final
    assert game.home_margin == 7
    assert game.total_points == 47


def test_open_game_has_no_score_stats() -> None:
    game = Game(
        game_id="g",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
    )
    assert not game.is_final
    assert game.home_margin is None
    assert game.total_points is None
