from datetime import UTC, datetime

from sbm.config import Settings, get_settings, params_for
from sbm.mode import Mode
from sbm.odds import (
    american_to_implied,
    expected_value,
    home_cover_prob,
    remove_vig_two_way,
    total_over_prob,
)
from sbm.schema import Game, Market, Pick, Prediction, Side, StakeColumn


def picks_from_prediction(
    game: Game,
    pred: Prediction,
    mode: Mode,
    settings: Settings | None = None,
    *,
    apply_week_gate: bool = True,
) -> list[Pick]:
    settings = settings or get_settings()
    params = params_for(game.league)
    # Week 1-3 CFB is too noisy to count in historical P&L; the live board still shows sides.
    if apply_week_gate and game.week < params.min_week_to_score:
        return []

    now = datetime.now(UTC)
    out: list[Pick] = []

    if game.spread_close is not None:
        market_home_margin = -game.spread_close
        edge_home = pred.predicted_home_margin - market_home_margin
        if abs(edge_home) >= settings.spread_edge_points:
            side = Side.HOME if edge_home > 0 else Side.AWAY
            team = game.home_team if side == Side.HOME else game.away_team
            model_line = -pred.predicted_home_margin
            cover_home = home_cover_prob(
                pred.predicted_home_margin, game.spread_close, params.margin_sigma
            )
            out.append(
                Pick(
                    mode=mode,
                    game_id=game.game_id,
                    league=game.league,
                    season=game.season,
                    week=game.week,
                    market=Market.SPREAD,
                    side=side,
                    team_or_side=team,
                    model_line=round(model_line, 2),
                    market_line=game.spread_close,
                    model_prob=round(cover_home if side == Side.HOME else 1.0 - cover_home, 4),
                    edge=round(abs(edge_home), 3),
                    american_odds=settings.juice,
                    placed_at=now,
                    column=StakeColumn.SYSTEM,
                )
            )

    if game.total_close is not None:
        edge_over = pred.predicted_total - game.total_close
        if abs(edge_over) >= settings.total_edge_points:
            side = Side.OVER if edge_over > 0 else Side.UNDER
            over_p = total_over_prob(pred.predicted_total, game.total_close, params.total_sigma)
            out.append(
                Pick(
                    mode=mode,
                    game_id=game.game_id,
                    league=game.league,
                    season=game.season,
                    week=game.week,
                    market=Market.TOTAL,
                    side=side,
                    team_or_side=side.value,
                    model_line=round(pred.predicted_total, 2),
                    market_line=game.total_close,
                    model_prob=round(over_p if side == Side.OVER else 1.0 - over_p, 4),
                    edge=round(abs(edge_over), 3),
                    american_odds=settings.juice,
                    placed_at=now,
                    column=StakeColumn.SYSTEM,
                )
            )

    if game.home_moneyline is not None and game.away_moneyline is not None:
        raw_h = american_to_implied(game.home_moneyline)
        raw_a = american_to_implied(game.away_moneyline)
        fair_h, fair_a = remove_vig_two_way(raw_h, raw_a)
        ev_home = expected_value(pred.home_win_prob, game.home_moneyline)
        ev_away = expected_value(1 - pred.home_win_prob, game.away_moneyline)
        if ev_home >= settings.moneyline_min_ev and ev_home >= ev_away:
            out.append(
                Pick(
                    mode=mode,
                    game_id=game.game_id,
                    league=game.league,
                    season=game.season,
                    week=game.week,
                    market=Market.MONEYLINE,
                    side=Side.HOME,
                    team_or_side=game.home_team,
                    model_prob=round(pred.home_win_prob, 4),
                    market_prob=round(fair_h, 4),
                    edge=round(ev_home, 4),
                    american_odds=game.home_moneyline,
                    placed_at=now,
                    column=StakeColumn.SYSTEM,
                )
            )
        elif ev_away >= settings.moneyline_min_ev:
            out.append(
                Pick(
                    mode=mode,
                    game_id=game.game_id,
                    league=game.league,
                    season=game.season,
                    week=game.week,
                    market=Market.MONEYLINE,
                    side=Side.AWAY,
                    team_or_side=game.away_team,
                    model_prob=round(1 - pred.home_win_prob, 4),
                    market_prob=round(fair_a, 4),
                    edge=round(ev_away, 4),
                    american_odds=game.away_moneyline,
                    placed_at=now,
                    column=StakeColumn.SYSTEM,
                )
            )

    return out


