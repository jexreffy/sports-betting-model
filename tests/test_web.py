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
    assert b"week-select" in research.content
    assert b"ticket-modal" not in research.content
    assert b"Model tickets" not in research.content
    live = client.get("/", params={"mode": "live"}, follow_redirects=False)
    assert live.status_code == 307
    api = client.get("/api/board", params={"mode": "simulation", "week": "2026-12-01"})
    assert api.status_code == 200
    assert api.headers.get("cache-control") == "no-store"
    body = api.json()
    assert body["mode"] == "simulation"
    assert "look_only" not in body
    assert "book" not in body
    assert "curve" not in body
    assert body["cards"]
    assert all(card["kind"] == "slot" for card in body["cards"])
    live_api = client.get("/api/board", params={"mode": "live"})
    assert live_api.status_code == 400
    year = client.get("/api/journal")
    assert year.status_code == 200
    assert year.json()["summary"]["n_tickets"] == 0
    quiet = client.get("/research", params={"week": "2026-12-08"})
    assert b"ingested" in quiet.content
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
    game_card = next(card for card in board["cards"] if card.get("kind") == "game")
    market = next(m for m in game_card["markets"] if m["model_ticket"])
    resp = client.post(
        "/api/mark",
        json={
            "mode": "simulation",
            "game_id": game_card["game_id"],
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
            "game_id": game_card["game_id"],
            "market": market["name"],
            "column": "gut",
        },
    )
    assert unmark.status_code == 410
    from sbm.mode import Mode

    assert not ledger_path(Mode.SIMULATION).exists()
    page = client.get("/research")
    assert b"wager-open" not in page.content
    assert b"scan-card" in page.content
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
                    "game_id": game_card["game_id"],
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
    assert 'datetime="2026-09-27T17:00:00+00:00"' in html
    assert "local-time.js" in html
    assert "CDT" not in html
    assert "Buffalo Bills" in html
    assert "bills" in html.lower()
    assert "team-search" in html
    assert "Kansas City Chiefs" in html
    assert "w4 " in html
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
    assert "<em>Model</em>" in research.text
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


def test_game_page_is_empty_until_a_matchup_is_pulled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    page = client.get("/game")
    assert page.status_code == 200
    assert b"does not list the slate" in page.content
    assert b"This week" not in page.content
    assert b"wager-open" not in page.content
    assert client.get("/game/missing").status_code == 404


def test_game_page_hypothetical_has_three_prices_and_no_log_buttons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.schema import Game, League

    save_games(
        League.NFL,
        [
            Game(
                game_id="buf-mia",
                league=League.NFL,
                season=2026,
                week=1,
                home_team="BUF",
                away_team="MIA",
            ),
            Game(
                game_id="kc-den",
                league=League.NFL,
                season=2026,
                week=1,
                home_team="KC",
                away_team="DEN",
            ),
        ],
    )
    page = client.get("/game", params={"league": "nfl", "team_a": "Bills", "team_b": "Chiefs"})
    assert page.status_code == 200
    html = page.text
    assert "Buffalo Bills at home" in html
    assert "Kansas City Chiefs at home" in html
    assert "Neutral field" in html
    assert "Rush EPA" in html
    assert "teamlogos/nfl/500/buf.png" in html
    assert "teamlogos/nfl/500/kc.png" in html
    assert "--team-color: #00338D" in html
    assert "--team-color: #E31837" in html
    assert "is-neutral" in html
    assert "wager-open" not in html
    assert "No meeting between these teams" in html


