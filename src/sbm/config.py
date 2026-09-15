from dataclasses import dataclass
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sbm.schema import League, ResearchWindow


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    data_dir: Path = Field(default=Path("data"), validation_alias="SBM_DATA_DIR")
    cfbd_api_key: str | None = Field(default=None, validation_alias="CFBD_API_KEY")
    the_odds_api_key: str | None = Field(default=None, validation_alias="THE_ODDS_API_KEY")
    live_practice: bool = Field(default=True, validation_alias="SBM_LIVE_PRACTICE")
    spread_edge_points: float = 1.5
    total_edge_points: float = 1.5
    moneyline_min_ev: float = 0.03
    juice: int = -110


class LeagueParams:
    def __init__(
        self,
        *,
        hfa_points: float,
        elo_per_point: float,
        k: float,
        revert: float,
        base_elo: float = 1500.0,
        margin_sigma: float = 13.5,
        total_sigma: float = 10.5,
        league_avg_total: float,
        min_week_to_score: int = 1,
        rest_points_per_day: float = 0.15,
        rest_cap: float = 2.0,
        off_k: float = 0.15,
        def_k: float = 0.15,
    ) -> None:
        self.hfa_points = hfa_points
        self.elo_per_point = elo_per_point
        self.k = k
        self.revert = revert
        self.base_elo = base_elo
        self.margin_sigma = margin_sigma
        self.total_sigma = total_sigma
        self.league_avg_total = league_avg_total
        self.min_week_to_score = min_week_to_score
        self.rest_points_per_day = rest_points_per_day
        self.rest_cap = rest_cap
        self.off_k = off_k
        self.def_k = def_k


NFL_PARAMS = LeagueParams(
    hfa_points=2.4,
    elo_per_point=25.0,
    k=20.0,
    revert=0.75,
    league_avg_total=44.5,
    min_week_to_score=1,
    margin_sigma=13.8,
)

CFB_PARAMS = LeagueParams(
    hfa_points=2.7,
    elo_per_point=22.0,
    k=24.0,
    revert=0.45,
    league_avg_total=54.0,
    min_week_to_score=4,
    margin_sigma=16.5,
    total_sigma=13.0,
)


@dataclass(frozen=True)
class ResearchWindows:
    """Same split for NFL and CFB. Historical paper P&L never uses 2026."""

    warmup_start: int = 2015
    warmup_end: int = 2020
    search_start: int = 2021
    search_end: int = 2023
    holdout_start: int = 2024
    holdout_end: int = 2025
    hands_off: int = 2026

    def window_for(self, season: int) -> ResearchWindow | None:
        if self.warmup_start <= season <= self.warmup_end:
            return ResearchWindow.WARMUP
        if self.search_start <= season <= self.search_end:
            return ResearchWindow.SEARCH
        if self.holdout_start <= season <= self.holdout_end:
            return ResearchWindow.HOLDOUT
        if season == self.hands_off:
            return ResearchWindow.HANDS_OFF
        return None

    def record_historical_picks(self, season: int) -> bool:
        return self.search_start <= season <= self.holdout_end


RESEARCH_WINDOWS = ResearchWindows()


def params_for(league: League) -> LeagueParams:
    return NFL_PARAMS if league == League.NFL else CFB_PARAMS


def get_settings() -> Settings:
    return Settings()
