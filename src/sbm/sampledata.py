"""Tiny synthetic slate used to bake README artifacts without live sports data."""

from sbm.schema import Game, League


def toy_nfl_season() -> list[Game]:
    teams = ["AAA", "BBB", "CCC", "DDD"]
    games: list[Game] = []
    gid = 0
    scores = [
        (24, 17),
        (31, 14),
        (13, 20),
        (27, 24),
        (10, 16),
        (35, 21),
        (17, 23),
        (28, 14),
        (21, 21),
        (19, 13),
        (42, 10),
        (6, 9),
    ]
    spreads = [-3, -7, 3.5, -2.5, 1, -6, 2.5, -4, 0, -3, -14, 2]
    totals = [44, 47, 41, 48, 40, 51, 43, 46, 45, 42, 52, 39]
    week = 1
    i = 0
    while i < len(scores):
        home, away = teams[i % 4], teams[(i + 1) % 4]
        hs, aws = scores[i]
        gid += 1
        games.append(
            Game(
                game_id=f"toy-{gid}",
                league=League.NFL,
                season=2024,
                week=week,
                home_team=home,
                away_team=away,
                home_score=hs,
                away_score=aws,
                spread_close=spreads[i],
                total_close=totals[i],
                home_moneyline=-150 if spreads[i] < 0 else 130,
                away_moneyline=130 if spreads[i] < 0 else -150,
            )
        )
        i += 1
        if i % 2 == 0:
            week += 1
    return games
