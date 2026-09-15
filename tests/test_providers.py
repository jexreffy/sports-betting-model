import pytest

from sbm.providers.lines import PassthroughProvider, TheOddsApiProvider
from sbm.schema import Game, League


def test_passthrough_keeps_lines() -> None:
    game = Game(
        game_id="g",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
        spread_close=-3.5,
        total_close=48,
    )
    out = PassthroughProvider().attach_lines([game])
    assert out[0].spread_close == -3.5


def test_odds_api_stub() -> None:
    with pytest.raises(NotImplementedError):
        TheOddsApiProvider(api_key="x").attach_lines([])
