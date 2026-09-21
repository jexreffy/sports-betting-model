from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sbm.records import standings
from sbm.schema import Game, League
from sbm.web.app import app


def _cfb(game_id: str, home: str, away: str, home_score: int, away_score: int) -> Game:
    return Game(
        game_id=game_id,
        league=League.CFB,
        season=2026,
        week=1,
        home_team=home,
        away_team=away,
        home_conference="B1G",
        away_conference="B1G",
        home_score=home_score,
        away_score=away_score,
    )


def test_head_to_head_splits_a_tied_group() -> None:
    games = [
        _cfb("iowa-osu", "Ohio State", "Iowa", 0, 35),
        _cfb("osu-mich", "Michigan", "Ohio State", 0, 10),
        _cfb("mich-psu", "Penn State", "Michigan", 0, 40),
    ]
    order = [row.team for row in standings(games, 2026, "B1G")]
    assert order == ["Iowa", "Ohio State", "Michigan", "Penn State"]


def _nfl(
    game_id: str, home: str, away: str, home_score: int | None, away_score: int | None
) -> Game:
    return Game(
        game_id=game_id,
        league=League.NFL,
        season=2026,
        week=1,
        home_team=home,
        away_team=away,
        home_score=home_score,
        away_score=away_score,
    )


def test_tie_counts_as_half_a_win_and_unplayed_teams_sit_last() -> None:
    games = [
        _nfl("tie", "DAL", "BUF", 10, 10),
        _nfl("buf-kc", "KC", "BUF", 0, 17),
        _nfl("chi-gb", "GB", "CHI", 0, 21),
        _nfl("chi-den", "DEN", "CHI", 7, 14),
        _nfl("kc-chi", "CHI", "KC", 0, 24),
        _nfl("open", "NYJ", "LAC", None, None),
    ]
    rows = standings(games, 2026, "nfl")
    by_team = {row.team: row for row in rows}
    order = [row.team for row in rows]
    assert by_team["BUF"].wins == 1 and by_team["BUF"].ties == 1
    assert by_team["BUF"].conf_wins == 1 and by_team["BUF"].conf_ties == 0
    assert by_team["DAL"].ties == 1 and by_team["DAL"].conf_ties == 0
    assert order.index("BUF") < order.index("CHI")
    assert rows[-2].played == 0 and rows[-1].played == 0
    assert {rows[-2].team, rows[-1].team} == {"LAC", "NYJ"}


def test_records_page_uses_finals_and_is_not_draggable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games

    save_games(League.CFB, [_cfb("osu-mich", "Michigan", "Ohio State", 0, 10)])
    page = TestClient(app).get("/records", params={"group": "B1G"})
    assert page.status_code == 200
    html = page.text
    assert "results on hand" in html
    assert "rank-grip" not in html
    assert "Ohio State" in html
    assert html.find("Ohio State") < html.find("Up North")
