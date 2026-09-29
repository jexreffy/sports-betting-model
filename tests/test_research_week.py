from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sbm.schema import Game, League, Prediction
from sbm.web.app import app
from sbm.web.board import best_market_ev, research_board, research_sort_key, scope_label


def _nfl(game_id: str, kickoff: datetime | None, **extra) -> Game:
    return Game(
        game_id=game_id,
        league=League.NFL,
        season=2026,
        week=3,
        home_team="KC",
        away_team="BUF",
        kickoff=kickoff,
        **extra,
    )


def test_no_line_sorts_after_priced_games_in_the_selected_window() -> None:
    sunday = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
    next_sunday = datetime(2026, 9, 27, 17, 0, tzinfo=UTC)
    games = [
        _nfl(
            "priced",
            sunday,
            spread_close=-3.0,
            total_close=47.5,
            home_moneyline=-150,
            away_moneyline=130,
        ),
        _nfl("blank", sunday.replace(hour=20)),
        _nfl("later", next_sunday, spread_close=-6.0),
    ]
    board = research_board(
        games,
        season=2026,
        week=date(2026, 9, 15),
        today=date(2026, 9, 21),
    )
    ids = [card["game_id"] for card in board["cards"] if card["kind"] == "game"]
    assert ids == ["priced", "blank"]
    blank = next(card for card in board["cards"] if card["game_id"] == "blank")
    assert blank["value"] is None
    assert blank["markets"][0]["market"] is None


def test_heatmap_color_sorts_ahead_of_raw_value() -> None:
    cards = [
        {"kind": "game", "game_id": "yellow", "fill": "model", "value": 0.4},
        {"kind": "game", "game_id": "green", "fill": "both", "value": 0.05},
        {"kind": "game", "game_id": "orange", "fill": "you", "value": 0.9},
        {"kind": "game", "game_id": "cold", "fill": "none", "value": 0.2},
        {"kind": "game", "game_id": "blank", "fill": "none", "value": None},
    ]
    cards.sort(key=research_sort_key)
    assert [card["game_id"] for card in cards] == [
        "green",
        "yellow",
        "orange",
        "cold",
        "blank",
    ]


def test_best_market_ev_is_none_without_a_posted_line() -> None:
    game = _nfl("x", None)
    pred = Prediction(
        game_id="x",
        predicted_home_margin=3.0,
        predicted_total=45.0,
        home_win_prob=0.6,
    )
    assert best_market_ev(game, pred) is None
    priced = game.model_copy(update={"spread_close": -7.0})
    assert best_market_ev(priced, pred) is not None


def test_undated_final_does_not_move_ranks_on_an_earlier_week() -> None:
    early = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)
    later = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
    games = [
        _nfl("early", early, spread_close=-3.0),
        Game(
            game_id="later",
            league=League.NFL,
            season=2026,
            week=3,
            home_team="LV",
            away_team="DEN",
            kickoff=later,
            spread_close=-3.0,
        ),
        Game(
            game_id="undated",
            league=League.NFL,
            season=2026,
            week=2,
            home_team="KC",
            away_team="DEN",
            home_score=40,
            away_score=0,
        ),
    ]
    earlier = research_board(
        games, season=2026, week=date(2026, 9, 8), today=date(2026, 9, 16)
    )
    current = research_board(
        games, season=2026, week=date(2026, 9, 15), today=date(2026, 9, 16)
    )
    shown_earlier = {card.get("game_id") for card in earlier["cards"]}
    assert "undated" not in shown_earlier
    early_card = next(card for card in earlier["cards"] if card["game_id"] == "early")
    later_card = next(card for card in current["cards"] if card["game_id"] == "later")
    undated_card = next(card for card in current["cards"] if card["game_id"] == "undated")
    assert early_card["home_rank"] == "Model: 3"
    assert undated_card["home_rank"] is None
    assert later_card["away_rank"] == "Model: 4"


