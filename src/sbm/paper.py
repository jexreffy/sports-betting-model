from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sbm.mode import Mode
from sbm.paths import ledger_path
from sbm.schema import (
    BankrollPoint,
    ColumnStats,
    Game,
    LedgerEntry,
    Market,
    Pick,
    Side,
    StakeColumn,
    SummaryStats,
)


class ModeMismatchError(ValueError):
    pass


def row_key(pick: Pick) -> str:
    return f"{pick.game_id}:{pick.market.value}:{pick.column.value}"


def _matches_week(pick: Pick, season: int | None, week: int | None) -> bool:
    if season is not None and pick.season != season:
        return False
    if week is not None and pick.week != week:
        return False
    return True


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
        return {row_key(e.pick) for e in self.load()}

    def record_picks(self, picks: list[Pick]) -> int:
        existing = self.game_ids()
        added = 0
        for pick in picks:
            key = row_key(pick)
            if key in existing:
                continue
            self.append(LedgerEntry(mode=self.mode, pick=pick))
            added += 1
        return added

    def infer_open_week(self) -> tuple[int, int] | None:
        open_rows = [e for e in self.load() if e.result is None]
        if not open_rows:
            return None
        season = max(e.pick.season for e in open_rows)
        week = min(e.pick.week for e in open_rows if e.pick.season == season)
        return season, week

    def settle(
        self,
        games: dict[str, Game],
        *,
        season: int | None = None,
        week: int | None = None,
    ) -> int:
        entries = self.load()
        settled = 0
        from sbm.odds import settle_pick

        updated: list[LedgerEntry] = []
        for entry in entries:
            if not _matches_week(entry.pick, season, week):
                updated.append(entry)
                continue
            if entry.result is not None:
                updated.append(entry)
                continue
            if entry.pick.skipped:
                updated.append(
                    entry.model_copy(
                        update={
                            "result": "skip",
                            "profit_units": 0.0,
                            "settled_at": datetime.now(UTC),
                        }
                    )
                )
                settled += 1
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

    def mark(
        self,
        *,
        game_id: str,
        market: Market,
        column: StakeColumn,
        skipped: bool,
        side: Side | None = None,
        team_or_side: str | None = None,
        source: Pick | None = None,
    ) -> LedgerEntry:
        entries = self.load()
        idx = next(
            (
                i
                for i, entry in enumerate(entries)
                if entry.pick.game_id == game_id
                and entry.pick.market == market
                and entry.pick.column == column
            ),
            None,
        )
        if idx is None:
            if source is None:
                raise ValueError("No diary row to mark")
            self._check(source.mode)
            pick = source.model_copy(
                update={
                    "mode": self.mode,
                    "column": column,
                    "skipped": skipped,
                    "side": side or source.side,
                    "team_or_side": team_or_side or source.team_or_side,
                }
            )
            entry = LedgerEntry(mode=self.mode, pick=pick)
            self.append(entry)
            return entry
        entry = entries[idx]
        if entry.result is not None:
            raise ValueError("Cannot mark a settled pick")
        pick_update: dict[str, object] = {"skipped": skipped}
        if side is not None:
            pick_update["side"] = side
        if team_or_side is not None:
            pick_update["team_or_side"] = team_or_side
        entries[idx] = entry.model_copy(update={"pick": entry.pick.model_copy(update=pick_update)})
        self._rewrite(entries)
        return entries[idx]

    def drop(
        self,
        *,
        game_id: str,
        market: Market,
        column: StakeColumn,
    ) -> None:
        entries = self.load()
        kept: list[LedgerEntry] = []
        removed = False
        for entry in entries:
            match = (
                entry.pick.game_id == game_id
                and entry.pick.market == market
                and entry.pick.column == column
            )
            if not match:
                kept.append(entry)
                continue
            if entry.result is not None:
                raise ValueError("Cannot drop a settled pick")
            removed = True
        if not removed:
            raise ValueError("No open ticket to drop")
        self._rewrite(kept)

    def _rewrite(self, entries: list[LedgerEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(entry.model_dump_json() + "\n")

    def _scoped(self, *, season: int | None = None, week: int | None = None) -> list[LedgerEntry]:
        return [e for e in self.load() if _matches_week(e.pick, season, week)]

    def summary(self, *, season: int | None = None, week: int | None = None) -> SummaryStats:
        entries = self._scoped(season=season, week=week)
        system = _stats_for(entries, StakeColumn.SYSTEM)
        gut = _stats_for(entries, StakeColumn.GUT)
        brier = _brier(entries)
        return SummaryStats(
            mode=self.mode,
            n_picks=system.n_picks,
            n_settled=system.n_settled,
            wins=system.wins,
            losses=system.losses,
            pushes=system.pushes,
            units=system.units,
            roi=system.roi,
            ats_pct=system.ats_pct,
            brier=brier,
            system=system,
            gut=gut,
        )

    def curve(self, *, season: int | None = None, week: int | None = None) -> list[BankrollPoint]:
        points: list[BankrollPoint] = []
        running = 0.0
        i = 0
        for entry in self._scoped(season=season, week=week):
            if entry.pick.column != StakeColumn.SYSTEM or entry.pick.skipped:
                continue
            if entry.result is None or entry.profit_units is None or entry.result == "skip":
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


def _stats_for(entries: list[LedgerEntry], column: StakeColumn) -> ColumnStats:
    col = [e for e in entries if e.pick.column == column and not e.pick.skipped]
    settled = [e for e in col if e.result is not None and e.result != "skip"]
    wins = sum(1 for e in settled if e.result == "win")
    losses = sum(1 for e in settled if e.result == "loss")
    pushes = sum(1 for e in settled if e.result == "push")
    units = sum(e.profit_units or 0.0 for e in settled)
    decided = wins + losses
    staked = sum(e.pick.units for e in settled if e.result != "push")
    roi = (units / staked) if staked else None
    ats = (wins / decided) if decided else None
    return ColumnStats(
        n_picks=len(col),
        n_settled=len(settled),
        wins=wins,
        losses=losses,
        pushes=pushes,
        units=round(units, 3),
        roi=None if roi is None else round(roi, 4),
        ats_pct=None if ats is None else round(ats, 4),
    )


def _brier(entries: list[LedgerEntry]) -> float | None:
    brier_vals: list[float] = []
    for entry in entries:
        if entry.pick.skipped or entry.pick.column != StakeColumn.SYSTEM:
            continue
        if entry.result is None or entry.result == "skip" or entry.pick.model_prob is None:
            continue
        y = 1.0 if entry.result == "win" else (0.5 if entry.result == "push" else 0.0)
        brier_vals.append((entry.pick.model_prob - y) ** 2)
    if not brier_vals:
        return None
    return round(sum(brier_vals) / len(brier_vals), 4)
