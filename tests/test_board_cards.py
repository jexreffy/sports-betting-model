from sbm.mode import Mode
from sbm.schema import Game, League, Prediction
from sbm.web.board import (
    ats_side_vs_market,
    fade_fill,
    game_cards,
    honesty_flags,
    is_international_venue,
    market_favorite_team,
    moneyline_percents,
    number_fades_market,
    you_ats_side,
    you_fade_spread,
)


def test_cards_group_picks_under_matchup() -> None:
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
            spread_close=-14,
            total_close=60,
            home_moneyline=-400,
            away_moneyline=320,
        )
    ]
    cards, _picks = game_cards(games, Mode.SIMULATION)
    assert len(cards) == 1
    card = cards[0]
    assert card["away_team"] == "BUF"
    assert card["home_team"] == "KC"
    assert card["away_display"] == "Buffalo Bills"
    assert card["home_display"] == "Kansas City Chiefs"
    assert card["away_abbrev"] == "BUF"
    assert "Model" in card["model_context"]
    assert "Neutral" in card["model_context"]
    ranked, _ = game_cards(
        games,
        Mode.SIMULATION,
        you_ranks={("nfl", "KC"): 4, ("nfl", "BUF"): 11},
    )
    assert ranked[0]["fill"] == card["fill"]
    assert ranked[0]["home_rank"] == "You: 4 / Model: 2"
    assert ranked[0]["away_rank"] == "You: 11 / Model: 1"
    spread = next(m for m in card["markets"] if m["name"] == "spread")
    assert spread["market"] == "KC -14.0"
    assert spread["model"] is None or spread["model"].startswith(("KC -", "BUF -", "Pick'em"))
    assert card["model_context"].split(" · ")[0].startswith("Model ")
    assert " +" not in card["model_context"]
    assert {opt["label"] for opt in spread["wager_options"]} == {"BUF", "KC"}
    dog = Game(
        game_id="g-dog",
        league=League.NFL,
        season=2024,
        week=5,
        home_team="KC",
        away_team="BUF",
        spread_close=3.5,
        total_close=47.0,
    )
    dog_cards, _ = game_cards([dog], Mode.SIMULATION)
    dog_spread = next(m for m in dog_cards[0]["markets"] if m["name"] == "spread")
    assert dog_spread["market"] == "BUF -3.5"
    pickem = Game(
        game_id="g-pk",
        league=League.NFL,
        season=2024,
        week=5,
        home_team="KC",
        away_team="BUF",
        spread_close=0.0,
        total_close=47.0,
    )
    pk_cards, _ = game_cards([pickem], Mode.SIMULATION)
    pk_spread = next(m for m in pk_cards[0]["markets"] if m["name"] == "spread")
    assert pk_spread["market"] == "Pick'em"
    names = [m["name"] for m in card["markets"]]
    assert names == ["spread", "total", "moneyline"]
    assert "model_ticket" in card["markets"][0]
    assert "wager_options" in card["markets"][0]


def test_international_dal_bal_is_warning() -> None:
    game = Game(
        game_id="2026_03_DAL_BAL",
        league=League.NFL,
        season=2026,
        week=3,
        home_team="BAL",
        away_team="DAL",
        spread_close=-3.0,
        total_close=44.5,
        home_moneyline=-155,
        away_moneyline=135,
        venue="Tottenham Hotspur Stadium",
    )
    assert is_international_venue(game.venue) is True
    flags = honesty_flags(game, None)
    assert flags["international"] is True
    assert flags["warning"] is True
    cards, _ = game_cards([game], Mode.SIMULATION, season=2026, week=3)
    assert cards[0]["warning"] is True
    assert cards[0]["international"] is True
    assert any(c.startswith("Warning") for c in cards[0]["chips"])


def test_melbourne_and_maracana_count_as_international() -> None:
    assert is_international_venue("Melbourne Cricket Ground") is True
    assert is_international_venue("Maracana Stadium") is True
    assert is_international_venue("Stade de France") is True
    assert is_international_venue("Bernabeu") is True
    assert is_international_venue("Estadio Banorte") is True
    assert is_international_venue("SoFi Stadium") is False
    assert is_international_venue("Caesars Superdome") is False


