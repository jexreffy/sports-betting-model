from datetime import UTC, datetime
from pathlib import Path

import pytest

from sbm.config import RESEARCH_WINDOWS
from sbm.predictions import (
    apply_called_misses,
    apply_ranks,
    bye_weeks,
    fill_unpicked_finals,
    format_kickoff_cdt,
    init_book,
    set_winner,
    sync_actuals,
)
from sbm.schema import Game, League, SeasonGameTake, SeasonPredictions, TeamSeasonTake


def _nfl(game_id: str, week: int, away: str, home: str, **kwargs: object) -> Game:
    return Game(
        game_id=game_id,
        league=League.NFL,
        season=RESEARCH_WINDOWS.hands_off,
        week=week,
        home_team=home,
        away_team=away,
        home_conference="AFC" if home in {"KC", "BUF", "BAL"} else "NFC",
        away_conference="AFC" if away in {"KC", "BUF", "BAL"} else "NFC",
        **kwargs,  # type: ignore[arg-type]
    )


def _cfb(
    game_id: str,
    week: int,
    away: str,
    home: str,
    away_conf: str,
    home_conf: str,
    **kwargs: object,
) -> Game:
    return Game(
        game_id=game_id,
        league=League.CFB,
        season=RESEARCH_WINDOWS.hands_off,
        week=week,
        home_team=home,
        away_team=away,
        home_conference=home_conf,
        away_conference=away_conf,
        **kwargs,  # type: ignore[arg-type]
    )


def test_rank_fill_skips_non_conference_and_existing_picks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    games = [
        _nfl("nfl-1", 4, "BUF", "KC"),
        _nfl("nfl-2", 5, "DAL", "PHI"),
        _cfb("cfb-1", 6, "Ohio State", "Michigan", "B1G", "B1G"),
        _cfb("cfb-2", 6, "Alabama", "Michigan", "SEC", "B1G"),
        _cfb("cfb-3", 6, "Western Kentucky", "Michigan", "CUSA", "B1G"),
    ]
    book = init_book(games, RESEARCH_WINDOWS.hands_off)
    assert any(t.team == "Michigan" for t in book.teams)
    book = set_winner(book, "nfl-1", "BUF")
    updated, filled, leftovers = apply_ranks(
        book,
        {
            "nfl": ["KC", "PHI", "BUF", "DAL"],
            "B1G": ["Ohio State", "Michigan"],
            "SEC": ["Alabama"],
        },
        games,
    )
    by_game = {}
    for team in updated.teams:
        for row in team.games:
            if row.predicted_winner:
                by_game[row.game_id] = row.predicted_winner
    assert by_game["nfl-1"] == "BUF"
    assert by_game["nfl-2"] == "PHI"
    assert by_game["cfb-1"] == "Ohio State"
    assert "cfb-2" not in by_game
    assert "cfb-3" not in by_game
    leftover_ids = {row["game_id"] for row in leftovers}
    assert "cfb-2" in leftover_ids
    assert "cfb-3" in leftover_ids
    assert filled == 2


def test_sync_does_not_overwrite_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    open_game = _nfl("nfl-1", 4, "BUF", "KC")
    book = init_book([open_game], RESEARCH_WINDOWS.hands_off)
    book = set_winner(book, "nfl-1", "BUF")
    final = open_game.model_copy(update={"home_score": 24, "away_score": 17})
    synced = sync_actuals(book, [final])
    row = next(g for t in synced.teams if t.team == "BUF" for g in t.games)
    assert row.predicted_winner == "BUF"
    assert row.actual_winner == "KC"


def test_heatmap_reconsider_when_behind_take(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    games = [
        _nfl("w1", 1, "BUF", "KC", home_score=30, away_score=10),
        _nfl("w2", 2, "BUF", "MIA", home_score=21, away_score=7),
        _nfl("w3", 3, "NE", "BUF", home_score=27, away_score=13),
        _nfl("w4", 4, "BUF", "NYJ"),
    ]
    book = init_book(games, RESEARCH_WINDOWS.hands_off)
    for gid in ("w1", "w2", "w3", "w4"):
        book = set_winner(book, gid, "BUF")
    buf = next(t for t in book.teams if t.team == "BUF")
    assert buf.reconsider is True
    assert buf.predicted_wins_played == 3
    remaining = next(g for g in buf.games if g.game_id == "w4")
    assert remaining.predicted_winner == "BUF"


def test_notre_dame_is_rostered_with_acc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    games = [
        _cfb(
            "nd-1",
            10,
            "Miami",
            "Notre Dame",
            "ACC",
            "FBS Independents",
        )
    ]
    book = init_book(games, RESEARCH_WINDOWS.hands_off)
    nd = next(t for t in book.teams if t.team == "Notre Dame")
    assert nd.conference == "ACC"
    miami = next(t for t in book.teams if t.team == "Miami")
    assert miami.conference == "ACC"
    leftover = next(g for g in nd.games if g.game_id == "nd-1")
    assert leftover.leftover is False


def test_format_kickoff_cdt_uses_chicago() -> None:
    nfl_1pm_et = datetime(2026, 9, 13, 13, 0, tzinfo=UTC)
    assert format_kickoff_cdt(nfl_1pm_et, League.NFL) == "Sun 12:00 PM CDT"
    cfb_utc = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)
    assert format_kickoff_cdt(cfb_utc, League.CFB) == "Sun 12:00 PM CDT"
    winter = datetime(2026, 12, 20, 13, 0, tzinfo=UTC)
    assert format_kickoff_cdt(winter, League.NFL) == "Sun 12:00 PM CST"
    naive = datetime(2026, 9, 13, 13, 0)
    assert format_kickoff_cdt(naive, League.NFL) == "Sun 12:00 PM CDT"
    assert format_kickoff_cdt(None) is None


