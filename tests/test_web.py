from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sbm.web.app import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_board_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    home = client.get("/", follow_redirects=False)
    assert home.status_code == 307
    assert home.headers["location"] == "/research"
    journal = client.get("/journal")
    assert journal.status_code == 200
    assert b"Journal" in journal.content
    assert b"journal-search" in journal.content
    research = client.get("/research")
    assert research.status_code == 200
    assert b"Research" in research.content
    assert b"Ratings" in research.content
    assert b"Rankings" in research.content
    assert b"ticket-modal" in research.content
    live = client.get("/", params={"mode": "live"}, follow_redirects=False)
    assert live.status_code == 307
    api = client.get("/api/board", params={"mode": "simulation"})
    assert api.status_code == 200
    assert api.headers.get("cache-control") == "no-store"
    body = api.json()
    assert body["mode"] == "simulation"
    assert "look_only" not in body
    assert "book" not in body
    assert "curve" not in body
    assert body["cards"] == []
    live_api = client.get("/api/board", params={"mode": "live"})
    assert live_api.status_code == 400
    year = client.get("/api/journal")
    assert year.status_code == 200
    assert year.json()["summary"]["n_tickets"] == 0
    assert b"ingested" in research.content
    pred = client.get("/predictions")
    assert pred.status_code == 200
    assert b"Predictions" in pred.content
    assert b"team-search" in pred.content


def test_invalid_mode_is_400() -> None:
    resp = client.get("/api/board", params={"mode": "casino"})
    assert resp.status_code == 400


def test_mark_is_gone_and_does_not_write_paper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.paths import ledger_path
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="g1",
                league=League.NFL,
                season=2026,
                week=1,
                home_team="KC",
                away_team="BUF",
                spread_close=-28.0,
                total_close=60.0,
                home_moneyline=-800,
                away_moneyline=600,
            )
        ],
    )
    board = client.get("/api/board", params={"mode": "simulation"}).json()
    assert board["cards"]
    market = next(m for m in board["cards"][0]["markets"] if m["model_ticket"])
    resp = client.post(
        "/api/mark",
        json={
            "mode": "simulation",
            "game_id": board["cards"][0]["game_id"],
            "market": market["name"],
            "column": "gut",
            "skipped": False,
            "side": "away",
        },
    )
    assert resp.status_code == 410
    unmark = client.post(
        "/api/unmark",
        json={
            "mode": "simulation",
            "game_id": board["cards"][0]["game_id"],
            "market": market["name"],
            "column": "gut",
        },
    )
    assert unmark.status_code == 410
    from sbm.mode import Mode

    assert not ledger_path(Mode.SIMULATION).exists()
    page = client.get("/research")
    assert b"wager-open" in page.content
    journal = client.post(
        "/api/journal/tickets",
        json={
            "sportsbook": "Novig",
            "stake_dollars": 5,
            "american_odds": -110,
            "kind": "straight",
            "legs": [
                {
                    "league": "nfl",
                    "season": 2026,
                    "week": 1,
                    "team_or_side": "BUF",
                    "opponent": "KC",
                    "market": market["name"],
                    "side": "away",
                    "game_id": board["cards"][0]["game_id"],
                }
            ],
        },
    )
    assert journal.status_code == 200, journal.text
    assert client.get("/api/journal").json()["summary"]["n_tickets"] == 1
    assert not ledger_path(Mode.SIMULATION).exists()


