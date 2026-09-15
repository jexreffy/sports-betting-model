from __future__ import annotations

from pathlib import Path

from sbm.paths import games_path
from sbm.schema import Game, League


def save_games(
    league: League,
    games: list[Game],
    path: Path | None = None,
    *,
    replace_seasons: set[int] | None = None,
) -> Path:
    """Write games, replacing only the given seasons (default: seasons in `games`).

    Other seasons already on disk are kept so a 2026-only ingest cannot wipe 2015–2025.
    """
    dest = path or games_path(league.value)
    dest.parent.mkdir(parents=True, exist_ok=True)
    seasons = replace_seasons if replace_seasons is not None else {g.season for g in games}
    existing = _read(dest) if dest.exists() else []
    kept = [g for g in existing if g.season not in seasons]
    merged = _sort(kept + list(games))
    with dest.open("w", encoding="utf-8") as fh:
        for game in merged:
            fh.write(game.model_dump_json() + "\n")
    return dest


def load_games(league: League | None = None, path: Path | None = None) -> list[Game]:
    if path is not None:
        return _read(path)
    if league is None:
        games: list[Game] = []
        for lg in League:
            p = games_path(lg.value)
            if p.exists():
                games.extend(_read(p))
        return _sort(games)
    path = games_path(league.value)
    if not path.exists():
        return []
    return _sort(_read(path))


def games_by_id(games: list[Game]) -> dict[str, Game]:
    return {g.game_id: g for g in games}


def _read(path: Path) -> list[Game]:
    out: list[Game] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Game.model_validate_json(line))
    return out


def _sort(games: list[Game]) -> list[Game]:
    return sorted(
        games,
        key=lambda g: (
            g.season,
            g.week,
            g.kickoff.isoformat() if g.kickoff else "",
            g.game_id,
        ),
    )