def test_you_fade_without_model_is_orange() -> None:
    game = Game(
        game_id="g-orange",
        league=League.NFL,
        season=2026,
        week=3,
        home_team="KC",
        away_team="CLE",
        spread_close=-0.5,
        total_close=41.5,
        home_moneyline=-150,
        away_moneyline=130,
    )
    assert market_favorite_team(game) == "KC"
    cards, _ = game_cards(
        [game],
        Mode.SIMULATION,
        season=2026,
        week=3,
        predicted_winners={"g-orange": "CLE"},
    )
    spread = next(m for m in cards[0]["markets"] if m["name"] == "spread")
    assert spread["you_fade"] is True
    assert spread["fill"] == "you"
    assert cards[0]["fill"] == "you"
    total = next(m for m in cards[0]["markets"] if m["name"] == "total")
    assert total["you_fade"] is False
    assert fade_fill(you_fade=True, model_fade=False) == "you"


def test_you_fade_takes_the_points_when_you_still_pick_the_favorite() -> None:
    game = Game(
        game_id="iowa-osu",
        league=League.CFB,
        season=2026,
        week=5,
        home_team="Iowa",
        away_team="Ohio State",
        spread_close=13.5,
        total_close=45.5,
        home_moneyline=425,
        away_moneyline=-575,
        home_conference="Big Ten",
        away_conference="Big Ten",
    )
    pred = Prediction(
        game_id="iowa-osu",
        predicted_home_margin=-2.1,
        predicted_total=46.5,
        home_win_prob=0.45,
    )
    assert market_favorite_team(game) == "Ohio State"
    assert you_fade_spread(game, pred, "Ohio State") is True
    assert you_fade_spread(game, pred, None) is False
    assert number_fades_market(game, -2.1) is True
    assert number_fades_market(game, -4.8) is True
    model_ml, market_ml = moneyline_percents(pred, game, "IOW")
    assert model_ml == "45% IOW"
    assert market_ml == "18% IOW"


def test_opposite_ats_sides_stay_you_fade() -> None:
    """You take the dog; the model lays more. That is not both fade."""
    game = Game(
        game_id="uk-sc",
        league=League.CFB,
        season=2026,
        week=5,
        home_team="South Carolina",
        away_team="Kentucky",
        spread_close=-3.0,
        home_conference="SEC",
        away_conference="SEC",
    )
    pred = Prediction(
        game_id="uk-sc",
        predicted_home_margin=6.2,
        predicted_total=48.0,
        home_win_prob=0.65,
    )
    assert market_favorite_team(game) == "South Carolina"
    assert you_fade_spread(game, pred, "Kentucky") is True
    assert you_ats_side(game, pred, "Kentucky") == "Kentucky"
    assert ats_side_vs_market(game, 6.2) == "South Carolina"
    assert number_fades_market(game, 6.2) is True
    assert number_fades_market(game, -0.5) is True
    assert fade_fill(
        you_fade=True,
        model_fade=True,
        you_side="Kentucky",
        model_side="South Carolina",
    ) == "you"
    cards, _ = game_cards(
        [game],
        Mode.SIMULATION,
        season=2026,
        week=5,
        predicted_winners={"uk-sc": "Kentucky"},
    )
    spread = next(m for m in cards[0]["markets"] if m["name"] == "spread")
    assert spread["you_fade"] is True
    assert spread["fill"] == "you"
    assert cards[0]["fill"] == "you"


def test_laying_more_with_the_favorite_is_a_shared_fade() -> None:
    game = Game(
        game_id="2026_04_LAC_SEA",
        league=League.NFL,
        season=2026,
        week=4,
        home_team="SEA",
        away_team="LAC",
        spread_close=-6.5,
        home_conference="NFC",
        away_conference="AFC",
    )
    pred = Prediction(
        game_id="2026_04_LAC_SEA",
        predicted_home_margin=10.2,
        predicted_total=44.0,
        home_win_prob=0.77,
    )
    assert market_favorite_team(game) == "SEA"
    assert you_fade_spread(game, pred, "SEA") is True
    assert you_ats_side(game, pred, "SEA") == "SEA"
    assert ats_side_vs_market(game, 10.2) == "SEA"
    assert you_fade_spread(game, pred, "LAC") is True
    assert fade_fill(
        you_fade=True,
        model_fade=True,
        you_side="SEA",
        model_side="SEA",
    ) == "both"


