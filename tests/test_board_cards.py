from sbm.mode import Mode
from sbm.schema import Game, League
from sbm.web.board import (
    fade_fill,
    game_cards,
    honesty_flags,
    is_international_venue,
    market_favorite_team,
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
        spread_close=-3.0,
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
    assert spread["model_fade"] is False
    assert spread["fill"] == "you"
    total = next(m for m in cards[0]["markets"] if m["name"] == "total")
    assert total["you_fade"] is False
    assert fade_fill(you_fade=True, model_fade=False) == "you"


def test_model_fade_without_you_is_yellow() -> None:
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
    assert spread["you_fade"] is False
    assert spread["fill"] == "model"
    assert spread["warning"] is True
    assert cards[0]["fill"] in {"model", "both"}
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
