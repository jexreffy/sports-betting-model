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
    assert home.headers["location"] == "/journal"
    journal = client.get("/journal")
    assert journal.status_code == 200
    assert b"Journal" in journal.content
    research = client.get("/research")
    assert research.status_code == 200
    assert b"Research" in research.content
    live = client.get("/", params={"mode": "live"}, follow_redirects=False)
    assert live.status_code == 307
    api = client.get("/api/board", params={"mode": "simulation"})
    assert api.status_code == 200
    assert api.headers.get("cache-control") == "no-store"
    body = api.json()
    assert body["mode"] == "simulation"
    assert body["look_only"] is True
    assert body["cards"] == []
    live_api = client.get("/api/board", params={"mode": "live"})
    assert live_api.status_code == 400
    year = client.get("/api/journal")
    assert year.status_code == 200
    assert year.json()["summary"]["n_tickets"] == 0
    assert b"ingested" in research.content


def test_invalid_mode_is_400() -> None:
    resp = client.get("/api/board", params={"mode": "casino"})
    assert resp.status_code == 400


def test_mark_writes_gut_on_simulation_diary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
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
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pick"]["column"] == "gut"
    assert body["mode"] == "simulation"
    sys_resp = client.post(
        "/api/mark",
        json={
            "mode": "simulation",
            "game_id": board["cards"][0]["game_id"],
            "market": market["name"],
            "column": "system",
            "skipped": False,
            "side": market["model_ticket"]["side"],
        },
    )
    assert sys_resp.status_code == 200, sys_resp.text
    journal = client.get("/api/journal").json()
    assert journal["summary"]["n_tickets"] == 0
    sim_again = client.get("/api/board", params={"mode": "simulation"}).json()
    assert {row["column"] for row in sim_again["book"]} == {"gut", "system"}
    drop = client.post(
        "/api/unmark",
        json={
            "mode": "simulation",
            "game_id": board["cards"][0]["game_id"],
            "market": market["name"],
            "column": "gut",
        },
    )
    assert drop.status_code == 200, drop.text
    after_drop = client.get("/api/board", params={"mode": "simulation"}).json()
    assert {row["column"] for row in after_drop["book"]} == {"system"}


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