def test_journal_add_and_year(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    resp = client.post(
        "/api/journal/tickets",
        json={
            "sportsbook": "Novig",
            "stake_dollars": 5,
            "implied_prob": 0.47,
            "kind": "straight",
            "legs": [
                {
                    "league": "nfl",
                    "season": 2026,
                    "week": 2,
                    "team_or_side": "JAX",
                    "opponent": "DEN",
                    "market": "moneyline",
                    "side": "away",
                    "game_id": "den-jax",
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sportsbook"] == "Novig"
    assert body["legs"][0]["team_or_side"] == "JAX"
    year = client.get("/api/journal").json()
    assert year["summary"]["n_tickets"] == 1
    assert year["tickets"][0]["status"] == "open"
    page = client.get("/journal")
    assert page.status_code == 200
    assert b"JAX" in page.content
    assert b"filter-status" in page.content
    assert b"filter-league" in page.content
    assert b"filter-week" in page.content


def test_predictions_api_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="2026_04_BUF_KC",
                league=League.NFL,
                season=2026,
                week=4,
                home_team="KC",
                away_team="BUF",
            )
        ],
    )
    listed = client.get("/api/predictions").json()
    teams = {t["team"] for t in listed["teams"]}
    assert "BUF" in teams
    assert "KC" in teams
    set_resp = client.post(
        "/api/predictions/set",
        json={
            "season": 2026,
            "game_id": "2026_04_BUF_KC",
            "predicted_winner": "BUF",
        },
    )
    assert set_resp.status_code == 200, set_resp.text
    buf = next(t for t in client.get("/api/predictions").json()["teams"] if t["team"] == "BUF")
    pick = next(g for g in buf["games"] if g["game_id"] == "2026_04_BUF_KC")
    assert pick["predicted_winner"] == "BUF"


def test_predictions_page_kickoff_and_away_home_buttons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from datetime import UTC, datetime

    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="2026_04_BUF_KC",
                league=League.NFL,
                season=2026,
                week=4,
                home_team="KC",
                away_team="BUF",
                kickoff=datetime(2026, 9, 27, 13, 0, tzinfo=UTC),
            )
        ],
    )
    page = client.get("/predictions")
    assert page.status_code == 200
    html = page.text
    assert "Sun 12:00 PM CDT" in html
    assert "Buffalo Bills" in html
    assert "bills" in html.lower()
    assert "team-search" in html
    assert "Kansas City Chiefs" in html
    assert "w4 Sun 12:00 PM CDT" in html
    assert "Bye w1" in html
    assert "BUF @ KC" not in html
    buf_btn = html.find('data-choice="away" data-winner="BUF"')
    kc_btn = html.find('data-choice="home" data-winner="KC"')
    assert 0 <= buf_btn < kc_btn
    buf_btn_2 = html.find('data-choice="away" data-winner="BUF"', buf_btn + 1)
    kc_btn_2 = html.find('data-choice="home" data-winner="KC"', kc_btn + 1)
    assert 0 <= buf_btn_2 < kc_btn_2
    assert "intl-chip" not in html
    assert "KC -2.4" in html
    assert 'data-choice="cover"' in html
    cover_at = html.find('data-choice="cover"')
    assert 0 <= buf_btn < cover_at < kc_btn
    set_cover = client.post(
        "/api/predictions/set",
        json={"season": 2026, "game_id": "2026_04_BUF_KC", "choice": "cover"},
    )
    assert set_cover.status_code == 200, set_cover.text
    kc = next(t for t in client.get("/api/predictions").json()["teams"] if t["team"] == "KC")
    pick = next(g for g in kc["games"] if g["game_id"] == "2026_04_BUF_KC")
    assert pick["pick_kind"] == "cover"
    assert pick["predicted_winner"] == "KC"
    assert pick["cover_favorite"] == "KC"


def test_ratings_and_rankings_pages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="2026_04_BUF_KC",
                league=League.NFL,
                season=2026,
                week=4,
                home_team="KC",
                away_team="BUF",
            )
        ],
    )
    ratings = client.get("/ratings")
    assert ratings.status_code == 200
    assert "Buffalo Bills" in ratings.text
    assert "NFF" in ratings.text
    assert ">all<" not in ratings.text
    assert "NFL" in ratings.text
    rankings = client.get("/rankings")
    assert ">all<" not in rankings.text
    assert "2026 NFL" in rankings.text
    assert rankings.status_code == 200
    assert "This list follows the model" in rankings.text
    moved = client.post(
        "/api/rankings/move",
        json={"season": 2026, "group": "nfl", "team": "KC", "direction": "up"},
    )
    assert moved.status_code == 200, moved.text
    again = client.get("/rankings?group=nfl")
    assert "follows the model" not in again.text
    research = client.get("/research")
    assert "You:" in research.text
    assert "Model " in research.text
    ranking_html = client.get("/rankings").text
    assert "rank-grip" in ranking_html
    assert 'aria-label="Move Buffalo Bills up"' in ranking_html
    assert 'aria-label="Move Buffalo Bills down"' in ranking_html
    assert ">Up<" not in ranking_html
    placed = client.post(
        "/api/rankings/place",
        json={"season": 2026, "group": "nfl", "team": "BUF", "index": 0},
    )
    assert placed.status_code == 200, placed.text
    assert placed.json()["groups"]["nfl"][0] == "BUF"


def test_predictions_marks_international_games(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="2026_03_DAL_BAL",
                league=League.NFL,
                season=2026,
                week=3,
                home_team="BAL",
                away_team="DAL",
                venue="Tottenham Hotspur Stadium",
            )
        ],
    )
    page = client.get("/predictions")
    assert page.status_code == 200
    html = page.text
    assert "intl-chip" in html
    assert "INTL" in html
    assert "Tottenham Hotspur Stadium" in html


def test_predictions_page_cfb_banner_and_abbrevs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.CFB,
        [
            Game(
                game_id="cfb-1",
                league=League.CFB,
                season=2026,
                week=6,
                home_team="Ohio State",
                away_team="Michigan",
                home_conference="B1G",
                away_conference="B1G",
            )
        ],
    )
    page = client.get("/predictions?conference=B1G")
    assert page.status_code == 200
    html = page.text
    assert "The Team Up North" in html
    assert "Ohio State Buckeyes" in html
    assert "--team-color: #00274C" in html
    assert ">TTUN<" in html
    assert "OSU -2.7" in html
    assert "data-winner=\"Michigan\"" in html
    assert "Michigan Wolverines" not in html
    assert ">MICH<" not in html
    assert "❌" in html
    assert "Michigan @ Ohio State" not in html
