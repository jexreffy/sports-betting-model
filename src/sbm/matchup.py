"""One matchup, priced three ways, plus each real meeting in a single season."""

from __future__ import annotations

from dataclasses import dataclass

from sbm.backtest import infer_current_week
from sbm.models.engine import ModelEngine
from sbm.odds import implied_to_american
from sbm.predictions import team_key
from sbm.schema import Game, League, Prediction
from sbm.teams import abbrev, aliases_for, display_name, team_face
from sbm.units import UnitBook, UnitWeek, favorite_side, unit_components

_NFL_STATS = (
    ("rush_off", "Rush EPA"),
    ("rush_allowed", "Rush EPA allowed"),
    ("pass_off", "Pass EPA"),
    ("pass_allowed", "Pass EPA allowed"),
    ("sack_off", "Sack rate"),
    ("sack_def", "Sack rate forced"),
)
_CFB_STATS = (
    ("line_yards", "Line yards"),
    ("stuff_def", "Stuff rate"),
    ("pass_success", "Pass success"),
    ("havoc_def", "Front-seven havoc"),
    ("talent", "Talent"),
)
_RATE_KEYS = {"sack_off", "sack_def", "stuff_def", "pass_success", "havoc_def"}


@dataclass(frozen=True)
class SitePrice:
    label: str
    spread: str
    total: str
    moneyline: str
    home_margin: float


@dataclass(frozen=True)
class Factor:
    label: str
    points: float


@dataclass(frozen=True)
class MeetingPrice:
    game: Game
    factors: list[Factor]
    margin: float


@dataclass(frozen=True)
class StatRow:
    label: str
    left: str
    right: str


@dataclass(frozen=True)
class MatchupView:
    league: League
    season: int
    week: int
    team_a: str
    team_b: str
    sites: list[SitePrice]
    stats: list[StatRow]
    meetings: list[MeetingPrice]


def resolve_team(league: League, query: str, games: list[Game]) -> str:
    """Match a typed name to one ingested team. Ambiguous names are an error."""
    token = query.strip()
    if not token:
        raise ValueError("Enter both teams")
    roster = sorted(
        {
            team
            for game in games
            if game.league == league
            for team in (game.home_team, game.away_team)
        }
    )
    if not roster:
        raise ValueError(f"No {league.value.upper()} teams ingested")
    lowered = token.lower()
    hits: list[str] = []
    for team in roster:
        names = {
            team.strip().lower(),
            abbrev(league, team).lower(),
            display_name(league, team).lower(),
        }
        names.update(alias.lower() for alias in aliases_for(league, team))
        if lowered in names:
            hits.append(team)
    unique: list[str] = []
    seen: set[str] = set()
    for team in hits:
        key = team_key(league, team)
        if key in seen:
            continue
        seen.add(key)
        unique.append(team)
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        raise ValueError(f"{query.strip()} matches more than one team")
    raise ValueError(f"Unknown team {query.strip()}")


def same_season_meetings(
    games: list[Game], league: League, season: int, team_a: str, team_b: str
) -> list[Game]:
    """Catalog games between the two teams in one season, earliest week first."""
    wanted = {team_key(league, team_a), team_key(league, team_b)}
    found = [
        game
        for game in games
        if game.league == league
        and game.season == season
        and {team_key(league, game.home_team), team_key(league, game.away_team)} == wanted
    ]
    found.sort(
        key=lambda game: (
            game.week,
            game.kickoff.isoformat() if game.kickoff else "",
            game.game_id,
        )
    )
    return found


def as_of_week(games: list[Game], league: League, season: int) -> int:
    """Current open week of the season, or its last week when the season is complete."""
    scoped = [game for game in games if game.league == league]
    inferred = infer_current_week(scoped, season=season)
    if inferred is None:
        return 1
    return inferred[1]


def engine_before(
    games: list[Game],
    league: League,
    season: int,
    week: int,
    units: UnitBook | None,
) -> ModelEngine:
    """Ratings from games strictly before this week. This week is not applied."""
    engine = ModelEngine(league, units=units)
    ordered = sorted(
        (game for game in games if game.league == league),
        key=lambda game: (
            game.season,
            game.week,
            game.kickoff.isoformat() if game.kickoff else "",
            game.game_id,
        ),
    )
    for game in ordered:
        if (game.season, game.week) < (season, week):
            engine.update(game)
    return engine


