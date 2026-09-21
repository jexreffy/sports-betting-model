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
    spread_edge_points: float = 1.5
    total_edge_points: float = 1.5
    moneyline_min_ev: float = 0.03
    juice: int = -110
    noisy_edge_points: float = 8.0


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
        run_weight: float = 8.0,
        pass_weight: float = 0.0,
        talent_weight: float = 0.5,
        unit_cap: float = 4.0,
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
        self.run_weight = run_weight
        self.pass_weight = pass_weight
        self.talent_weight = talent_weight
        self.unit_cap = unit_cap


_LEAGUE_PARAM_FIELDS = (
    "hfa_points",
    "elo_per_point",
    "k",
    "revert",
    "base_elo",
    "margin_sigma",
    "total_sigma",
    "league_avg_total",
    "min_week_to_score",
    "rest_points_per_day",
    "rest_cap",
    "off_k",
    "def_k",
    "run_weight",
    "pass_weight",
    "talent_weight",
    "unit_cap",
)


def copy_league_params(params: LeagueParams, **overrides: float) -> LeagueParams:
    data = {name: getattr(params, name) for name in _LEAGUE_PARAM_FIELDS}
    data.update(overrides)
    return LeagueParams(**data)


# Unit weights are the 2021–2023 search. Pass landed at zero. Not refit on 2026.
NFL_PARAMS = LeagueParams(
    hfa_points=2.4,
    elo_per_point=25.0,
    k=20.0,
    revert=0.75,
    league_avg_total=44.5,
    min_week_to_score=1,
    margin_sigma=13.8,
    run_weight=8.0,
    pass_weight=0.0,
    talent_weight=0.0,
    unit_cap=4.0,
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
    run_weight=8.0,
    pass_weight=0.0,
    talent_weight=0.5,
    unit_cap=4.0,
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
