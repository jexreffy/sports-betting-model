from sbm.backtest import current_slate_picks, infer_current_week, walk_forward
from sbm.mode import Mode
from sbm.models.engine import ModelEngine
from sbm.schema import Game, League


def _g(
    week: int,
    home: str,
    away: str,
    hs: int | None,
    aws: int | None,
    gid: str,
    spread: float = -3,
) -> Game:
    return Game(
        game_id=gid,
        league=League.NFL,
        season=2024,
        week=week,
        home_team=home,
        away_team=away,
        home_score=hs,
        away_score=aws,
        spread_close=spread,
        total_close=45,
    )


def test_week2_prediction_ignores_week2_scores() -> None:
    games = [
        _g(1, "AAA", "BBB", 30, 10, "w1"),
        _g(2, "AAA", "CCC", 99, 0, "w2", spread=-20),
    ]
    engine = ModelEngine(League.NFL)
    engine.update(games[0])
    honest = engine.predict(games[1]).predicted_home_margin

    leaked = ModelEngine(League.NFL)
    leaked.update(games[0])
    leaked.update(games[1])
    after_future = leaked.predict(games[1]).predicted_home_margin
    assert honest != after_future

    picks, engines = walk_forward(games, mode=Mode.SIMULATION)
    # Engine after walk_forward has seen week 2, but the pick used the pre-update state.
    assert picks
    week2 = [p for p in picks if p.game_id == "w2" and p.market == "spread"]
    assert week2
    # Rebuild the honest week-2 margin
    assert abs(engines[League.NFL].elo.rating("AAA") - leaked.elo.rating("AAA")) < 1e-6


def test_current_slate_does_not_train_on_same_week() -> None:
    games = [
        _g(1, "AAA", "BBB", 27, 10, "w1"),
        _g(2, "AAA", "CCC", 50, 0, "w2a", spread=-20),
        _g(2, "DDD", "EEE", 3, 40, "w2b", spread=14),
    ]
    picks, engines = current_slate_picks(games, mode=Mode.SIMULATION, season=2024, week=2)
    # Ratings should equal an engine that only saw week 1
    only_w1 = ModelEngine(League.NFL)
    only_w1.update(games[0])
    assert engines[League.NFL].elo.rating("AAA") == only_w1.elo.rating("AAA")
    assert engines[League.NFL].elo.rating("CCC") == only_w1.elo.rating("CCC")
    assert any(p.game_id.startswith("w2") for p in picks)


def test_infer_week_when_slate_is_complete() -> None:
    games = [
        _g(1, "AAA", "BBB", 24, 17, "w1"),
        _g(2, "AAA", "CCC", 20, 17, "w2"),
    ]
    assert infer_current_week(games) == (2024, 2)
    assert infer_current_week([]) is None


def test_infer_week_skips_stray_historical_unplayed() -> None:
    games = [
        Game(
            game_id="old",
            league=League.CFB,
            season=2024,
            week=5,
            home_team="App State",
            away_team="Liberty",
            home_score=None,
            away_score=None,
        ),
        Game(
            game_id="now",
            league=League.CFB,
            season=2026,
            week=2,
            home_team="Michigan",
            away_team="Oklahoma",
            home_score=None,
            away_score=None,
        ),
    ]
    assert infer_current_week(games) == (2026, 2)


def test_cfb_week_threshold_skips_early_scoring() -> None:
    games = [
        Game(
            game_id="cfb-1",
            league=League.CFB,
            season=2024,
            week=1,
            home_team="ALA",
            away_team="USF",
            home_score=42,
            away_score=10,
            spread_close=-28,
            total_close=55,
        )
    ]
    picks, _ = walk_forward(games, mode=Mode.SIMULATION)
    assert picks == []


def test_current_slate_still_flags_early_cfb_weeks() -> None:
    games = [
        Game(
            game_id="cfb-2",
            league=League.CFB,
            season=2026,
            week=2,
            home_team="Michigan",
            away_team="Oklahoma",
            spread_close=-20,
            total_close=55,
        )
    ]
    picks, _ = current_slate_picks(games, mode=Mode.SIMULATION, season=2026, week=2)
    assert picks
    assert all(p.week == 2 for p in picks)
