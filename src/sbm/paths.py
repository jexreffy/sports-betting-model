from pathlib import Path

from sbm.config import get_settings
from sbm.mode import Mode


def data_root() -> Path:
    root = get_settings().data_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def raw_dir() -> Path:
    path = data_root() / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def mode_dir(mode: Mode) -> Path:
    path = data_root() / mode.value
    path.mkdir(parents=True, exist_ok=True)
    return path


def ledger_path(mode: Mode) -> Path:
    return mode_dir(mode) / "ledger.jsonl"


def historical_ledger_path(mode: Mode) -> Path:
    """Walk-forward P&L only. Never the current-week paper book."""
    return mode_dir(mode) / "historical_ledger.jsonl"


def journal_dir() -> Path:
    path = data_root() / "journal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def journal_tickets_path() -> Path:
    return journal_dir() / "tickets.jsonl"


def live_ledger_legacy_path() -> Path:
    """Pre-Journal paper file. Read for migrate only; never write."""
    return data_root() / "live" / "ledger.jsonl"


def games_path(league: str) -> Path:
    return raw_dir() / f"{league}_games.jsonl"


def predictions_dir() -> Path:
    path = data_root() / "predictions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def predictions_path(season: int) -> Path:
    return predictions_dir() / f"{season}.json"