def test_init_book_copies_kickoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    kick = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)
    book = init_book([_nfl("nfl-1", 4, "BUF", "KC", kickoff=kick)], RESEARCH_WINDOWS.hands_off)
    row = next(g for t in book.teams if t.team == "BUF" for g in t.games)
    assert row.kickoff == kick


def test_bye_weeks_nfl_and_cfb_gaps() -> None:
    nfl_rows = init_book(
        [_nfl("a", 1, "BUF", "KC"), _nfl("b", 3, "BUF", "MIA")],
        RESEARCH_WINDOWS.hands_off,
    )
    buf = next(t for t in nfl_rows.teams if t.team == "BUF")
    assert 2 in bye_weeks(buf.games, League.NFL)
    assert 1 not in bye_weeks(buf.games, League.NFL)
    cfb_rows = init_book(
        [
            _cfb("c1", 1, "Ohio State", "Michigan", "B1G", "B1G"),
            _cfb("c2", 3, "Ohio State", "Penn State", "B1G", "B1G"),
        ],
        RESEARCH_WINDOWS.hands_off,
    )
    osu = next(t for t in cfb_rows.teams if t.team == "Ohio State")
    assert bye_weeks(osu.games, League.CFB) == [2]


def test_fill_unpicked_finals_hits_except_called_wrongs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    games = [
        _cfb(
            "osu-tex",
            2,
            "Ohio State",
            "Texas",
            "B1G",
            "Big 12",
            home_score=14,
            away_score=7,
        ),
        _cfb(
            "wmu-mich",
            1,
            "Western Michigan",
            "Michigan",
            "MAC",
            "B1G",
            home_score=24,
            away_score=10,
        ),
    ]
    book = init_book(games, RESEARCH_WINDOWS.hands_off)
    book = sync_actuals(book, games)
    updated, filled, misses = fill_unpicked_finals(
        book,
        "B1G",
        [("OSU", "TEX")],
    )
    assert filled == 2
    assert misses == 1
    osu = next(g for t in updated.teams if t.team == "Ohio State" for g in t.games)
    assert osu.predicted_winner == "Ohio State"
    assert osu.actual_winner == "Texas"
    mich = next(g for t in updated.teams if t.team == "Michigan" for g in t.games)
    assert mich.predicted_winner == "Michigan"


def test_apply_called_misses_picks_the_loser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    games = [
        _cfb(
            "ucla-cal",
            1,
            "UCLA",
            "California",
            "B1G",
            "ACC",
            home_score=10,
            away_score=17,
        )
    ]
    book = init_book(games, RESEARCH_WINDOWS.hands_off)
    book = sync_actuals(book, games)
    book = set_winner(book, "ucla-cal", "UCLA")
    updated, n = apply_called_misses(book, [("UCLA", "CAL")])
    assert n == 1
    row = next(g for t in updated.teams if t.team == "UCLA" for g in t.games)
    assert row.actual_winner == "UCLA"
    assert row.predicted_winner == "California"


def _cover_book() -> SeasonPredictions:
    row = dict(
        game_id="g",
        week=1,
        predicted_winner="KC",
        pick_kind="cover",
        cover_favorite="KC",
        cover_line=6.5,
    )
    return SeasonPredictions(
        season=2026,
        teams=[
            TeamSeasonTake(
                team="KC",
                league=League.NFL,
                conference="AFC",
                games=[SeasonGameTake(opponent="BUF", is_home=True, **row)],
            ),
            TeamSeasonTake(
                team="BUF",
                league=League.NFL,
                conference="AFC",
                games=[SeasonGameTake(opponent="KC", is_home=False, **row)],
            ),
        ],
    )


def test_cover_holds_a_small_move_and_rewrites_when_the_favorite_flips() -> None:
    from sbm.predictions import audit_covers, set_pick

    game = Game(
        game_id="g",
        league=League.NFL,
        season=2026,
        week=1,
        home_team="KC",
        away_team="BUF",
    )
    held, changed = audit_covers(_cover_book(), {"g": 8.0}, {"g": game})
    assert changed is False
    assert held.teams[0].games[0].pick_kind == "cover"

    flipped, changed = audit_covers(_cover_book(), {"g": -3.0}, {"g": game})
    assert changed is True
    assert flipped.audits[0].change == "flip"
    for team in flipped.teams:
        row = team.games[0]
        assert row.pick_kind == "outright"
        assert row.predicted_winner == "KC"
        assert row.cover_favorite is None

    moved, changed = audit_covers(_cover_book(), {"g": 10.0}, {"g": game})
    assert changed is True
    assert moved.audits[0].change == "move"

    pickem, changed = audit_covers(_cover_book(), {"g": 0.2}, {"g": game})
    assert changed is True
    assert pickem.audits[0].change == "pickem"

    picked = set_pick(
        _cover_book(),
        "g",
        "away",
        home_margin=6.5,
        away_team="BUF",
        home_team="KC",
    )
    assert picked.teams[0].games[0].pick_kind == "outright"
    assert picked.teams[0].games[0].predicted_winner == "BUF"
