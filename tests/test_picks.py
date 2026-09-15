from sbm.config import NFL_PARAMS, Settings
from sbm.mode import Mode
from sbm.odds import home_cover_prob, margin_to_win_prob
from sbm.picks import pick_from_market_side, picks_from_prediction
from sbm.schema import Game, League, Market, Prediction, Side, StakeColumn


def _game(**kwargs: object) -> Game:
    base: dict[str, object] = {
        "game_id": "g1",
        "league": League.NFL,
        "season": 2024,
        "week": 5,
        "home_team": "KC",
        "away_team": "BAL",
        "spread_close": -3.0,
        "total_close": 45.0,
        "home_moneyline": -110,
        "away_moneyline": -110,
    }
    base.update(kwargs)
    return Game.model_validate(base)


def _settings() -> Settings:
    return Settings(spread_edge_points=1.5, total_edge_points=1.5, moneyline_min_ev=0.03)


def test_spread_and_total_follow_model_edge() -> None:
    pred = Prediction(
        game_id="g1",
        predicted_home_margin=7.0,
        predicted_total=38.0,
        home_win_prob=0.72,
    )
    picks = picks_from_prediction(_game(), pred, Mode.SIMULATION, _settings())
    by_market = {p.market: p for p in picks}
    assert by_market[Market.SPREAD].side == Side.HOME
    assert by_market[Market.SPREAD].team_or_side == "KC"
    cover = home_cover_prob(7.0, -3.0, NFL_PARAMS.margin_sigma)
    win = margin_to_win_prob(7.0, NFL_PARAMS.margin_sigma)
    assert by_market[Market.SPREAD].model_prob == round(cover, 4)
    assert by_market[Market.SPREAD].model_prob != round(win, 4)
    assert by_market[Market.TOTAL].side == Side.UNDER
    assert by_market[Market.TOTAL].model_prob is not None
    assert by_market[Market.MONEYLINE].side == Side.HOME


def test_below_threshold_is_a_skip() -> None:
    pred = Prediction(
        game_id="g1",
        predicted_home_margin=3.2,
        predicted_total=45.4,
        home_win_prob=0.51,
    )
    picks = picks_from_prediction(_game(), pred, Mode.SIMULATION, _settings())
    assert picks == []


def test_cfb_week_gate_off_for_current_board() -> None:
    game = _game(league=League.CFB, week=2, spread_close=-20.0)
    pred = Prediction(
        game_id="g1",
        predicted_home_margin=7.0,
        predicted_total=54.0,
        home_win_prob=0.7,
    )
    gated = picks_from_prediction(game, pred, Mode.SIMULATION, _settings(), apply_week_gate=True)
    board = picks_from_prediction(game, pred, Mode.SIMULATION, _settings(), apply_week_gate=False)
    assert gated == []
    assert board


def test_gut_moneyline_without_model_gate() -> None:
    game = _game(home_team="DEN", away_team="JAX", home_moneyline=-140, away_moneyline=120)
    pred = Prediction(
        game_id="g1",
        predicted_home_margin=1.2,
        predicted_total=45.0,
        home_win_prob=0.54,
    )
    gated = picks_from_prediction(game, pred, Mode.LIVE, _settings())
    assert Market.MONEYLINE not in {p.market for p in gated}
    pick = pick_from_market_side(
        game,
        pred,
        mode=Mode.LIVE,
        market=Market.MONEYLINE,
        side=Side.AWAY,
        column=StakeColumn.GUT,
    )
    assert pick.team_or_side == "JAX"
    assert pick.american_odds == 120
    assert pick.column == StakeColumn.GUT
