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
    assert b"ingested" in sim.content


def test_invalid_mode_is_400() -> None:
    resp = client.get("/", params={"mode": "casino"})
    assert resp.status_code == 400
