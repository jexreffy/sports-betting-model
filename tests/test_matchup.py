import pytest

from sbm.config import NFL_PARAMS
from sbm.matchup import price_matchup
from sbm.schema import Game, League
from sbm.units import UnitBook, UnitWeek


def _game(**kwargs: object) -> Game:
    base: dict[str, object] = {
        "game_id": "g",
        "league": League.NFL,
        "season": 2026,
        "week": 1,
        "home_team": "KC",
        "away_team": "BUF",
    }
    base.update(kwargs)
    return Game.model_validate(base)


def test_three_sites_differ_by_home_field_and_are_not_saved() -> None:
    games = [
        _game(game_id="buf-mia", home_team="BUF", away_team="MIA"),
        _game(game_id="kc-den", home_team="KC", away_team="DEN"),
    ]
    before = [game.game_id for game in games]
    view = price_matchup(games, League.NFL, 2026, "BUF", "KC", None)
    assert [game.game_id for game in games] == before
    assert view.meetings == []
    bills_home, chiefs_home, neutral = view.sites
    assert bills_home.label.startswith("Buffalo")
    assert "at home" in chiefs_home.label
    assert neutral.label == "Neutral field"
    assert bills_home.home_margin - neutral.home_margin == pytest.approx(NFL_PARAMS.hfa_points)
    assert neutral.home_margin == pytest.approx(0.0)
    assert chiefs_home.home_margin == pytest.approx(NFL_PARAMS.hfa_points)


def test_home_and_home_prices_each_meeting_before_its_week() -> None:
    games = [
        _game(
            game_id="w1",
            week=1,
            home_team="KC",
            away_team="BUF",
            home_score=3,
            away_score=40,
        ),
        _game(game_id="w14", week=14, home_team="BUF", away_team="KC"),
        _game(game_id="old", season=2025, week=1, home_team="KC", away_team="BUF"),
    ]
    view = price_matchup(games, League.NFL, 2026, "BUF", "KC", None)
    assert [item.game.game_id for item in view.meetings] == ["w1", "w14"]
    first, second = view.meetings
    assert first.margin == pytest.approx(NFL_PARAMS.hfa_points)
    assert second.margin > NFL_PARAMS.hfa_points
    assert first.margin != second.margin
    for meeting in view.meetings:
        assert sum(row.points for row in meeting.factors) == pytest.approx(meeting.margin)


def test_unit_cap_is_its_own_factor_and_stats_come_from_prior_weeks() -> None:
    units = UnitBook(
        [
            UnitWeek(
                league=League.NFL,
                season=2025,
                week=18,
                team="BUF",
                rush_off=2.0,
                rush_allowed=0.0,
                pass_off=0.0,
                pass_allowed=0.0,
            ),
            UnitWeek(
                league=League.NFL,
                season=2025,
                week=18,
                team="KC",
                rush_off=-2.0,
                rush_allowed=0.0,
                pass_off=0.0,
                pass_allowed=0.0,
            ),
        ]
    )
    game = _game(game_id="w1", home_team="BUF", away_team="KC")
    view = price_matchup([game], League.NFL, 2026, "BUF", "KC", units)
    meeting = view.meetings[0]
    assert any(row.label == "Unit cap" for row in meeting.factors)
    assert sum(row.points for row in meeting.factors) == pytest.approx(meeting.margin)
    rush = next(row for row in view.stats if row.label == "Rush EPA")
    assert rush.left == "2.00"
    assert rush.right == "-2.00"
