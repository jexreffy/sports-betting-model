"""User order of teams. Display context only — it does not move the model or the heatmap."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sbm.paths import rankings_path


class RankingsBook(BaseModel):
    season: int
    groups: dict[str, list[str]] = Field(default_factory=dict)


def load_rankings(season: int) -> RankingsBook:
    path = rankings_path(season)
    if not path.exists():
        return RankingsBook(season=season)
    return RankingsBook.model_validate_json(path.read_text(encoding="utf-8"))


def save_rankings(book: RankingsBook) -> None:
    path = rankings_path(book.season)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(book.model_dump_json(indent=2), encoding="utf-8")


def visible_order(saved: list[str], model_order: list[str]) -> list[str]:
    """Saved order first. Teams the model has and the list does not are appended."""
    if not saved:
        return list(model_order)
    known = set(saved)
    return list(saved) + [team for team in model_order if team not in known]


def place_team(order: list[str], team: str, index: int) -> list[str]:
    """Move `team` to a 0-based index. The index is the slot after the team is removed."""
    if team not in order:
        raise ValueError(f"{team} is not in this ranking")
    updated = [name for name in order if name != team]
    slot = max(0, min(index, len(updated)))
    updated.insert(slot, team)
    return updated


def move_team(order: list[str], team: str, direction: str) -> list[str]:
    if direction not in {"up", "down"}:
        raise ValueError(f"Unknown direction {direction}")
    if team not in order:
        raise ValueError(f"{team} is not in this ranking")
    index = order.index(team)
    swap = index - 1 if direction == "up" else index + 1
    if swap < 0 or swap >= len(order):
        return list(order)
    updated = list(order)
    updated[index], updated[swap] = updated[swap], updated[index]
    return updated


def you_rank(saved: list[str], team: str) -> int | None:
    if team not in saved:
        return None
    return saved.index(team) + 1
