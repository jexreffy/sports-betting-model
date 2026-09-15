import pytest

from sbm.mode import Mode
from sbm.odds import (
    american_to_implied,
    cover_home_spread,
    cover_total,
    expected_value,
    home_cover_prob,
    margin_to_win_prob,
    profit_units,
    remove_vig_two_way,
    settle_pick,
    total_over_prob,
)
from sbm.schema import Game, League, Market, Pick, Side


def test_minus_110_implied():
    assert abs(american_to_implied(-110) - 0.5238) < 0.001


def test_plus_150_implied():
    assert abs(american_to_implied(150) - 0.4) < 1e-9


def test_remove_vig_symmetric_juice():
    fair_a, fair_b = remove_vig_two_way(american_to_implied(-110), american_to_implied(-110))
    assert abs(fair_a - 0.5) < 1e-9
    assert abs(fair_b - 0.5) < 1e-9


def test_ev_fair_minus_110_is_negative():
    # 50% win rate into -110 is a losing bet
    ev = expected_value(0.5, -110)
    assert ev < 0


def test_ev_positive_with_edge():
    ev = expected_value(0.58, -110)
    assert ev > 0


def test_profit_units_win_and_loss():
    assert abs(profit_units(-110, 1.0, True) - 100 / 110) < 1e-9
    assert profit_units(-110, 1.0, False) == -1.0
    assert profit_units(-110, 1.0, True, push=True) == 0.0


def test_home_cover_and_push():
    assert cover_home_spread(7, -3) == "win"
    assert cover_home_spread(3, -3) == "push"
    assert cover_home_spread(2, -3) == "loss"


def test_total_cover():
    assert cover_total(48, 45, Side.OVER) == "win"
    assert cover_total(45, 45, Side.UNDER) == "push"
    assert cover_total(40, 45, Side.OVER) == "loss"


def test_settle_away_spread():
    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
        home_score=20,
        away_score=17,
        spread_close=-3,
    )
    pick = Pick(
        mode=Mode.SIMULATION,
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.SPREAD,
        side=Side.AWAY,
        team_or_side="BAL",
        edge=2.0,
    )
    result, profit = settle_pick(pick, game)
    assert result == "push"
    assert profit == 0.0


def test_cover_prob_is_not_win_prob():
    win = margin_to_win_prob(7.0, 13.8)
    cover = home_cover_prob(7.0, -3.0, 13.8)
    assert cover != win
    assert cover > 0.5
    assert abs(total_over_prob(45.0, 45.0, 10.5) - 0.5) < 1e-9


def test_zero_odds_rejected():
    with pytest.raises(ValueError):
        american_to_implied(0)


def test_settle_moneyline_and_total():
    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
        home_score=27,
        away_score=20,
        spread_close=-3,
        total_close=45,
        home_moneyline=-150,
        away_moneyline=130,
    )
    ml = Pick(
        mode=Mode.SIMULATION,
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.MONEYLINE,
        side=Side.HOME,
        team_or_side="KC",
        edge=0.05,
        american_odds=-150,
    )
    total = Pick(
        mode=Mode.SIMULATION,
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.TOTAL,
        side=Side.OVER,
        team_or_side="over",
        edge=2.0,
    )
    ml_result, ml_profit = settle_pick(ml, game)
    tot_result, tot_profit = settle_pick(total, game)
    assert ml_result == "win"
    assert ml_profit > 0
    assert tot_result == "win"
    assert tot_profit > 0


def test_settle_rejects_unfinished_game():
    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
    )
    pick = Pick(
        mode=Mode.SIMULATION,
        game_id="g1",
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.SPREAD,
        side=Side.HOME,
        team_or_side="KC",
        edge=2.0,
    )
    with pytest.raises(ValueError, match="not final"):
        settle_pick(pick, game)
