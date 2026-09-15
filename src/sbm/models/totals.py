from __future__ import annotations

from collections import defaultdict

from sbm.config import LeagueParams
from sbm.schema import Game


class ScoringBook:
    """Offensive / defensive scoring ratings in points vs league average."""

    def __init__(self, params: LeagueParams) -> None:
        self.params = params
        self.off: dict[str, float] = defaultdict(float)
        self.defense: dict[str, float] = defaultdict(float)
        self._seen_seasons: dict[str, int] = {}

    def maybe_revert(self, team: str, season: int) -> None:
        last = self._seen_seasons.get(team)
        if last is not None and season > last:
            self.off[team] *= self.params.revert
            self.defense[team] *= self.params.revert
        self._seen_seasons[team] = season

    def predicted_scores(self, game: Game) -> tuple[float, float]:
        self.maybe_revert(game.home_team, game.season)
        self.maybe_revert(game.away_team, game.season)
        avg = self.params.league_avg_total / 2.0
        hfa = 0.0 if game.is_neutral else self.params.hfa_points / 2.0
        home = avg + self.off[game.home_team] - self.defense[game.away_team] + hfa
        away = avg + self.off[game.away_team] - self.defense[game.home_team]
        return home, away

    def predicted_total(self, game: Game) -> float:
        home, away = self.predicted_scores(game)
        return home + away

    def update(self, game: Game) -> None:
        if not game.is_final or game.home_score is None or game.away_score is None:
            return
        pred_home, pred_away = self.predicted_scores(game)
        home_err = game.home_score - pred_home
        away_err = game.away_score - pred_away
        self.off[game.home_team] += self.params.off_k * home_err
        self.defense[game.away_team] -= self.params.def_k * home_err
        self.off[game.away_team] += self.params.off_k * away_err
        self.defense[game.home_team] -= self.params.def_k * away_err
        self._seen_seasons[game.home_team] = game.season
        self._seen_seasons[game.away_team] = game.season
