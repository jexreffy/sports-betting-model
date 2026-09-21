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

    def _rating_for_season(self, team: str, season: int) -> float:
        last = self._seen_seasons.get(team)
        current = self.ratings[team]
        if last is not None and season > last:
            return self.params.base_elo + self.params.revert * (current - self.params.base_elo)
        return current

    def rest_adjustment(self, game: Game) -> float:
        if game.home_rest_days is None or game.away_rest_days is None:
            return 0.0
        delta = game.home_rest_days - game.away_rest_days
        adj = delta * self.params.rest_points_per_day
        return max(-self.params.rest_cap, min(self.params.rest_cap, adj))

    def neutral_home_margin(self, game: Game) -> float:
        """Elo gap in points. Home field and rest are not included."""
        diff = self._rating_for_season(game.home_team, game.season) - self._rating_for_season(
            game.away_team, game.season
        )
        return diff / self.params.elo_per_point

    def favorability(self, team: str, season: int) -> float:
        """Points versus an average opponent. No home field, no rest."""
        rating = self._rating_for_season(team, season)
        return (rating - self.params.base_elo) / self.params.elo_per_point

    def predicted_home_margin(self, game: Game) -> float:
        hfa = 0.0 if game.is_neutral else self.params.hfa_points
        diff = self._rating_for_season(game.home_team, game.season) - self._rating_for_season(
            game.away_team, game.season
        )
        return diff / self.params.elo_per_point + hfa + self.rest_adjustment(game)

    def update(self, game: Game) -> None:
        if not game.is_final or game.home_margin is None:
            return
        self.maybe_revert(game.home_team, game.season)
        self.maybe_revert(game.away_team, game.season)
        pred = self.predicted_home_margin(game)
        error = game.home_margin - pred
        shift = self.params.k * (error / self.params.margin_sigma)
        # Cap so a blowout does not explode ratings
        shift = max(-self.params.k, min(self.params.k, shift))
        self.ratings[game.home_team] += shift
        self.ratings[game.away_team] -= shift
        self._seen_seasons[game.home_team] = game.season
        self._seen_seasons[game.away_team] = game.season
