from sbm.config import get_settings
from sbm.mode import Mode
from sbm.schema import Game, League, Market, Pick, Side, StakeColumn
from sbm.web.board import game_cards, honesty_flags


def test_honesty_flag_around_threshold() -> None:
    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=5,
        home_team="KC",
        away_team="BAL",
        spread_close=-3.0,
    )
    quiet = Pick(
        mode=Mode.SIMULATION,
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=5,
        market=Market.SPREAD,
        side=Side.HOME,
        team_or_side="KC",
        edge=get_settings().noisy_edge_points,
        column=StakeColumn.SYSTEM,
    )
    loud = quiet.model_copy(update={"edge": get_settings().noisy_edge_points + 0.1})
    assert honesty_flags(game, quiet)["noisy"] is False
    assert honesty_flags(game, loud)["noisy"] is True


def test_early_cfb_is_flagged() -> None:
    game = Game(
        game_id="c1",
        league=League.CFB,
        season=2026,
        week=1,
        home_team="Alabama",
        away_team="Western Kentucky",
        spread_close=-28.0,
        total_close=55.0,
    )
    flags = honesty_flags(game, None)
    assert flags["early_season"] is True
    assert flags["warning"] is True


def test_international_nfl_is_warning() -> None:
    game = Game(
        game_id="lon",
        league=League.NFL,
        season=2026,
        week=3,
        home_team="BAL",
        away_team="DAL",
        venue="Tottenham Hotspur Stadium",
    )
    flags = honesty_flags(game, None)
    assert flags["international"] is True
    assert flags["warning"] is True


def test_noisy_class_on_cards() -> None:
    games = [
        Game(
            game_id="g1",
            league=League.NFL,
            season=2024,
            week=5,
            home_team="KC",
            away_team="BUF",
            home_score=None,
            away_score=None,
            spread_close=-28.0,
            total_close=60.0,
            home_moneyline=-800,
            away_moneyline=600,
        )
    ]
    cards, _ = game_cards(games, Mode.SIMULATION)
    assert cards[0]["noisy"] is True
    spread = next(m for m in cards[0]["markets"] if m["name"] == "spread")
    assert spread["noisy"] is True