def test_game_page_shows_each_same_season_meeting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.journal import Journal
    from sbm.schema import Game, League, Leg, Market, Side, Ticket, TicketKind

    save_games(
        League.NFL,
        [
            Game(
                game_id="w1",
                league=League.NFL,
                season=2026,
                week=1,
                home_team="KC",
                away_team="BUF",
                home_score=3,
                away_score=40,
                spread_close=-3.0,
                total_close=47.5,
                home_moneyline=-150,
                away_moneyline=130,
                venue="Arrowhead Stadium",
                home_rest_days=7,
                away_rest_days=7,
            ),
            Game(
                game_id="w14",
                league=League.NFL,
                season=2026,
                week=14,
                home_team="BUF",
                away_team="KC",
                spread_close=-2.5,
                total_close=48.0,
                home_moneyline=-140,
                away_moneyline=120,
                venue="Tottenham Hotspur Stadium",
                home_rest_days=10,
                away_rest_days=6,
            ),
            Game(
                game_id="old",
                league=League.NFL,
                season=2025,
                week=1,
                home_team="KC",
                away_team="BUF",
                spread_close=-3.0,
                total_close=44.0,
                home_moneyline=-150,
                away_moneyline=130,
            ),
        ],
    )
    Journal().add(
        Ticket(
            ticket_id="t-w1",
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
                    team_or_side="BUF",
                    opponent="KC",
                    market=Market.MONEYLINE,
                    side=Side.AWAY,
                    game_id="w1",
                )
            ],
        )
    )
    page = client.get("/game/w1")
    assert page.status_code == 200
    html = page.text
    assert 'id="game-w1"' in html
    assert 'id="game-w14"' in html
    assert "game-old" not in html
    assert 'data-game="w1"' in html
    assert 'data-game="w14"' in html
    assert html.count("wager-open") >= 2
    assert "Arrowhead Stadium" in html
    assert "Tottenham Hotspur Stadium" in html
    assert "Home field" in html
    assert "International" in html
    assert 'class="real-game game-card' in html
    assert "is-opened" in html
    research = client.get("/research")
    assert "/game/w14#game-w14" in research.text
    predictions = client.get("/predictions")
    assert "/game/w1#game-w1" in predictions.text
    assert "/game/w14#game-w14" in predictions.text
    assert "pick-winner" in predictions.text
    journal = client.get("/journal")
    assert "/game/w1#game-w1" in journal.text


def test_journal_links_a_leg_that_has_no_stored_game_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.journal import Journal
    from sbm.schema import Game, League, Leg, Market, Ticket, TicketKind

    save_games(
        League.NFL,
        [
            Game(
                game_id="2026_01_HOU_BUF",
                league=League.NFL,
                season=2026,
                week=1,
                home_team="BUF",
                away_team="HOU",
            )
        ],
    )
    save_games(
        League.CFB,
        [
            Game(
                game_id="cfb-ou-mich",
                league=League.CFB,
                season=2026,
                week=1,
                home_team="Michigan",
                away_team="Oklahoma",
            )
        ],
    )
    Journal().add(
        Ticket(
            ticket_id="t-hou",
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
                    team_or_side="HOU",
                    opponent="BUF",
                    market=Market.SPREAD,
                    market_line=1.5,
                )
            ],
        )
    )
    Journal().add(
        Ticket(
            ticket_id="t-ou",
            season=2026,
            sportsbook="Novig",
            stake_dollars=5.0,
            american_odds=-110,
            kind=TicketKind.STRAIGHT,
            legs=[
                Leg(
                    league=League.CFB,
                    season=2026,
                    week=1,
                    team_or_side="OU",
                    opponent="MICH",
                    market=Market.SPREAD,
                    market_line=-4.5,
                )
            ],
        )
    )
    page = client.get("/journal")
    assert page.status_code == 200
    assert "/game/2026_01_HOU_BUF#game-2026_01_HOU_BUF" in page.text
    assert "/game/cfb-ou-mich#game-cfb-ou-mich" in page.text


def test_journal_week_dropdown_uses_tuesday_monday_dates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime

    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.data.store import save_games
    from sbm.journal import Journal
    from sbm.schema import Game, League, Leg, Market, Ticket, TicketKind

    save_games(
        League.NFL,
        [
            Game(
                game_id="2026_02_DET_BUF",
                league=League.NFL,
                season=2026,
                week=2,
                home_team="BUF",
                away_team="DET",
                kickoff=datetime(2026, 9, 17, 19, 15, tzinfo=UTC),
            )
        ],
    )
    Journal().add(
        Ticket(
            ticket_id="t-buf",
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
                    team_or_side="BUF",
                    opponent="DET",
                    market=Market.MONEYLINE,
                )
            ],
        )
    )
    page = client.get("/journal")
    assert page.status_code == 200
    html = page.text
    assert '<select id="filter-week">' in html
    assert "Tue Sep 15 – Mon Sep 21" in html
    assert 'value="2026-09-15"' in html
    assert "teamlogos/nfl/500/buf.png" in html
    assert "--team-color: #00338D" in html
