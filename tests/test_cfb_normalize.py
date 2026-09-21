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
            "homeConference": "Big Ten",
            "awayConference": "Big Ten",
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
    assert game.home_conference == "B1G"
    assert game.away_conference == "B1G"


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


def test_fbs_vs_fcs_week_zero_is_kept() -> None:
    games = games_from_cfbd_payloads(
        [
            {
                "id": 3,
                "season": 2026,
                "week": 0,
                "seasonType": "regular",
                "homeTeam": "Alabama",
                "awayTeam": "Montana",
                "homePoints": 52,
                "awayPoints": 7,
                "homeClassification": "fbs",
                "awayClassification": "fcs",
            }
        ],
        [],
    )
    assert len(games) == 1
    assert games[0].week == 0
    assert games[0].away_team == "Montana"


def test_two_week_one_games_in_different_windows_split() -> None:
    games = games_from_cfbd_payloads(
        [
            {
                "id": 10,
                "season": 2026,
                "week": 1,
                "seasonType": "regular",
                "homeTeam": "USC",
                "awayTeam": "San José State",
                "startDate": "2026-08-29T19:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
            {
                "id": 11,
                "season": 2026,
                "week": 1,
                "seasonType": "regular",
                "homeTeam": "USC",
                "awayTeam": "Fresno State",
                "startDate": "2026-09-05T01:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
            {
                "id": 12,
                "season": 2026,
                "week": 1,
                "seasonType": "regular",
                "homeTeam": "Alabama",
                "awayTeam": "Georgia",
                "startDate": "2026-09-05T23:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
        ],
        [],
    )
    by_id = {game.game_id: game.week for game in games}
    assert by_id["cfb-10"] == 0
    assert by_id["cfb-11"] == 1
    assert by_id["cfb-12"] == 1


def test_same_window_doubleheader_stays_week_one() -> None:
    games = games_from_cfbd_payloads(
        [
            {
                "id": 20,
                "season": 2026,
                "week": 1,
                "seasonType": "regular",
                "homeTeam": "USC",
                "awayTeam": "Georgia",
                "startDate": "2026-09-03T23:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
            {
                "id": 21,
                "season": 2026,
                "week": 1,
                "seasonType": "regular",
                "homeTeam": "USC",
                "awayTeam": "Oregon",
                "startDate": "2026-09-06T00:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
        ],
        [],
    )
    assert {game.week for game in games} == {1}


def test_playoff_week_one_is_not_renumbered() -> None:
    games = games_from_cfbd_payloads(
        [
            {
                "id": 30,
                "season": 2026,
                "week": 1,
                "seasonType": "regular",
                "homeTeam": "USC",
                "awayTeam": "Georgia",
                "startDate": "2026-09-05T23:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
            {
                "id": 31,
                "season": 2026,
                "week": 1,
                "seasonType": "postseason",
                "homeTeam": "USC",
                "awayTeam": "Ohio State",
                "startDate": "2027-01-01T01:00:00Z",
                "homeClassification": "fbs",
                "awayClassification": "fbs",
            },
        ],
        [],
    )
    assert {game.week for game in games} == {1}
