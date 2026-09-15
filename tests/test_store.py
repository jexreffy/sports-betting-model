from datetime import UTC, datetime
from pathlib import Path

from sbm.data.store import load_games, save_games
from sbm.schema import Game, League


def _g(season: int, week: int, gid: str, kickoff: datetime | None = None) -> Game:
    return Game(
        game_id=gid,
        league=League.NFL,
        season=season,
        week=week,
        home_team="KC",
        away_team="BAL",
        kickoff=kickoff,
    )


def test_save_merges_and_keeps_other_seasons(tmp_path: Path) -> None:
    path = tmp_path / "nfl_games.jsonl"
    save_games(League.NFL, [_g(2024, 1, "old")], path=path)
    save_games(League.NFL, [_g(2026, 1, "new")], path=path, replace_seasons={2026})
    ids = {g.game_id for g in load_games(path=path)}
    assert ids == {"old", "new"}


def test_save_replaces_only_requested_season(tmp_path: Path) -> None:
    path = tmp_path / "nfl_games.jsonl"
    save_games(League.NFL, [_g(2024, 1, "old-a"), _g(2026, 1, "old-b")], path=path)
    save_games(League.NFL, [_g(2026, 2, "fresh")], path=path, replace_seasons={2026})
    games = load_games(path=path)
    assert {g.game_id for g in games} == {"old-a", "fresh"}


def test_sort_is_season_week_then_kickoff(tmp_path: Path) -> None:
    path = tmp_path / "nfl_games.jsonl"
    later = _g(2026, 1, "later")
    earlier = _g(2024, 1, "earlier", kickoff=datetime(2024, 9, 5, tzinfo=UTC))
    save_games(League.NFL, [later, earlier], path=path, replace_seasons={2024, 2026})
    games = load_games(path=path)
    assert [g.game_id for g in games] == ["earlier", "later"]
