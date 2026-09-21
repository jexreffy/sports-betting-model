from sbm.schema import League
from sbm.teams import (
    aliases_for,
    book_ticket_label,
    display_name,
    logo_url,
    render_abbrev,
    render_display_name,
    render_logo_mark,
    render_logo_url,
    search_blob,
    team_color,
    team_face,
)


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


def test_rendered_name_splits_place_and_nickname() -> None:
    carolina = team_face(League.CFB, "South Carolina")
    assert carolina.place == "South Carolina"
    assert carolina.nickname == "Gamecocks"
    assert carolina.display_name == "South Carolina Gamecocks"
    bay = team_face(League.NFL, "TB")
    assert bay.place == "Tampa Bay"
    assert bay.nickname == "Buccaneers"
    tide = team_face(League.CFB, "Alabama")
    assert tide.place == "Alabama"
    assert tide.nickname == "Crimson Tide"
    ttun = team_face(League.CFB, "Michigan")
    assert ttun.place == "The Team"
    assert ttun.nickname == "Up North"
    assert ttun.display_name == "The Team Up North"


def test_michigan_render_is_ttun_only() -> None:
    assert render_display_name(League.CFB, "Michigan") == "The Team Up North"
    assert render_abbrev(League.CFB, "Michigan") == "TTUN"
    assert render_logo_mark(League.CFB, "Michigan") == "❌"
    assert render_logo_url(League.CFB, "Michigan") is None
    assert render_abbrev(League.CFB, "Michigan State") == "MSU"
    assert "ncaa/500/130.png" in (logo_url(League.CFB, "Michigan") or "")


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


def test_nfl_logo_uses_espn_slug() -> None:
    assert logo_url(League.NFL, "LA").endswith("/lar.png")
    assert logo_url(League.NFL, "WAS").endswith("/wsh.png")
    assert logo_url(League.NFL, "KC").endswith("/kc.png")
    assert "ncaa/500/87.png" in (logo_url(League.CFB, "Notre Dame") or "")


def test_team_face_renders_ttun_and_keeps_the_stored_name() -> None:
    face = team_face(League.CFB, "Michigan", "B1G")
    assert face.team == "Michigan"
    assert face.display_name == "The Team Up North"
    assert face.abbrev == "TTUN"
    assert face.logo_mark == "❌"
    assert face.logo_url is None
    assert "ttun" in face.search_text
    assert "wolverines" in face.search_text
    state = team_face(League.CFB, "Michigan State")
    assert state.abbrev == "MSU"
    assert state.logo_url


def test_cfb_team_color_is_school_primary() -> None:
    assert team_color(League.CFB, "Michigan", "B1G") == "#00274C"
    assert team_color(League.CFB, "Ohio State", "B1G") == "#BB0000"
    assert team_color(League.NFL, "KC") == "#E31837"
