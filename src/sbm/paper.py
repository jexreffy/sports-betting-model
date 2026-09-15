from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sbm.mode import Mode
from sbm.paths import ledger_path
from sbm.schema import (
    BankrollPoint,
    Game,
    LedgerEntry,
    Pick,
    SummaryStats,
)


class ModeMismatchError(ValueError):
    pass


class Ledger:
    def __init__(self, mode: Mode, path: Path | None = None) -> None:
        self.mode = mode
        self.path = path or ledger_path(mode)

    def _check(self, mode: Mode) -> None:
        if mode != self.mode:
            raise ModeMismatchError(
                f"Refusing to write {mode.value} data into {self.mode.value} ledger"
            )

    def append(self, entry: LedgerEntry) -> None:
        self._check(entry.mode)
        self._check(entry.pick.mode)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(entry.model_dump_json() + "\n")

    def load(self) -> list[LedgerEntry]:
        if not self.path.exists():
            return []
        entries: list[LedgerEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = LedgerEntry.model_validate_json(line)
            if entry.mode != self.mode:
                raise ModeMismatchError(
                    f"Ledger {self.path} contains {entry.mode.value} row"
                )
            entries.append(entry)
        return entries

    def game_ids(self) -> set[str]:
        return {e.pick.game_id + ":" + e.pick.market + ":" + e.pick.side for e in self.load()}

    def record_picks(self, picks: list[Pick]) -> int:
        existing = self.game_ids()
        added = 0
        for pick in picks:
            key = f"{pick.game_id}:{pick.market}:{pick.side}"
            if key in existing:
                continue
            self.append(LedgerEntry(mode=self.mode, pick=pick))
            added += 1
        return added

    def settle(self, games: dict[str, Game]) -> int:
        entries = self.load()
        settled = 0
        from sbm.odds import settle_pick

        updated: list[LedgerEntry] = []
        for entry in entries:
            if entry.result is not None:
                updated.append(entry)
                continue
            game = games.get(entry.pick.game_id)
            if game is None or not game.is_final:
                updated.append(entry)
                continue
            result, profit = settle_pick(entry.pick, game)
            updated.append(
                entry.model_copy(
                    update={
                        "result": result,
                        "profit_units": profit,
                        "home_score": game.home_score,
                        "away_score": game.away_score,
                        "closing_spread": game.spread_close,
                        "closing_total": game.total_close,
                        "settled_at": datetime.now(UTC),
                    }
                )
            )
            settled += 1
        self._rewrite(updated)
        return settled

    def _rewrite(self, entries: list[LedgerEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(entry.model_dump_json() + "\n")

    def summary(self) -> SummaryStats:
        entries = self.load()
        settled = [e for e in entries if e.result is not None]
        wins = sum(1 for e in settled if e.result == "win")
        losses = sum(1 for e in settled if e.result == "loss")
        pushes = sum(1 for e in settled if e.result == "push")
        units = sum(e.profit_units or 0.0 for e in settled)
        decided = wins + losses
        staked = sum(e.pick.units for e in settled if e.result != "push")
        roi = (units / staked) if staked else None
        ats = (wins / decided) if decided else None
        brier_vals: list[float] = []
        for e in settled:
            if e.pick.model_prob is None:
                continue
            y = 1.0 if e.result == "win" else (0.5 if e.result == "push" else 0.0)
            brier_vals.append((e.pick.model_prob - y) ** 2)
        brier = sum(brier_vals) / len(brier_vals) if brier_vals else None
        return SummaryStats(
            mode=self.mode,
            n_picks=len(entries),
            n_settled=len(settled),
            wins=wins,
            losses=losses,
            pushes=pushes,
            units=round(units, 3),
            roi=None if roi is None else round(roi, 4),
            ats_pct=None if ats is None else round(ats, 4),
            brier=None if brier is None else round(brier, 4),
        )

    def curve(self) -> list[BankrollPoint]:
        points: list[BankrollPoint] = []
        running = 0.0
        i = 0
        for entry in self.load():
            if entry.result is None or entry.profit_units is None:
                continue
            running += entry.profit_units
            i += 1
            points.append(
                BankrollPoint(
                    index=i,
                    season=entry.pick.season,
                    week=entry.pick.week,
                    cumulative_units=round(running, 3),
                    game_id=entry.pick.game_id,
                )
            )
        return points
