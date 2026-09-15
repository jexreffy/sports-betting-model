from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from sbm.mode import Mode


class League(StrEnum):
    NFL = "nfl"
    CFB = "cfb"


class ResearchWindow(StrEnum):
    WARMUP = "warmup"
    SEARCH = "search"
    HOLDOUT = "holdout"
    HANDS_OFF = "hands_off"


class Market(StrEnum):
    SPREAD = "spread"
    MONEYLINE = "moneyline"
    TOTAL = "total"


class Side(StrEnum):
    HOME = "home"
    AWAY = "away"
    OVER = "over"
    UNDER = "under"


class Game(BaseModel):
    game_id: str
    league: League
    season: int
    week: int
    home_team: str
    away_team: str
    kickoff: datetime | None = None
    home_score: int | None = None
    away_score: int | None = None
    spread_close: float | None = None
    total_close: float | None = None
    home_moneyline: int | None = None
    away_moneyline: int | None = None
    home_rest_days: int | None = None
    away_rest_days: int | None = None
    is_neutral: bool = False

    @property
    def is_final(self) -> bool:
        return self.home_score is not None and self.away_score is not None

    @property
    def home_margin(self) -> float | None:
        if not self.is_final:
            return None
        return float(self.home_score - self.away_score)  # type: ignore[operator]

    @property
    def total_points(self) -> float | None:
        if not self.is_final:
            return None
        return float(self.home_score + self.away_score)  # type: ignore[operator]


class Prediction(BaseModel):
    game_id: str
    predicted_home_margin: float
    predicted_total: float
    home_win_prob: float


class Pick(BaseModel):
    mode: Mode
    game_id: str
    league: League
    season: int
    week: int
    market: Market
    side: Side
    team_or_side: str
    model_line: float | None = None
    market_line: float | None = None
    model_prob: float | None = None
    market_prob: float | None = None
    edge: float
    american_odds: int = -110
    units: float = 1.0
    placed_at: datetime | None = None
    research_window: ResearchWindow | None = None


class LedgerEntry(BaseModel):
    mode: Mode
    pick: Pick
    result: str | None = None
    profit_units: float | None = None
    home_score: int | None = None
    away_score: int | None = None
    closing_spread: float | None = None
    closing_total: float | None = None
    settled_at: datetime | None = None

    @model_validator(mode="after")
    def mode_matches_pick(self) -> "LedgerEntry":
        if self.pick.mode != self.mode:
            raise ValueError("LedgerEntry.mode must match pick.mode")
        return self


class BankrollPoint(BaseModel):
    index: int
    season: int
    week: int
    cumulative_units: float
    game_id: str


class SummaryStats(BaseModel):
    mode: Mode
    n_picks: int = 0
    n_settled: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    units: float = 0.0
    roi: float | None = None
    ats_pct: float | None = None
    brier: float | None = Field(default=None)

    def as_dict(self) -> dict:
        return self.model_dump()
