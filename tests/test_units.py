from sbm.config import NFL_PARAMS, copy_league_params
from sbm.models.engine import ModelEngine
from sbm.schema import Game, League
from sbm.units import UnitBook, UnitWeek, cfb_unit_weeks, home_adjustment, nfl_unit_weeks


def _nfl(season: int, week: int, team: str, rush: float) -> UnitWeek:
    return UnitWeek(
        league=League.NFL,
        season=season,
        week=week,
        team=team,
        rush_off=rush,
        rush_allowed=0.0,
        pass_off=0.0,
        pass_allowed=0.0,
    )


def test_profile_uses_previous_week_then_last_season() -> None:
    book = UnitBook(
        [
            _nfl(2023, 18, "KC", 0.05),
            _nfl(2024, 1, "KC", 0.2),
            _nfl(2024, 2, "KC", 0.9),
        ]
    )
    assert book.profile_before(League.NFL, "KC", 2024, 1).rush_off == 0.05
    assert book.profile_before(League.NFL, "KC", 2024, 2).rush_off == 0.2
    assert book.profile_before(League.NFL, "KC", 2024, 3).rush_off == 0.9
    assert book.profile_before(League.NFL, "NOBODY", 2024, 3) is None


def test_adjustment_is_capped_and_skips_the_current_week() -> None:
    book = UnitBook(
        [
            _nfl(2023, 18, "AAA", 1.0),
            _nfl(2023, 18, "BBB", -1.0),
            _nfl(2024, 1, "AAA", 5.0),
            _nfl(2024, 1, "BBB", -5.0),
        ]
    )
    game = Game(
        game_id="g",
        league=League.NFL,
        season=2024,
        week=1,
        home_team="AAA",
        away_team="BBB",
    )
    params = copy_league_params(NFL_PARAMS, run_weight=8.0, pass_weight=0.0, unit_cap=4.0)
    points, label = home_adjustment(game, book, params)
    assert points == params.unit_cap
    assert label == "run EPA"
    bare = ModelEngine(League.NFL).predict(game).predicted_home_margin
    moved = ModelEngine(League.NFL, params=params, units=book).predict(game).predicted_home_margin
    assert moved == bare + params.unit_cap


def test_nfl_weeks_do_not_include_the_game_being_predicted() -> None:
    games = [
        Game(
            game_id="w1",
            league=League.NFL,
            season=2024,
            week=1,
            home_team="KC",
            away_team="BUF",
            home_score=20,
            away_score=17,
        )
    ]
    rows = [
        {
            "season": 2024,
            "week": 1,
            "team": "KC",
            "season_type": "REG",
            "rushing_epa": 8.0,
            "carries": 20,
            "passing_epa": 0.1,
        },
        {
            "season": 2024,
            "week": 1,
            "team": "BUF",
            "season_type": "REG",
            "rushing_epa": -0.2,
            "passing_epa": 0.0,
        },
    ]
    weeks = nfl_unit_weeks(rows, games)
    book = UnitBook(weeks)
    assert book.profile_before(League.NFL, "KC", 2024, 1) is None
    through = book.profile_before(League.NFL, "KC", 2024, 2)
    assert through is not None
    assert through.rush_off == 0.4  # 8 EPA on 20 carries
    assert through.rush_allowed == -0.2


def test_cfb_cumulative_and_talent_fallback() -> None:
    games = [
        {
            "season": 2024,
            "week": 1,
            "team": "Ohio State",
            "offense": {
                "plays": 10,
                "lineYards": 3.0,
                "passingPlays": {"successRate": 0.5},
            },
            "defense": {"plays": 10, "stuffRate": 0.2, "havoc": {"frontSeven": 0.1}},
        },
        {
            "season": 2024,
            "week": 2,
            "team": "Ohio State",
            "offense": {
                "plays": 10,
                "lineYards": 5.0,
                "passingPlays": {"successRate": 0.5},
            },
            "defense": {"plays": 10, "stuffRate": 0.2, "havoc": {"frontSeven": 0.1}},
        },
    ]
    talent = [{"year": 2024, "team": "Ohio State", "talent": 950}]
    book = UnitBook(cfb_unit_weeks(games, talent))
    week_two = book.profile_before(League.CFB, "Ohio State", 2024, 2)
    assert week_two is not None
    assert week_two.line_yards == 3.0
    assert week_two.talent == 950
    week_three = book.profile_before(League.CFB, "Ohio State", 2024, 3)
    assert week_three is not None
    assert week_three.line_yards == 4.0
