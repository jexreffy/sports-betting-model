from enum import StrEnum


class Mode(StrEnum):
    """Research / paper path only. Real tickets live in the Journal store."""

    SIMULATION = "simulation"


def parse_mode(value: str) -> Mode:
    lowered = value.lower()
    if lowered == "live":
        raise ValueError("Live was renamed to Journal; use /journal or `sbm journal`")
    try:
        return Mode(lowered)
    except ValueError as exc:
        raise ValueError(f"Unknown mode {value!r}; expected simulation") from exc
