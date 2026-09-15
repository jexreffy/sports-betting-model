from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sbm.web.app import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_board_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    sim = client.get("/", params={"mode": "simulation"})
    assert sim.status_code == 200
    assert b"Simulation" in sim.content
    live = client.get("/", params={"mode": "live"})
    assert live.status_code == 200
    assert b"LIVE" in live.content
    api = client.get("/api/board", params={"mode": "simulation"})
    assert api.status_code == 200
    assert api.headers.get("cache-control") == "no-store"
    body = api.json()
    assert body["mode"] == "simulation"
    assert body["cards"] == []
    assert "system" in body["summary"]
    assert "gut" in body["summary"]
    assert body["book"] == []
    assert b"ingested" in sim.content


def test_invalid_mode_is_400() -> None:
    resp = client.get("/", params={"mode": "casino"})
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
    live = client.get("/api/board", params={"mode": "live"}).json()
    assert live["summary"]["gut"]["n_picks"] == 0
    assert live["book"] == []
    sim_again = client.get("/api/board", params={"mode": "simulation"}).json()
    assert {row["column"] for row in sim_again["book"]} == {"gut", "system"}
    assert {row["game_id"] for row in sim_again["book"]} == {board["cards"][0]["game_id"]}
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


def test_live_gut_moneyline_without_system_pick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="den-jax",
                league=League.NFL,
                season=2026,
                week=2,
                home_team="DEN",
                away_team="JAX",
                spread_close=-1.0,
                total_close=44.5,
                home_moneyline=-140,
                away_moneyline=120,
            )
        ],
    )
    board = client.get("/api/board", params={"mode": "live"}).json()
    ml = next(m for m in board["cards"][0]["markets"] if m["name"] == "moneyline")
    assert ml["open_for_marks"] is True
    assert ml["model_ticket"] is None
    resp = client.post(
        "/api/mark",
        json={
            "mode": "live",
            "game_id": "den-jax",
            "market": "moneyline",
            "column": "gut",
            "skipped": False,
            "side": "away",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["pick"]["team_or_side"] == "JAX"
    live = client.get("/api/board", params={"mode": "live"}).json()
    ml = next(m for m in live["cards"][0]["markets"] if m["name"] == "moneyline")
    assert ml["gut"]["team_or_side"] == "JAX"
    assert live["book"][0]["column"] == "gut"
    assert live["book"][0]["label"] == "Gut · NFL w2 JAX@DEN JAX moneyline"
    cfb_view = client.get("/api/board", params={"mode": "live", "league": "cfb"}).json()
    assert cfb_view["book"][0]["label"] == "Gut · NFL w2 JAX@DEN JAX moneyline"
    blocked = client.post(
        "/api/mark",
        json={
            "mode": "live",
            "game_id": "den-jax",
            "market": "moneyline",
            "column": "system",
            "skipped": False,
            "side": "away",
        },
    )
    assert blocked.status_code == 400