def margin_factors(engine: ModelEngine, game: Game) -> list[Factor]:
    """Pieces of the home margin. They sum to the pregame prediction."""
    elo = engine.elo.neutral_home_margin(game)
    hfa = 0.0 if game.is_neutral else engine.params.hfa_points
    rest = engine.elo.rest_adjustment(game)
    parts, capped, _label = unit_components(game, engine.units, engine.params)
    rows = [
        Factor("Elo", elo),
        Factor("Home field", hfa),
        Factor("Rest", rest),
        Factor("Run", parts["run"]),
        Factor("Pass", parts["pass"]),
        Factor("Talent", parts["talent"]),
    ]
    raw = parts["run"] + parts["pass"] + parts["talent"]
    if abs(raw - capped) > 1e-9:
        rows.append(Factor("Unit cap", capped - raw))
    return rows


def price_matchup(
    games: list[Game],
    league: League,
    season: int,
    team_a: str,
    team_b: str,
    units: UnitBook | None = None,
) -> MatchupView:
    """Hypothetical three-site prices, plus one pregame price per meeting that season.

    Synthetic games stay in memory. `games` is not modified.
    """
    if team_key(league, team_a) == team_key(league, team_b):
        raise ValueError("Pick two different teams")
    week = as_of_week(games, league, season)
    abstract = engine_before(games, league, season, week, units)
    sites = [
        _site(abstract, league, season, week, team_a, team_b, neutral=False),
        _site(abstract, league, season, week, team_b, team_a, neutral=False),
        _site(abstract, league, season, week, team_a, team_b, neutral=True),
    ]
    meetings: list[MeetingPrice] = []
    engines: dict[int, ModelEngine] = {}
    for game in same_season_meetings(games, league, season, team_a, team_b):
        engine = engines.get(game.week)
        if engine is None:
            engine = engine_before(games, league, game.season, game.week, units)
            engines[game.week] = engine
        pred = engine.predict(game)
        meetings.append(
            MeetingPrice(
                game=game,
                factors=margin_factors(engine, game),
                margin=pred.predicted_home_margin,
            )
        )
    return MatchupView(
        league=league,
        season=season,
        week=week,
        team_a=team_a,
        team_b=team_b,
        sites=sites,
        stats=_stats(abstract, units, league, season, week, team_a, team_b),
        meetings=meetings,
    )


def _site(
    engine: ModelEngine,
    league: League,
    season: int,
    week: int,
    home: str,
    away: str,
    *,
    neutral: bool,
) -> SitePrice:
    game = Game(
        game_id=f"hyp-{league.value}-{season}-{week}-{'n' if neutral else 'h'}-{away}-{home}",
        league=league,
        season=season,
        week=week,
        home_team=home,
        away_team=away,
        is_neutral=neutral,
    )
    pred = engine.predict(game)
    if neutral:
        label = "Neutral field"
    else:
        label = f"{team_face(league, home).display_name} at home"
    return SitePrice(
        label=label,
        spread=_spread(league, pred, away, home),
        total=f"{pred.predicted_total:.1f}",
        moneyline=_moneyline(league, pred, away, home),
        home_margin=pred.predicted_home_margin,
    )


def _spread(league: League, pred: Prediction, away: str, home: str) -> str:
    favorite, points = favorite_side(pred.predicted_home_margin, away, home)
    if favorite is None:
        return "Pick'em"
    return f"{team_face(league, favorite).abbrev} -{points:.1f}"


def _moneyline(league: League, pred: Prediction, away: str, home: str) -> str:
    away_prob = 1.0 - pred.home_win_prob
    home_name = team_face(league, home).abbrev
    away_name = team_face(league, away).abbrev
    return (
        f"{home_name} {pred.home_win_prob:.0%} ({_american(pred.home_win_prob)})"
        f" · {away_name} {away_prob:.0%} ({_american(away_prob)})"
    )


def _american(prob: float) -> str:
    if prob <= 0.0 or prob >= 1.0:
        return "—"
    return f"{implied_to_american(prob):+d}"


def _stats(
    engine: ModelEngine,
    units: UnitBook | None,
    league: League,
    season: int,
    week: int,
    team_a: str,
    team_b: str,
) -> list[StatRow]:
    left = units.profile_before(league, team_a, season, week) if units is not None else None
    right = units.profile_before(league, team_b, season, week) if units is not None else None
    rows = [
        StatRow(
            "Neutral-field favorability",
            f"{engine.elo.favorability(team_a, season):+.1f}",
            f"{engine.elo.favorability(team_b, season):+.1f}",
        )
    ]
    fields = _NFL_STATS if league == League.NFL else _CFB_STATS
    for key, label in fields:
        rows.append(StatRow(label, _stat_value(key, left), _stat_value(key, right)))
    return rows


def _stat_value(key: str, profile: UnitWeek | None) -> str:
    if profile is None:
        return "—"
    value = getattr(profile, key)
    if value is None:
        return "—"
    if key in _RATE_KEYS:
        return f"{value:.3f}"
    if key == "talent":
        return f"{value:.1f}"
    return f"{value:.2f}"
