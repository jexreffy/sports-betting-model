from pathlib import Path

from sbm.mode import Mode
from sbm.schema import Game, League
from sbm.web.board import game_cards


def test_cards_group_picks_under_matchup() -> None:
    games = [
        Game(
            game_id="g1",
            league=League.NFL,
            season=2024,
            week=5,
            home_team="KC",
            away_team="BUF",
            home_score=None,
            away_score=None,
            spread_close=-14,
            total_close=60,
            home_moneyline=-400,
            away_moneyline=320,
        )
    ]
    cards, _picks = game_cards(games, Mode.SIMULATION)
    assert len(cards) == 1
    card = cards[0]
    assert card["away_team"] == "BUF"
    assert card["home_team"] == "KC"
    assert card["away_display"] == "Buffalo Bills"
    assert card["home_display"] == "Kansas City Chiefs"
    assert card["away_abbrev"] == "BUF"
    spread = next(m for m in card["markets"] if m["name"] == "spread")
    assert {opt["label"] for opt in spread["side_options"]} == {"BUF", "KC"}
    names = [m["name"] for m in card["markets"]]
    assert names == ["spread", "total", "moneyline"]
    assert "model_ticket" in card["markets"][0]
    assert "system" in card["markets"][0]
    assert "gut" in card["markets"][0]


def test_card_surfaces_gut_mark(tmp_path: Path) -> None:
    from sbm.paper import Ledger
    from sbm.schema import LedgerEntry, Market, Pick, Side, StakeColumn

    game = Game(
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=2,
        home_team="TB",
        away_team="CLE",
        spread_close=-8.5,
        total_close=40.5,
        home_moneyline=-375,
        away_moneyline=295,
    )
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "ledger.jsonl")
    source = Pick(
        mode=Mode.SIMULATION,
        game_id="g1",
        league=League.NFL,
        season=2026,
        week=2,
        market=Market.SPREAD,
        side=Side.AWAY,
        team_or_side="CLE",
        edge=2.5,
        column=StakeColumn.SYSTEM,
    )
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=source))
    ledger.mark(
        game_id="g1",
        market=Market.SPREAD,
        column=StakeColumn.GUT,
        skipped=False,
        side=Side.HOME,
        team_or_side="TB",
        source=source,
    )
    cards, _ = game_cards([game], Mode.SIMULATION, ledger=ledger)
    assert cards[0]["has_gut"] is True
    assert "TB spread" in cards[0]["gut_label"]
    spread = next(m for m in cards[0]["markets"] if m["name"] == "spread")
    assert spread["gut"]["team_or_side"] == "TB"