def test_current_week_errors_use_last_week_finals() -> None:
    last = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)
    now = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
    games = [
        _nfl(
            "done",
            last,
            home_score=24,
            away_score=17,
            spread_close=-3.0,
            total_close=45.0,
        ),
        _nfl("open", now, spread_close=-3.0),
    ]
    current = research_board(
        games, season=2026, week=date(2026, 9, 15), today=date(2026, 9, 21)
    )
    assert current["errors"]["title"] == "Last week"
    assert current["errors"]["n_games"] == 1
    assert current["errors"]["by_league"][0]["mae_margin_vs_close"] is not None
    assert current["errors"]["by_league"][0]["sentences"]
    assert "spread" in current["errors"]["by_league"][0]["sentences"][0]
    review = research_board(
        games, season=2026, week=date(2026, 9, 8), today=date(2026, 9, 21)
    )
    assert review["errors"]["title"] == "This slate"
    assert review["errors"]["n_games"] == 1


def test_scope_labels_use_usual_casing() -> None:
    assert scope_label("nfl") == "NFL"
    assert scope_label("cfb") == "CFB"
    assert scope_label("all") == "All"
    assert scope_label("B1G") == "B1G"
    assert scope_label("Big 12") == "Big 12"
    assert scope_label("open") == "Open"
    assert scope_label("straight") == "Straight"
    assert scope_label("moneyline") == "Moneyline"
    assert scope_label("spread") == "Spread"


def test_p4_filter_keeps_nonconference_games() -> None:
    sunday = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
    games = [
        Game(
            game_id="mich-wm",
            league=League.CFB,
            season=2026,
            week=3,
            home_team="Michigan",
            away_team="Western Michigan",
            kickoff=sunday,
            spread_close=-28.0,
        ),
        Game(
            game_id="ala-aub",
            league=League.CFB,
            season=2026,
            week=3,
            home_team="Alabama",
            away_team="Auburn",
            kickoff=sunday,
            spread_close=-7.0,
        ),
        Game(
            game_id="kc-buf",
            league=League.NFL,
            season=2026,
            week=3,
            home_team="KC",
            away_team="BUF",
            kickoff=sunday,
            spread_close=-3.0,
        ),
    ]
    board = research_board(
        games, season=2026, scope="B1G", week=date(2026, 9, 15), today=date(2026, 9, 21)
    )
    ids = [card["game_id"] for card in board["cards"] if card["kind"] == "game"]
    assert ids == ["mich-wm"]


def test_dropdown_runs_through_the_postseason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    titles = client.get("/board", params={"week": "2026-12-01", "league": "cfb"})
    assert titles.status_code == 200
    assert "Big 12 Championship" in titles.text
    assert "AT&amp;T Stadium" in titles.text
    assert "SEC Championship" in titles.text
    ten = client.get("/board", params={"week": "2026-12-01", "league": "B1G"})
    assert "Big Ten Championship" in ten.text
    assert "SEC Championship" not in ten.text
    assert "Big 12 Championship" not in ten.text
    assert "Matchup not set" in titles.text
    assert "wager-open" not in titles.text
    assert 'href="/game/' not in titles.text
    quarters = client.get("/board", params={"week": "2026-12-29", "league": "cfb"})
    assert 'datetime="2027-01-01T17:00:00+00:00"' in quarters.text
    assert 'datetime="2027-01-01T21:00:00+00:00"' in quarters.text
    assert 'datetime="2027-01-02T01:00:00+00:00"' in quarters.text
    assert "CFP Quarterfinal" in quarters.text
    assert "Fiesta Bowl" in quarters.text
    assert "Cotton" not in quarters.text
    assert "Rose" not in quarters.text
    assert "Peach" not in quarters.text
    bowl = client.get("/board", params={"week": "2027-02-09", "league": "nfl"})
    assert "Super Bowl LXI" in bowl.text
    assert "SoFi Stadium" in bowl.text
    assert "Sun Feb 14" in bowl.text
    wild = client.get("/board", params={"week": "2027-01-12", "league": "nfl"})
    assert wild.text.count('class="game-card scan-slot"') == 6
    assert "Jan 16–18" in wild.text
    body = client.get("/api/board").json()
    starts = [item["start"] for item in body["weeks"]]
    assert "2026-12-01" in starts
    assert "2027-02-09" in starts
