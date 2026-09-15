from enum import StrEnum


class Mode(StrEnum):
    SIMULATION = "simulation"
    LIVE = "live"


def parse_mode(value: str) -> Mode:
    try:
        return Mode(value.lower())
    except ValueError as exc:
        raise ValueError(f"Unknown mode {value!r}; expected simulation or live") from exc
