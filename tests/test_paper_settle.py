from pathlib import Path

from sbm.mode import Mode
from sbm.paper import Ledger
from sbm.schema import Game, League, LedgerEntry, Market, Pick, Side


def _pick(mode: Mode = Mode.SIMULATION, game_id: str = "g1") -> Pick:
    return Pick(
        mode=mode,
        game_id=game_id,
        league=League.NFL,
        season=2024,
        week=1,
        market=Market.SPREAD,
        side=Side.HOME,
        team_or_side="KC",
        edge=3.0,
        model_prob=0.62,
    )


def _final(game_id: str = "g1", home: int = 24, away: int = 17) -> Game:
    return Game(
        game_id=game_id,
        league=League.NFL,
        season=2024,
        week=1,
        home_team="KC",
        away_team="BAL",
        home_score=home,
        away_score=away,
        spread_close=-3.0,
        total_close=45.0,
    )


def test_settle_win_then_summary_and_curve(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick()))
    assert ledger.settle({"g1": _final()}) == 1
    assert ledger.settle({"g1": _final()}) == 0
    summary = ledger.summary()
    assert summary.wins == 1
    assert summary.n_settled == 1
    assert summary.units > 0
    curve = ledger.curve()
    assert len(curve) == 1
    assert curve[0].cumulative_units == summary.units


def test_record_picks_is_idempotent(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    pick = _pick()
    assert ledger.record_picks([pick]) == 1
    assert ledger.record_picks([pick]) == 0
    assert len(ledger.load()) == 1


def test_unfinished_game_stays_open(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick()))
    open_game = _final().model_copy(update={"home_score": None, "away_score": None})
    assert ledger.settle({"g1": open_game}) == 0
    assert ledger.load()[0].result is None


def test_settle_week_leaves_other_weeks_open(tmp_path: Path) -> None:
    ledger = Ledger(Mode.SIMULATION, path=tmp_path / "simulation" / "ledger.jsonl")
    ledger.append(LedgerEntry(mode=Mode.SIMULATION, pick=_pick(game_id="w1")))
    ledger.append(
        LedgerEntry(
            mode=Mode.SIMULATION,
            pick=_pick(game_id="w2").model_copy(update={"week": 2, "game_id": "w2"}),
        )
    )
    games = {
        "w1": _final("w1"),
        "w2": _final("w2").model_copy(update={"week": 2}),
    }
    assert ledger.settle(games, season=2024, week=2) == 1
    by_id = {e.pick.game_id: e for e in ledger.load()}
    assert by_id["w1"].result is None
    assert by_id["w2"].result == "win"
    week_summary = ledger.summary(season=2024, week=2)
    assert week_summary.n_settled == 1
    assert ledger.summary(season=2024, week=1).n_settled == 0
