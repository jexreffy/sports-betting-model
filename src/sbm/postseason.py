"""Published 2026 postseason times. Matchups are not known, so these are not games."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sbm.journal import slate_bounds
from sbm.predictions import kickoff_iso
from sbm.schema import League

CHICAGO = ZoneInfo("America/Chicago")
EASTERN = ZoneInfo("America/New_York")

# The book only tracks these four conferences, plus the CFP and the NFL bracket.
POSTSEASON_SEASON = 2026


@dataclass(frozen=True)
class PostseasonSlot:
    slot_id: str
    league: League
    round_name: str
    kickoff: datetime | None
    day_label: str | None
    venue: str | None
    sort_at: datetime

    def window_start(self):
        return slate_bounds(self.sort_at)[0]

    def kickoff_iso(self) -> str | None:
        if self.kickoff is None:
            return None
        return kickoff_iso(self.kickoff, self.league)


def _at(year: int, month: int, day: int, hour: int, minute: int, zone: ZoneInfo) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=zone)


def _day(year: int, month: int, day: int) -> datetime:
    """Noon Chicago, only so a day-only slot lands in the right Tuesday–Monday window."""
    return datetime(year, month, day, 12, tzinfo=CHICAGO)


def slots_for_season(season: int) -> list[PostseasonSlot]:
    if season != POSTSEASON_SEASON:
        return []
    et = EASTERN
    ct = CHICAGO
    slots = [
        PostseasonSlot(
            "big12-title",
            League.CFB,
            "Big 12 Championship",
            _at(2026, 12, 4, 19, 0, ct),
            None,
            "AT&T Stadium",
            _at(2026, 12, 4, 19, 0, ct),
        ),
        PostseasonSlot(
            "acc-title",
            League.CFB,
            "ACC Championship",
            _at(2026, 12, 5, 12, 0, et),
            None,
            "Charlotte",
            _at(2026, 12, 5, 12, 0, et),
        ),
        PostseasonSlot(
            "sec-title",
            League.CFB,
            "SEC Championship",
            _at(2026, 12, 5, 16, 0, et),
            None,
            "Atlanta",
            _at(2026, 12, 5, 16, 0, et),
        ),
        PostseasonSlot(
            "b1g-title",
            League.CFB,
            "Big Ten Championship",
            _at(2026, 12, 5, 20, 0, et),
            None,
            "Indianapolis",
            _at(2026, 12, 5, 20, 0, et),
        ),
        PostseasonSlot(
            "cfp-r1-1",
            League.CFB,
            "CFP First Round",
            _at(2026, 12, 18, 20, 0, et),
            None,
            None,
            _at(2026, 12, 18, 20, 0, et),
        ),
        PostseasonSlot(
            "cfp-r1-2",
            League.CFB,
            "CFP First Round",
            _at(2026, 12, 19, 12, 0, et),
            None,
            None,
            _at(2026, 12, 19, 12, 0, et),
        ),
        PostseasonSlot(
            "cfp-r1-3",
            League.CFB,
            "CFP First Round",
            _at(2026, 12, 19, 15, 30, et),
            None,
            None,
            _at(2026, 12, 19, 15, 30, et),
        ),
        PostseasonSlot(
            "cfp-r1-4",
            League.CFB,
            "CFP First Round",
            _at(2026, 12, 19, 19, 30, et),
            None,
            None,
            _at(2026, 12, 19, 19, 30, et),
        ),
        PostseasonSlot(
            "cfp-fiesta",
            League.CFB,
            "Fiesta Bowl",
            _at(2026, 12, 30, 19, 30, et),
            None,
            None,
            _at(2026, 12, 30, 19, 30, et),
        ),
        PostseasonSlot(
            "cfp-qf-1",
            League.CFB,
            "CFP Quarterfinal",
            _at(2027, 1, 1, 12, 0, et),
            None,
            None,
            _at(2027, 1, 1, 12, 0, et),
        ),
        PostseasonSlot(
            "cfp-qf-2",
            League.CFB,
            "CFP Quarterfinal",
            _at(2027, 1, 1, 16, 0, et),
            None,
            None,
            _at(2027, 1, 1, 16, 0, et),
        ),
        PostseasonSlot(
            "cfp-qf-3",
            League.CFB,
            "CFP Quarterfinal",
            _at(2027, 1, 1, 20, 0, et),
            None,
            None,
            _at(2027, 1, 1, 20, 0, et),
        ),
        PostseasonSlot(
            "cfp-orange",
            League.CFB,
            "Orange Bowl",
            _at(2027, 1, 14, 19, 30, et),
            None,
            None,
            _at(2027, 1, 14, 19, 30, et),
        ),
        PostseasonSlot(
            "cfp-sugar",
            League.CFB,
            "Sugar Bowl",
            _at(2027, 1, 15, 19, 30, et),
            None,
            None,
            _at(2027, 1, 15, 19, 30, et),
        ),
        PostseasonSlot(
            "cfp-title",
            League.CFB,
            "CFP National Championship",
            _at(2027, 1, 25, 19, 30, et),
            None,
            "Allegiant Stadium",
            _at(2027, 1, 25, 19, 30, et),
        ),
    ]
    wild_card = _day(2027, 1, 16)
    for index in range(1, 7):
        slots.append(
            PostseasonSlot(
                f"nfl-wc-{index}",
                League.NFL,
                "Wild Card",
                None,
                "Jan 16–18",
                None,
                wild_card,
            )
        )
    divisional = _day(2027, 1, 23)
    for index in range(1, 5):
        slots.append(
            PostseasonSlot(
                f"nfl-div-{index}",
                League.NFL,
                "Divisional",
                None,
                "Jan 23–24",
                None,
                divisional,
            )
        )
    title_day = _day(2027, 1, 31)
    slots.append(
        PostseasonSlot(
            "nfl-afc",
            League.NFL,
            "AFC Championship",
            None,
            "Sun Jan 31",
            None,
            title_day,
        )
    )
    slots.append(
        PostseasonSlot(
            "nfl-nfc",
            League.NFL,
            "NFC Championship",
            None,
            "Sun Jan 31",
            None,
            title_day,
        )
    )
    slots.append(
        PostseasonSlot(
            "nfl-sb",
            League.NFL,
            "Super Bowl LXI",
            None,
            "Sun Feb 14",
            "SoFi Stadium",
            _day(2027, 2, 14),
        )
    )
    return slots
