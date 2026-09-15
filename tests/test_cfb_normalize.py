from sbm.data.cfb import games_from_cfbd_payloads
from sbm.schema import League


def test_fbs_only_and_consensus_line() -> None:
    games_payload = [
        {
            "id": 1,
            "season": 2024,
            "week": 5,
            "seasonType": "regular",
            "homeTeam": "Michigan",
            "awayTeam": "Ohio State",
            "homePoints": 13,
            "awayPoints": 10,
            "homeClassification": "fbs",
            "awayClassification": "fbs",
            "startDate": "2024-11-30T17:00:00.000Z",
            "neutralSite": False,
        },
        {
            "id": 2,
            "season": 2024,
            "week": 5,
            "seasonType": "regular",
            "homeTeam": "Montana",
            "awayTeam": "Idaho",
            "homePoints": 21,
            "awayPoints": 17,
            "homeClassification": "fcs",
            "awayClassification": "fcs",
        },
    ]
    lines_payload = [
        {
            "id": 1,
            "lines": [
                {
                    "provider": "consensus",
                    "spread": -2.5,
                    "overUnder": 42.5,
                    "homeMoneyline": -140,
                    "awayMoneyline": 120,
                },
            ],
        }
    ]
    games = games_from_cfbd_payloads(games_payload, lines_payload)
    assert len(games) == 1
    game = games[0]
    assert game.league == League.CFB
    assert game.game_id == "cfb-1"
    assert game.spread_close == -2.5
    assert game.total_close == 42.5
    assert game.home_moneyline == -140


def test_missing_classification_is_dropped() -> None:
    games = games_from_cfbd_payloads(
        [
            {
                "id": 9,
                "season": 2024,
                "week": 5,
                "seasonType": "regular",
                "homeTeam": "Montana",
                "awayTeam": "Idaho",
                "homePoints": 21,
                "awayPoints": 17,
            }
        ],
        [],
    )
    assert games == []
