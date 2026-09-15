from sbm.schema import League
from sbm.teams import aliases_for, book_ticket_label, display_name, search_blob


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


def test_nfl_display_is_location_and_nickname() -> None:
    assert display_name(League.NFL, "PIT") == "Pittsburgh Steelers"
    assert display_name(League.NFL, "JAX") == "Jacksonville Jaguars"


def test_cfb_display_is_school_and_nickname() -> None:
    assert display_name(League.CFB, "Michigan") == "Michigan Wolverines"
    assert display_name(League.CFB, "Ohio State") == "Ohio State Buckeyes"


def test_book_ticket_includes_matchup_abbrevs_for_totals() -> None:
    label = book_ticket_label(
        column="system",
        league=League.NFL,
        week=2,
        away_team="PIT",
        home_team="NE",
        team_or_side="under",
        market="total",
    )
    assert label == "System · NFL w2 PIT@NE under total"


def test_cfb_book_ticket_uses_school_abbrevs() -> None:
    label = book_ticket_label(
        column="gut",
        league=League.CFB,
        week=3,
        away_team="Michigan",
        home_team="Ohio State",
        team_or_side="Michigan",
        market="spread",
    )
    assert label == "Gut · CFB w3 MICH@OSU MICH spread"