def test_picking_the_market_favorite_against_the_model_is_not_a_you_fade() -> None:
    game = Game(
        game_id="fla-miz",
        league=League.CFB,
        season=2026,
        week=5,
        home_team="Missouri",
        away_team="Florida",
        spread_close=4.5,
        home_conference="SEC",
        away_conference="SEC",
    )
    pred = Prediction(
        game_id="fla-miz",
        predicted_home_margin=6.3,
        predicted_total=61.5,
        home_win_prob=0.65,
    )
    assert market_favorite_team(game) == "Florida"
    assert you_fade_spread(game, pred, "Florida") is False
    assert number_fades_market(game, 6.3) is True


def test_same_favorite_inside_a_point_is_not_a_model_fade() -> None:
    game = Game(
        game_id="psu-nw",
        league=League.CFB,
        season=2026,
        week=5,
        home_team="Northwestern",
        away_team="Penn State",
        spread_close=2.5,
        home_conference="Big Ten",
        away_conference="Big Ten",
    )
    pred = Prediction(
        game_id="psu-nw",
        predicted_home_margin=-0.7,
        predicted_total=50.0,
        home_win_prob=0.48,
    )
    assert market_favorite_team(game) == "Penn State"
    assert you_fade_spread(game, pred, "Northwestern") is True
    assert number_fades_market(game, -3.4) is False
    assert number_fades_market(game, -0.7) is True


def test_favorite_to_win_still_fades_a_blown_out_number() -> None:
    game = Game(
        game_id="g-yellow",
        league=League.NFL,
        season=2026,
        week=3,
        home_team="KC",
        away_team="BUF",
        spread_close=-28.0,
        total_close=60.0,
        home_moneyline=-800,
        away_moneyline=600,
    )
    cards, _ = game_cards(
        [game],
        Mode.SIMULATION,
        season=2026,
        week=3,
        predicted_winners={"g-yellow": "KC"},
    )
    spread = next(m for m in cards[0]["markets"] if m["name"] == "spread")
    assert spread["model_fade"] is True
    assert spread["you_fade"] is True
    assert spread["fill"] == "both"
    assert spread["warning"] is True
    assert cards[0]["fill"] == "both"
    assert any(c.startswith("Warning") for c in cards[0]["chips"])


def test_both_fade_is_green_with_warning_badge() -> None:
    game = Game(
        game_id="g-green",
        league=League.NFL,
        season=2026,
        week=3,
        home_team="BAL",
        away_team="DAL",
        spread_close=-28.0,
        total_close=60.0,
        home_moneyline=-800,
        away_moneyline=600,
        venue="Tottenham Hotspur Stadium",
    )
    cards, _ = game_cards(
        [game],
        Mode.SIMULATION,
        season=2026,
        week=3,
        predicted_winners={"g-green": "DAL"},
    )
    spread = next(m for m in cards[0]["markets"] if m["name"] == "spread")
    assert spread["you_fade"] is True
    assert spread["model_fade"] is True
    assert spread["fill"] == "both"
    assert cards[0]["warning"] is True
    assert "Both fade" in cards[0]["chips"]
    assert any(c.startswith("Warning") for c in cards[0]["chips"])
    assert fade_fill(you_fade=True, model_fade=True) == "both"


def test_final_has_no_heatmap_or_current_ranks() -> None:
    game = Game(
        game_id="g-final",
        league=League.NFL,
        season=2026,
        week=3,
        home_team="NYG",
        away_team="DAL",
        home_score=6,
        away_score=40,
        spread_close=-3.0,
        total_close=44.5,
        home_moneyline=-150,
        away_moneyline=130,
        venue="Tottenham Hotspur Stadium",
    )
    assert honesty_flags(game, None)["warning"] is True
    cards, _ = game_cards(
        [game],
        Mode.SIMULATION,
        season=2026,
        week=3,
        predicted_winners={"g-final": "DAL"},
        you_ranks={("nfl", "NYG"): 32, ("nfl", "DAL"): 1},
    )
    card = cards[0]
    assert card["is_final"] is True
    assert card["fill"] == "none"
    assert card["warning"] is False
    assert card["international"] is False
    assert not any(chip.startswith("Warning") for chip in card["chips"])
    assert "You fade" not in card["chips"]
    assert "Model fade" not in card["chips"]
    assert "Both fade" not in card["chips"]
    assert card["away_rank"] is None
    assert card["home_rank"] is None
    spread = next(m for m in card["markets"] if m["name"] == "spread")
    assert spread["fill"] == "none"
    assert spread["you_fade"] is False
    assert spread["model_fade"] is False
    assert spread["warning"] is False
