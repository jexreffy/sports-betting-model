import pandas as pd

from sbm.data.nfl import schedules_to_games
from sbm.schema import League


def test_schedules_to_games_maps_spread_as_home_line() -> None:
    df = pd.DataFrame(
        [
            {
                "game_id": "2024_01_BAL_KC",
                "season": 2024,
                "week": 1,
                "game_type": "REG",
                "home_team": "KC",
                "away_team": "BAL",
                "home_score": 27,
                "away_score": 20,
                "spread_line": 3.0,
                "total_line": 47.5,
                "home_moneyline": -155,
                "away_moneyline": 135,
                "gameday": "2024-09-05",
                "gametime": "20:20",
                "home_rest": 10,
                "away_rest": 10,
                "stadium": "Arrowhead Stadium",
            }
        ]
    )
    games = schedules_to_games(df)
    assert len(games) == 1
    game = games[0]
    assert game.league == League.NFL
    # nflverse +3 home margin → sportsbook SEA/KC -3
    assert game.spread_close == -3.0
    assert game.total_close == 47.5
    assert game.home_margin == 7
    assert game.venue == "Arrowhead Stadium"
    assert game.home_conference == "AFC"
    assert game.away_conference == "AFC"


def test_preseason_rows_are_dropped() -> None:
    df = pd.DataFrame(
        [
            {
                "game_id": "2024_pre_KC_SF",
                "season": 2024,
                "week": 1,
                "game_type": "PRE",
                "home_team": "KC",
                "away_team": "SF",
                "home_score": 20,
                "away_score": 17,
                "spread_line": 3.0,
                "total_line": 40,
            }
        ]
    )
    assert schedules_to_games(df) == []
