from sbm.mode import Mode
from sbm.schema import Game, League
from sbm.web.board import game_cards


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
    names = [m["name"] for m in card["markets"]]
    assert names == ["spread", "total", "moneyline"]
