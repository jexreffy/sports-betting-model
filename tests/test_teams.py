from sbm.schema import League
from sbm.teams import aliases_for, search_blob


def test_nfl_search_includes_city_and_nickname() -> None:
    blob = search_blob(League.NFL, "PIT", "NE")
    assert "steelers" in blob
    assert "pittsburgh" in blob
    assert "patriots" in blob
    assert "new england" in blob


def test_cfb_search_includes_nickname() -> None:
    names = aliases_for(League.CFB, "Michigan")
    assert "wolverines" in names
    assert "Michigan" in names
