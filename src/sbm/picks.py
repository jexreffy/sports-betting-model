from datetime import UTC, datetime

from sbm.config import Settings, get_settings, params_for
from sbm.mode import Mode
from sbm.odds import american_to_implied, expected_value, remove_vig_two_way
from sbm.schema import Game, Market, Pick, Prediction, Side


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
                    model_prob=round(
                        pred.home_win_prob if side == Side.HOME else 1 - pred.home_win_prob, 4
                    ),
                    edge=round(abs(edge_home), 3),
                    american_odds=settings.juice,
                    placed_at=now,
                )
            )

    if game.total_close is not None:
        edge_over = pred.predicted_total - game.total_close
        if abs(edge_over) >= settings.total_edge_points:
            side = Side.OVER if edge_over > 0 else Side.UNDER
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
                    edge=round(abs(edge_over), 3),
                    american_odds=settings.juice,
                    placed_at=now,
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
                )
            )

    return out
