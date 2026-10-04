"""Download one season range into data/raw. Other seasons already on disk stay."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from sbm.schema import League


@dataclass(frozen=True)
class IngestResult:
    seasons: tuple[int, ...]
    nfl_games: int | None = None
    nfl_unit_weeks: int | None = None
    cfb_games: int | None = None
    cfb_unit_weeks: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "seasons": list(self.seasons),
            "nfl_games": self.nfl_games,
            "nfl_unit_weeks": self.nfl_unit_weeks,
            "cfb_games": self.cfb_games,
            "cfb_unit_weeks": self.cfb_unit_weeks,
        }


def _targets(league: str) -> list[League]:
    token = league.lower()
    if token == "all":
        return [League.NFL, League.CFB]
    if token in {League.NFL.value, League.CFB.value}:
        return [League(token)]
    raise ValueError("league must be nfl, cfb, or all")


def ingest_seasons(league: str, seasons: list[int]) -> IngestResult:
    """Replace `seasons` for the requested leagues. Earlier and later seasons stay."""
    if not seasons:
        raise ValueError("seasons must not be empty")
    targets = _targets(league)
    nfl_payload: tuple[list, list] | None = None
    cfb_payload: tuple[list, list] | None = None
    try:
        if League.NFL in targets:
            from sbm.data.nfl import download_nfl_games, download_nfl_team_stats
            from sbm.units import nfl_unit_weeks

            games = download_nfl_games(seasons)
            weeks = nfl_unit_weeks(download_nfl_team_stats(seasons), games)
            nfl_payload = (games, weeks)
        if League.CFB in targets:
            from sbm.data.cfb import download_cfb_advanced, download_cfb_games, download_cfb_talent
            from sbm.units import cfb_unit_weeks

            games = download_cfb_games(seasons)
            weeks = cfb_unit_weeks(download_cfb_advanced(seasons), download_cfb_talent(seasons))
            cfb_payload = (games, weeks)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Score refresh failed ({type(exc).__name__}).") from exc

    from sbm.data.store import save_games
    from sbm.units import save_units

    nfl_games: int | None = None
    nfl_units: int | None = None
    cfb_games: int | None = None
    cfb_units: int | None = None
    replace = set(seasons)
    if nfl_payload is not None:
        games, weeks = nfl_payload
        save_games(League.NFL, games, replace_seasons=replace)
        save_units(weeks, league=League.NFL, replace_seasons=replace)
        nfl_games = len(games)
        nfl_units = len(weeks)
    if cfb_payload is not None:
        games, weeks = cfb_payload
        save_games(League.CFB, games, replace_seasons=replace)
        save_units(weeks, league=League.CFB, replace_seasons=replace)
        cfb_games = len(games)
        cfb_units = len(weeks)
    return IngestResult(
        seasons=tuple(seasons),
        nfl_games=nfl_games,
        nfl_unit_weeks=nfl_units,
        cfb_games=cfb_games,
        cfb_unit_weeks=cfb_units,
    )
