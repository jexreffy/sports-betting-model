from sbm.config import LeagueParams, params_for
from sbm.models.elo import EloBook
from sbm.models.totals import ScoringBook
from sbm.odds import margin_to_win_prob
from sbm.schema import Game, League, Prediction
from sbm.units import UnitBook, home_adjustment


class ModelEngine:
    def __init__(
        self,
        league: League,
        params: LeagueParams | None = None,
        units: UnitBook | None = None,
    ) -> None:
        self.league = league
        self.params = params or params_for(league)
        self.elo = EloBook(self.params)
        self.totals = ScoringBook(self.params)
        self.units = units

    def predict(self, game: Game) -> Prediction:
        adjustment, _label = home_adjustment(game, self.units, self.params)
        margin = self.elo.predicted_home_margin(game) + adjustment
        total = self.totals.predicted_total(game)
        return Prediction(
            game_id=game.game_id,
            predicted_home_margin=margin,
            predicted_total=total,
            home_win_prob=margin_to_win_prob(margin, self.params.margin_sigma),
        )

    def update(self, game: Game) -> None:
        self.elo.update(game)
        self.totals.update(game)
