from __future__ import annotations

from collections import defaultdict

from sbm.config import LeagueParams
from sbm.schema import Game


class EloBook:
    """Point-spread Elo. Updates only after a game is applied — never from future scores."""

    def __init__(self, params: LeagueParams) -> None:
        self.params = params
        self.ratings: dict[str, float] = defaultdict(lambda: params.base_elo)
        self._seen_seasons: dict[str, int] = {}

    def rating(self, team: str) -> float:
        return self.ratings[team]

    def maybe_revert(self, team: str, season: int) -> None:
        last = self._seen_seasons.get(team)
        if last is not None and season > last:
            current = self.ratings[team]
            self.ratings[team] = self.params.base_elo + self.params.revert * (
                current - self.params.base_elo
            )
        self._seen_seasons[team] = season

    def rest_adjustment(self, game: Game) -> float:
        if game.home_rest_days is None or game.away_rest_days is None:
            return 0.0
        delta = game.home_rest_days - game.away_rest_days
        adj = delta * self.params.rest_points_per_day
        return max(-self.params.rest_cap, min(self.params.rest_cap, adj))

    def predicted_home_margin(self, game: Game) -> float:
        self.maybe_revert(game.home_team, game.season)
        self.maybe_revert(game.away_team, game.season)
        hfa = 0.0 if game.is_neutral else self.params.hfa_points
        diff = self.ratings[game.home_team] - self.ratings[game.away_team]
        return diff / self.params.elo_per_point + hfa + self.rest_adjustment(game)

    def update(self, game: Game) -> None:
        if not game.is_final or game.home_margin is None:
            return
        pred = self.predicted_home_margin(game)
        error = game.home_margin - pred
        shift = self.params.k * (error / self.params.margin_sigma)
        # Cap so a blowout does not explode ratings
        shift = max(-self.params.k, min(self.params.k, shift))
        self.ratings[game.home_team] += shift
        self.ratings[game.away_team] -= shift
        self._seen_seasons[game.home_team] = game.season
        self._seen_seasons[game.away_team] = game.season
