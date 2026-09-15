from __future__ import annotations

from typing import Protocol

from sbm.schema import Game


class LineProvider(Protocol):
    """Market lines for a slate. Swap implementations without changing pick math."""

    name: str

    def attach_lines(self, games: list[Game]) -> list[Game]:
        """Return games with spread/total/ML fields filled from this provider."""
        ...


class PassthroughProvider:
    """Use lines already on the Game (nflverse close or CFBD consensus)."""

    name = "passthrough"

    def attach_lines(self, games: list[Game]) -> list[Game]:
        return games


class NflverseProvider:
    name = "nflverse"

    def attach_lines(self, games: list[Game]) -> list[Game]:
        return list(games)


class CfbdProvider:
    name = "cfbd"

    def attach_lines(self, games: list[Game]) -> list[Game]:
        return games


class TheOddsApiProvider:
    """Reserved for a 2027 live-odds hook. Not implemented in v1."""

    name = "the_odds_api"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def attach_lines(self, games: list[Game]) -> list[Game]:
        raise NotImplementedError(
            "TheOddsApiProvider is a stub. Set lines via nflverse/CFBD ingest, "
            "or implement attach_lines() when you add a THE_ODDS_API_KEY."
        )


def default_provider() -> LineProvider:
    return PassthroughProvider()
