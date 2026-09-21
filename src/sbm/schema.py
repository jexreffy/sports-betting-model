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


class StakeColumn(StrEnum):
    SYSTEM = "system"
    GUT = "gut"


class TicketKind(StrEnum):
    STRAIGHT = "straight"
    PARLAY = "parlay"


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
    column: StakeColumn = StakeColumn.SYSTEM
    skipped: bool = False


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


class ColumnStats(BaseModel):
    n_picks: int = 0
    n_settled: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    units: float = 0.0
    roi: float | None = None
    ats_pct: float | None = None


class Leg(BaseModel):
    """One side of a Journal ticket. Props may omit market and game_id."""

    league: League
    season: int
    week: int
    team_or_side: str
    game_id: str | None = None
    market: Market | None = None
    side: Side | None = None
    market_line: float | None = None
    american_odds: int | None = None
    opponent: str | None = None


class Ticket(BaseModel):
    ticket_id: str
    season: int
    sportsbook: str
    stake_dollars: float
    american_odds: int
    kind: TicketKind
    legs: list[Leg]
    result: str | None = None
    profit_dollars: float | None = None
    cashout_dollars: float | None = None
    implied_prob: float | None = None
    placed_at: datetime | None = None
    settled_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def valid_ticket(self) -> "Ticket":
        if not self.legs:
            raise ValueError("Ticket needs at least one leg")
        if self.kind == TicketKind.STRAIGHT and len(self.legs) != 1:
            raise ValueError("Straight tickets need exactly one leg")
        if self.kind == TicketKind.PARLAY and len(self.legs) < 2:
            raise ValueError("Parlays need at least two legs")
        if self.result == "cashout" and self.cashout_dollars is None:
            raise ValueError("Cash-out tickets need cashout_dollars")
        return self


class JournalYearStats(BaseModel):
    season: int
    n_tickets: int = 0
    n_open: int = 0
    hits: int = 0
    misses: int = 0
    pushes: int = 0
    cashed_early: int = 0
    staked_dollars: float = 0.0
    profit_dollars: float = 0.0
    roi: float | None = None


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
    system: ColumnStats = Field(default_factory=ColumnStats)
    gut: ColumnStats = Field(default_factory=ColumnStats)

    def as_dict(self) -> dict:
        return self.model_dump()
