"""American odds, vig removal, expected value, and settlement helpers."""

from __future__ import annotations

import math

from sbm.schema import Game, Market, Pick, Side


def american_to_decimal(odds: int) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be 0")
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def american_to_implied(odds: int) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be 0")
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def profit_units(american_odds: int, stake_units: float, won: bool, push: bool = False) -> float:
    if push:
        return 0.0
    if won:
        return stake_units * (american_to_decimal(american_odds) - 1.0)
    return -stake_units


def remove_vig_two_way(prob_a: float, prob_b: float) -> tuple[float, float]:
    total = prob_a + prob_b
    if total <= 0:
        raise ValueError("Implied probabilities must be positive")
    return prob_a / total, prob_b / total


def expected_value(model_prob: float, american_odds: int, stake: float = 1.0) -> float:
    """EV in units for a stake, using the model's probability of winning."""
    win_profit = stake * (american_to_decimal(american_odds) - 1.0)
    return model_prob * win_profit - (1.0 - model_prob) * stake


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def margin_to_win_prob(predicted_home_margin: float, margin_sigma: float = 13.5) -> float:
    """P(home wins) from a predicted margin, ignoring ties."""
    if margin_sigma <= 0:
        raise ValueError("margin_sigma must be positive")
    return normal_cdf(predicted_home_margin / margin_sigma)


def cover_home_spread(home_margin: float, home_spread: float) -> str:
    """home_spread is the home team's line (negative = home favored)."""
    adj = home_margin + home_spread
    if abs(adj) < 1e-9:
        return "push"
    return "win" if adj > 0 else "loss"


def cover_total(total_points: float, total_line: float, side: Side) -> str:
    if abs(total_points - total_line) < 1e-9:
        return "push"
    went_over = total_points > total_line
    if side == Side.OVER:
        return "win" if went_over else "loss"
    if side == Side.UNDER:
        return "win" if not went_over else "loss"
    raise ValueError(f"Invalid total side {side}")


def settle_pick(pick: Pick, game: Game) -> tuple[str, float]:
    if not game.is_final:
        raise ValueError(f"Game {game.game_id} is not final")

    if pick.market == Market.SPREAD:
        if game.spread_close is None:
            raise ValueError(f"No spread to settle {game.game_id}")
        home_result = cover_home_spread(game.home_margin or 0.0, game.spread_close)
        if pick.side == Side.HOME:
            result = home_result
        elif pick.side == Side.AWAY:
            result = {"win": "loss", "loss": "win", "push": "push"}[home_result]
        else:
            raise ValueError("Spread pick must be home or away")
    elif pick.market == Market.TOTAL:
        if game.total_close is None or game.total_points is None:
            raise ValueError(f"No total to settle {game.game_id}")
        result = cover_total(game.total_points, game.total_close, pick.side)
    elif pick.market == Market.MONEYLINE:
        if game.home_margin is None:
            raise ValueError(f"No score to settle {game.game_id}")
        if game.home_margin == 0:
            result = "push"
        elif pick.side == Side.HOME:
            result = "win" if game.home_margin > 0 else "loss"
        elif pick.side == Side.AWAY:
            result = "win" if game.home_margin < 0 else "loss"
        else:
            raise ValueError("Moneyline pick must be home or away")
    else:
        raise ValueError(f"Unknown market {pick.market}")

    profit = profit_units(pick.american_odds, pick.units, result == "win", result == "push")
    return result, profit
