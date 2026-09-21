import pytest

from sbm.rankings import RankingsBook, move_team, place_team, visible_order, you_rank


def test_visible_order_appends_new_teams_and_move_swaps() -> None:
    assert visible_order([], ["A", "B"]) == ["A", "B"]
    assert visible_order(["B", "A"], ["A", "B", "C"]) == ["B", "A", "C"]
    assert move_team(["A", "B", "C"], "B", "up") == ["B", "A", "C"]
    assert move_team(["A", "B"], "A", "up") == ["A", "B"]
    assert you_rank(["B", "A"], "A") == 2
    assert you_rank([], "A") is None


def test_place_team_moves_to_an_index() -> None:
    assert place_team(["A", "B", "C", "D"], "D", 0) == ["D", "A", "B", "C"]
    assert place_team(["A", "B", "C", "D"], "A", 2) == ["B", "C", "A", "D"]
    assert place_team(["A", "B"], "A", 5) == ["B", "A"]


def test_move_rejects_unknown_direction() -> None:
    with pytest.raises(ValueError):
        move_team(["A"], "A", "sideways")


def test_rankings_round_trip(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SBM_DATA_DIR", str(tmp_path))
    from sbm.rankings import load_rankings, save_rankings

    book = RankingsBook(season=2026, groups={"nfl": ["KC", "BUF"]})
    save_rankings(book)
    loaded = load_rankings(2026)
    assert loaded.groups["nfl"] == ["KC", "BUF"]
