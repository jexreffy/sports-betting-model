from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sbm.data.store import load_games, save_games
from sbm.journal import Journal
from sbm.schema import Game, League, Leg, Market, Side, Ticket, TicketKind
from sbm.web.app import app

client = TestClient(app)


def _game(**kwargs: object) -> Game:
    base: dict[str, object] = {
        "game_id": "nfl-2026-old",
        "league": League.NFL,
        "season": 2026,
        "week": 1,
        "home_team": "KC",
        "away_team": "DEN",
    }
    base.update(kwargs)
    return Game.model_validate(base)


def _ticket() -> Ticket:
    return Ticket(
        ticket_id="t1",
        season=2026,
        sportsbook="Novig",
        stake_dollars=5.0,
        american_odds=-110,
        kind=TicketKind.STRAIGHT,
        legs=[
            Leg(
                league=League.NFL,
                season=2026,
                week=1,
                team_or_side="KC",
                game_id="g1",
                market=Market.MONEYLINE,
                side=Side.HOME,
            )
        ],
    )


def test_board_and_journal_offer_weekly_chores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    board = client.get("/board")
    journal = client.get("/journal")
    for page in (board, journal):
        assert page.status_code == 200
        assert b"Refresh scores" in page.content
        assert b"Settle journal" in page.content
        assert b"/api/ingest" in page.content
        assert b"/api/journal/settle" in page.content


def test_refresh_scores_replaces_only_hands_off_season(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    save_games(
        League.NFL,
        [
            _game(game_id="nfl-2025", season=2025, home_score=1, away_score=0),
            _game(game_id="nfl-2026-old", home_score=None, away_score=None),
        ],
    )
    save_games(
        League.CFB,
        [
            _game(
                game_id="cfb-2025",
                league=League.CFB,
                season=2025,
                home_team="Florida",
                away_team="Missouri",
            )
        ],
    )
    fresh = _game(game_id="nfl-2026-new", home_score=24, away_score=17)

    monkeypatch.setattr("sbm.data.nfl.download_nfl_games", lambda seasons: [fresh])
    monkeypatch.setattr("sbm.data.nfl.download_nfl_team_stats", lambda seasons: [])
    monkeypatch.setattr("sbm.data.cfb.download_cfb_games", lambda seasons: [])
    monkeypatch.setattr("sbm.data.cfb.download_cfb_advanced", lambda seasons: [])
    monkeypatch.setattr("sbm.data.cfb.download_cfb_talent", lambda seasons: [])

    resp = client.post("/api/ingest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["season"] == 2026
    assert body["nfl_games"] == 1
    assert body["cfb_games"] == 0

    nfl = load_games(League.NFL)
    assert {g.game_id for g in nfl} == {"nfl-2025", "nfl-2026-new"}
    assert load_games(League.CFB)[0].game_id == "cfb-2025"
    assert Journal().load() == []


def test_refresh_scores_reports_a_download_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    save_games(League.NFL, [_game(game_id="nfl-2026-keep", home_score=3, away_score=0)])

    def _boom(seasons: list[int]) -> list[Game]:
        raise RuntimeError("CFBD_API_KEY is required to ingest college football.")

    monkeypatch.setattr(
        "sbm.data.nfl.download_nfl_games",
        lambda seasons: [_game(game_id="nfl-2026-new", home_score=9, away_score=0)],
    )
    monkeypatch.setattr("sbm.data.nfl.download_nfl_team_stats", lambda seasons: [])
    monkeypatch.setattr("sbm.data.cfb.download_cfb_games", _boom)

    resp = client.post("/api/ingest")
    assert resp.status_code == 400
    assert "CFBD_API_KEY" in resp.json()["detail"]
    assert [game.game_id for game in load_games(League.NFL)] == ["nfl-2026-keep"]


def test_settle_journal_grades_finals_and_leaves_the_rest_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    final = _game(game_id="g1", home_score=27, away_score=20)
    save_games(League.NFL, [final])
    book = Journal()
    book.add(_ticket())
    book.add(
        _ticket().model_copy(
            update={
                "ticket_id": "still-open",
                "legs": [
                    _ticket().legs[0].model_copy(update={"game_id": "not-final"}),
                ],
            }
        )
    )

    resp = client.post("/api/journal/settle")
    assert resp.status_code == 200
    assert resp.json()["settled"] == 1
    graded = {row.ticket_id: row.result for row in Journal().load()}
    assert graded == {"t1": "win", "still-open": None}