def pick_from_market_side(
    game: Game,
    pred: Prediction | None,
    *,
    mode: Mode,
    market: Market,
    side: Side,
    column: StakeColumn,
    skipped: bool = False,
    settings: Settings | None = None,
) -> Pick:
    """Build a diary pick for any posted side, even if the model did not clear the edge gate."""
    settings = settings or get_settings()
    params = params_for(game.league)
    now = datetime.now(UTC)
    if market == Market.SPREAD:
        if game.spread_close is None:
            raise ValueError("No spread posted")
        if side not in {Side.HOME, Side.AWAY}:
            raise ValueError("Spread side must be home or away")
        team = game.home_team if side == Side.HOME else game.away_team
        model_line = None if pred is None else round(-pred.predicted_home_margin, 2)
        market_home_margin = -game.spread_close
        edge = 0.0
        model_prob = None
        if pred is not None:
            edge = abs(pred.predicted_home_margin - market_home_margin)
            cover_home = home_cover_prob(
                pred.predicted_home_margin, game.spread_close, params.margin_sigma
            )
            model_prob = round(cover_home if side == Side.HOME else 1.0 - cover_home, 4)
        return Pick(
            mode=mode,
            game_id=game.game_id,
            league=game.league,
            season=game.season,
            week=game.week,
            market=Market.SPREAD,
            side=side,
            team_or_side=team,
            model_line=model_line,
            market_line=game.spread_close,
            model_prob=model_prob,
            edge=round(edge, 3),
            american_odds=settings.juice,
            placed_at=now,
            column=column,
            skipped=skipped,
        )
    if market == Market.TOTAL:
        if game.total_close is None:
            raise ValueError("No total posted")
        if side not in {Side.OVER, Side.UNDER}:
            raise ValueError("Total side must be over or under")
        edge = 0.0
        model_prob = None
        model_line = None if pred is None else round(pred.predicted_total, 2)
        if pred is not None:
            edge = abs(pred.predicted_total - game.total_close)
            over_p = total_over_prob(pred.predicted_total, game.total_close, params.total_sigma)
            model_prob = round(over_p if side == Side.OVER else 1.0 - over_p, 4)
        return Pick(
            mode=mode,
            game_id=game.game_id,
            league=game.league,
            season=game.season,
            week=game.week,
            market=Market.TOTAL,
            side=side,
            team_or_side=side.value,
            model_line=model_line,
            market_line=game.total_close,
            model_prob=model_prob,
            edge=round(edge, 3),
            american_odds=settings.juice,
            placed_at=now,
            column=column,
            skipped=skipped,
        )
    if market == Market.MONEYLINE:
        if game.home_moneyline is None or game.away_moneyline is None:
            raise ValueError("No moneyline posted")
        if side not in {Side.HOME, Side.AWAY}:
            raise ValueError("Moneyline side must be home or away")
        odds = game.home_moneyline if side == Side.HOME else game.away_moneyline
        team = game.home_team if side == Side.HOME else game.away_team
        model_prob = None
        market_prob = None
        edge = 0.0
        raw_h = american_to_implied(game.home_moneyline)
        raw_a = american_to_implied(game.away_moneyline)
        fair_h, fair_a = remove_vig_two_way(raw_h, raw_a)
        if pred is not None:
            win_p = pred.home_win_prob if side == Side.HOME else 1.0 - pred.home_win_prob
            model_prob = round(win_p, 4)
            market_prob = round(fair_h if side == Side.HOME else fair_a, 4)
            edge = round(expected_value(model_prob, odds), 4)
        return Pick(
            mode=mode,
            game_id=game.game_id,
            league=game.league,
            season=game.season,
            week=game.week,
            market=Market.MONEYLINE,
            side=side,
            team_or_side=team,
            model_prob=model_prob,
            market_prob=market_prob,
            edge=edge,
            american_odds=odds,
            placed_at=now,
            column=column,
            skipped=skipped,
        )
    raise ValueError(f"Unknown market {market}")
