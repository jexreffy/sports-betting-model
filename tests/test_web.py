from fastapi.testclient import TestClient

from sbm.web.app import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_board_modes() -> None:
    sim = client.get("/", params={"mode": "simulation"})
    assert sim.status_code == 200
    assert b"Simulation" in sim.content
    live = client.get("/", params={"mode": "live"})
    assert live.status_code == 200
    assert b"LIVE" in live.content
    api = client.get("/api/board", params={"mode": "simulation"})
    assert api.status_code == 200
    body = api.json()
    assert body["mode"] == "simulation"
    assert "cards" in body
    assert "slate_label" in body
    if body["cards"]:
        card = body["cards"][0]
        assert "away_team" in card and "home_team" in card
        assert "markets" in card
    assert b"game-card" in sim.content or b"ingested" in sim.content
