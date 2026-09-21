"""Location / nickname aliases so the board search can find a game."""

from __future__ import annotations

from sbm.schema import League

NFL_ALIASES: dict[str, list[str]] = {
    "ARI": ["arizona", "cardinals", "cards", "az"],
    "ATL": ["atlanta", "falcons"],
    "BAL": ["baltimore", "ravens"],
    "BUF": ["buffalo", "bills"],
    "CAR": ["carolina", "panthers"],
    "CHI": ["chicago", "bears"],
    "CIN": ["cincinnati", "bengals"],
    "CLE": ["cleveland", "browns"],
    "DAL": ["dallas", "cowboys"],
    "DEN": ["denver", "broncos"],
    "DET": ["detroit", "lions"],
    "GB": ["green bay", "packers", "pack"],
    "HOU": ["houston", "texans"],
    "IND": ["indianapolis", "colts"],
    "JAX": ["jacksonville", "jaguars", "jags", "jac"],
    "KC": ["kansas city", "chiefs"],
    "LA": ["los angeles rams", "rams", "lar", "st louis"],
    "LAC": ["los angeles chargers", "chargers", "bolts", "san diego", "sd"],
    "LV": ["las vegas", "raiders", "oakland"],
    "MIA": ["miami", "dolphins", "fins"],
    "MIN": ["minnesota", "vikings", "vikes"],
    "NE": ["new england", "patriots", "pats"],
    "NO": ["new orleans", "saints"],
    "NYG": ["new york giants", "giants", "ny giants"],
    "NYJ": ["new york jets", "jets", "ny jets"],
    "PHI": ["philadelphia", "eagles", "philly"],
    "PIT": ["pittsburgh", "steelers", "pitt"],
    "SEA": ["seattle", "seahawks", "hawks"],
    "SF": ["san francisco", "49ers", "niners", "sfo"],
    "TB": ["tampa bay", "buccaneers", "bucs", "tampa"],
    "TEN": ["tennessee", "titans"],
    "WAS": ["washington", "commanders", "skins", "football team"],
}

# Extra CFB nicknames keyed by CFBD school name (lowercase).
CFB_NICKNAMES: dict[str, list[str]] = {
    "air force": ["falcons"],
    "akron": ["zips"],
    "alabama": ["crimson tide", "bama", "tide"],
    "app state": ["appalachian state", "mountaineers", "app"],
    "arizona": ["wildcats"],
    "arizona state": ["sun devils", "asu"],
    "arkansas": ["razorbacks", "hogs"],
    "army": ["black knights"],
    "auburn": ["tigers", "war eagle"],
    "baylor": ["bears"],
    "boise state": ["broncos"],
    "boston college": ["eagles", "bc"],
    "bowling green": ["falcons", "bgsu"],
    "byu": ["cougars", "brigham young"],
    "california": ["golden bears", "cal", "bears"],
    "central michigan": ["chippewas", "cmu"],
    "cincinnati": ["bearcats"],
    "clemson": ["tigers"],
    "coastal carolina": ["chanticleers", "chants"],
    "colorado": ["buffaloes", "buffs"],
    "colorado state": ["rams"],
    "delaware": ["blue hens"],
    "duke": ["blue devils"],
    "east carolina": ["pirates", "ecu"],
    "florida": ["gators"],
    "florida state": ["seminoles", "noles", "fsu"],
    "fresno state": ["bulldogs"],
    "georgia": ["bulldogs", "dawgs", "uga"],
    "georgia tech": ["yellow jackets", "jackets", "gt"],
    "houston": ["cougars"],
    "illinois": ["fighting illini", "illini"],
    "indiana": ["hoosiers"],
    "iowa": ["hawkeyes"],
    "iowa state": ["cyclones"],
    "james madison": ["dukes", "jmu"],
    "kansas": ["jayhawks"],
    "kansas state": ["wildcats", "k-state", "kstate"],
    "kentucky": ["wildcats"],
    "liberty": ["flames"],
    "louisville": ["cardinals"],
    "lsu": ["tigers", "louisiana state"],
    "maryland": ["terrapins", "terps"],
    "memphis": ["tigers"],
    "miami": ["hurricanes", "the u", "canes"],
    "michigan": ["wolverines"],
    "michigan state": ["spartans", "msu"],
    "minnesota": ["golden gophers", "gophers"],
    "mississippi state": ["bulldogs", "miss state"],
    "missouri": ["tigers", "mizzou"],
    "navy": ["midshipmen", "mids"],
    "nc state": ["wolfpack", "north carolina state"],
    "nebraska": ["cornhuskers", "huskers"],
    "north carolina": ["tar heels", "heels", "unc"],
    "northwestern": ["wildcats"],
    "notre dame": ["fighting irish", "irish", "nd"],
    "ohio state": ["buckeyes", "osu"],
    "oklahoma": ["sooners", "ou"],
    "oklahoma state": ["cowboys", "pokes", "ok state"],
    "ole miss": ["rebels", "mississippi"],
    "oregon": ["ducks"],
    "oregon state": ["beavers"],
    "penn state": ["nittany lions", "lions", "psu"],
    "pittsburgh": ["panthers", "pitt"],
    "purdue": ["boilermakers"],
    "rutgers": ["scarlet knights"],
    "south carolina": ["gamecocks"],
    "south florida": ["bulls", "usf"],
    "smu": ["mustangs"],
    "stanford": ["cardinal"],
    "syracuse": ["orange"],
    "tcu": ["horned frogs", "frogs"],
    "tennessee": ["volunteers", "vols"],
    "texas": ["longhorns", "horns"],
    "texas a&m": ["aggies", "a&m", "tamu"],
    "texas tech": ["red raiders"],
    "tulane": ["green wave"],
    "ucla": ["bruins"],
    "usc": ["trojans", "southern california"],
    "utah": ["utes"],
    "vanderbilt": ["commodores", "dores", "vandy"],
    "virginia": ["cavaliers", "cavs", "uva"],
    "virginia tech": ["hokies", "vt"],
    "wake forest": ["demon deacons", "deacs"],
    "washington": ["huskies"],
    "washington state": ["cougars", "wazu", "wsu"],
    "west virginia": ["mountaineers", "wvu"],
    "western kentucky": ["hilltoppers", "wku"],
    "wisconsin": ["badgers"],
    "arkansas state": ["red wolves"],
    "ball state": ["cardinals"],
    "buffalo": ["bulls"],
    "charlotte": ["49ers"],
    "eastern michigan": ["eagles"],
    "florida atlantic": ["owls"],
    "florida international": ["panthers"],
    "georgia southern": ["eagles"],
    "georgia state": ["panthers"],
    "hawai'i": ["rainbow warriors", "hawaii"],
    "jacksonville state": ["gamecocks"],
    "kennesaw state": ["owls"],
    "kent state": ["golden flashes"],
    "louisiana": ["ragin cajuns", "cajuns"],
    "louisiana tech": ["bulldogs"],
    "marshall": ["thundering herd"],
    "massachusetts": ["minutemen", "umass"],
    "miami (oh)": ["redhawks"],
    "middle tennessee": ["blue raiders"],
    "missouri state": ["bears"],
    "nevada": ["wolf pack"],
    "new mexico": ["lobos"],
    "new mexico state": ["aggies"],
    "north dakota state": ["bison"],
    "north texas": ["mean green"],
    "northern illinois": ["huskies"],
    "ohio": ["bobcats"],
    "old dominion": ["monarchs"],
    "rice": ["owls"],
    "sacramento state": ["hornets"],
    "sam houston": ["bearkats"],
    "san diego state": ["aztecs"],
    "san josé state": ["spartans", "san jose state"],
    "south alabama": ["jaguars"],
    "southern miss": ["golden eagles"],
    "temple": ["owls"],
    "texas state": ["bobcats"],
    "toledo": ["rockets"],
    "troy": ["trojans"],
    "tulsa": ["golden hurricane"],
    "uab": ["blazers"],
    "ucf": ["knights"],
    "uconn": ["huskies"],
    "ul monroe": ["warhawks"],
    "unlv": ["rebels"],
    "utep": ["miners"],
    "utsa": ["roadrunners"],
    "utah state": ["aggies"],
    "western michigan": ["broncos"],
    "wyoming": ["cowboys"],
}

NFL_CONFERENCE: dict[str, str] = {
    "BUF": "AFC",
    "MIA": "AFC",
    "NE": "AFC",
    "NYJ": "AFC",
    "BAL": "AFC",
    "CIN": "AFC",
    "CLE": "AFC",
    "PIT": "AFC",
    "HOU": "AFC",
    "IND": "AFC",
    "JAX": "AFC",
    "TEN": "AFC",
    "DEN": "AFC",
    "KC": "AFC",
    "LAC": "AFC",
    "LV": "AFC",
    "DAL": "NFC",
    "NYG": "NFC",
    "PHI": "NFC",
    "WAS": "NFC",
    "CHI": "NFC",
    "DET": "NFC",
    "GB": "NFC",
    "MIN": "NFC",
    "ATL": "NFC",
    "CAR": "NFC",
    "NO": "NFC",
    "TB": "NFC",
    "ARI": "NFC",
    "LA": "NFC",
    "SEA": "NFC",
    "SF": "NFC",
}

NFL_DISPLAY: dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

# Short codes for CFBD school names (3 letters when unique; 4 only when that is the usual code).
CFB_ABBREV: dict[str, str] = {
    "air force": "AFA",
    "akron": "AKR",
    "alabama": "ALA",
    "app state": "APP",
    "arizona": "ARZ",
    "arizona state": "ASU",
    "arkansas": "ARK",
    "arkansas state": "ARST",
    "army": "ARMY",
    "auburn": "AUB",
    "byu": "BYU",
    "ball state": "BALL",
    "baylor": "BAY",
    "boise state": "BSU",
    "boston college": "BC",
    "bowling green": "BGSU",
    "buffalo": "BUF",
    "california": "CAL",
    "central michigan": "CMU",
    "charlotte": "CLT",
    "cincinnati": "CIN",
    "clemson": "CLE",
    "coastal carolina": "CCU",
    "colorado": "COL",
    "colorado state": "CSU",
    "delaware": "DEL",
    "duke": "DUK",
    "east carolina": "ECU",
    "eastern michigan": "EMU",
    "florida": "FLA",
    "florida atlantic": "FAU",
    "florida international": "FIU",
    "florida state": "FSU",
    "fresno state": "FRE",
    "georgia": "UGA",
    "georgia southern": "GAS",
    "georgia state": "GSU",
    "georgia tech": "GT",
    "hawai'i": "HAW",
    "houston": "HOU",
    "illinois": "ILL",
    "indiana": "IND",
    "iowa": "IOW",
    "iowa state": "ISU",
    "jacksonville state": "JSU",
    "james madison": "JMU",
    "kansas": "KAN",
    "kansas state": "KSU",
    "kennesaw state": "KEN",
    "kent state": "KNT",
    "kentucky": "UK",
    "lsu": "LSU",
    "liberty": "LIB",
    "louisiana": "UL",
    "louisiana tech": "LT",
    "louisville": "LOU",
    "marshall": "MRH",
    "maryland": "MD",
    "massachusetts": "UMS",
    "memphis": "MEM",
    "miami": "MIA",
    "miami (oh)": "MOH",
    "michigan": "MICH",
    "michigan state": "MSU",
    "middle tennessee": "MTS",
    "minnesota": "MIN",
    "mississippi state": "MSST",
    "missouri": "MIZ",
    "missouri state": "MOS",
    "nc state": "NCS",
    "navy": "NAV",
    "nebraska": "NEB",
    "nevada": "NEV",
    "new mexico": "UNM",
    "new mexico state": "NMS",
    "north carolina": "UNC",
    "north dakota state": "NDS",
    "north texas": "UNT",
    "northern illinois": "NIU",
    "northwestern": "NW",
    "notre dame": "ND",
    "ohio": "OHI",
    "ohio state": "OSU",
    "oklahoma": "OU",
    "oklahoma state": "OKS",
    "old dominion": "ODU",
    "ole miss": "MIS",
    "oregon": "ORE",
    "oregon state": "ORS",
    "penn state": "PSU",
    "pittsburgh": "PIT",
    "purdue": "PUR",
    "rice": "RIC",
    "rutgers": "RUT",
    "smu": "SMU",
    "sacramento state": "SAC",
    "sam houston": "SHS",
    "san diego state": "SDS",
    "san josé state": "SJS",
    "south alabama": "USA",
    "south carolina": "SC",
    "south florida": "USF",
    "southern miss": "USM",
    "stanford": "STA",
    "syracuse": "SYR",
    "tcu": "TCU",
    "temple": "TEM",
    "tennessee": "TEN",
    "texas": "TEX",
    "texas a&m": "TAM",
    "texas state": "TXS",
    "texas tech": "TTU",
    "toledo": "TOL",
    "troy": "TRY",
    "tulane": "TLN",
    "tulsa": "TLS",
    "uab": "UAB",
    "ucf": "UCF",
    "ucla": "UCLA",
    "uconn": "CON",
    "ul monroe": "ULM",
    "unlv": "UNLV",
    "usc": "USC",
    "utep": "UTEP",
    "utsa": "UTSA",
    "utah": "UTH",
    "utah state": "USU",
    "vanderbilt": "VAN",
    "virginia": "UVA",
    "virginia tech": "VT",
    "wake forest": "WF",
    "washington": "WAS",
    "washington state": "WSU",
    "west virginia": "WVU",
    "western kentucky": "WKU",
    "western michigan": "WMU",
    "wisconsin": "WIS",
    "wyoming": "WYO",
}


def _cfb_key(team: str) -> str:
    return team.strip().lower().replace("san jose state", "san josé state")


def nfl_conference(team: str) -> str | None:
    code = abbrev(League.NFL, team)
    return NFL_CONFERENCE.get(code)


P4_CONFERENCES = frozenset({"B1G", "SEC", "ACC", "Big 12"})

_CFB_CONFERENCE_ALIASES = {
    "big ten": "B1G",
    "b1g": "B1G",
    "big ten conference": "B1G",
    "sec": "SEC",
    "southeastern": "SEC",
    "southeastern conference": "SEC",
    "acc": "ACC",
    "atlantic coast": "ACC",
    "atlantic coast conference": "ACC",
    "big 12": "Big 12",
    "big12": "Big 12",
    "big 12 conference": "Big 12",
}


def normalize_cfb_conference(raw: object | None) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    key = " ".join(text.lower().replace("-", " ").split())
    if key in _CFB_CONFERENCE_ALIASES:
        return _CFB_CONFERENCE_ALIASES[key]
    return text


def is_p4_conference(conference: str | None) -> bool:
    return conference in P4_CONFERENCES


# Exact CFBD school names for the current Predictions roster.
CFB_P4_CONFERENCE: dict[str, str] = {
    "Ohio State": "B1G",
    "Indiana": "B1G",
    "USC": "B1G",
    "Penn State": "B1G",
    "Iowa": "B1G",
    "Washington": "B1G",
    "Oregon": "B1G",
    "UCLA": "B1G",
    "Michigan": "B1G",
    "Nebraska": "B1G",
    "Illinois": "B1G",
    "Northwestern": "B1G",
    "Maryland": "B1G",
    "Wisconsin": "B1G",
    "Minnesota": "B1G",
    "Michigan State": "B1G",
    "Purdue": "B1G",
    "Rutgers": "B1G",
    "Ole Miss": "SEC",
    "Georgia": "SEC",
    "Texas": "SEC",
    "Florida": "SEC",
    "Alabama": "SEC",
    "LSU": "SEC",
    "Mississippi State": "SEC",
    "Vanderbilt": "SEC",
    "Texas A&M": "SEC",
    "Tennessee": "SEC",
    "Kentucky": "SEC",
    "Auburn": "SEC",
    "Missouri": "SEC",
    "Oklahoma": "SEC",
    "South Carolina": "SEC",
    "Arkansas": "SEC",
    "Miami": "ACC",
    "Louisville": "ACC",
    "SMU": "ACC",
    "Duke": "ACC",
    "Wake Forest": "ACC",
    "Pittsburgh": "ACC",
    "Virginia Tech": "ACC",
    "California": "ACC",
    "Virginia": "ACC",
    "Clemson": "ACC",
    "North Carolina": "ACC",
    "NC State": "ACC",
    "Georgia Tech": "ACC",
    "Syracuse": "ACC",
    "Florida State": "ACC",
    "Boston College": "ACC",
    "Stanford": "ACC",
    # Independent, but Predictions files them with the ACC (scheduling agreement).
    "Notre Dame": "ACC",
    "BYU": "Big 12",
    "Texas Tech": "Big 12",
    "Utah": "Big 12",
    "Houston": "Big 12",
    "Arizona State": "Big 12",
    "Kansas State": "Big 12",
    "Arizona": "Big 12",
    "West Virginia": "Big 12",
    "Cincinnati": "Big 12",
    "Iowa State": "Big 12",
    "Oklahoma State": "Big 12",
    "Colorado": "Big 12",
    "Baylor": "Big 12",
    "TCU": "Big 12",
    "UCF": "Big 12",
    "Kansas": "Big 12",
}


def cfb_p4_conference(team: str) -> str | None:
    return CFB_P4_CONFERENCE.get(team.strip())


NFL_PRIMARY: dict[str, str] = {
    "ARI": "#97233F",
    "ATL": "#A71930",
    "BAL": "#241773",
    "BUF": "#00338D",
    "CAR": "#0085CA",
    "CHI": "#0B162A",
    "CIN": "#FB4F14",
    "CLE": "#311D00",
    "DAL": "#003594",
    "DEN": "#FB4F14",
    "DET": "#0076B6",
    "GB": "#203731",
    "HOU": "#03202F",
    "IND": "#002C5F",
    "JAX": "#006778",
    "KC": "#E31837",
    "LA": "#003594",
    "LAC": "#0080C6",
    "LV": "#A5ACAF",
    "MIA": "#008E97",
    "MIN": "#4F2683",
    "NE": "#002244",
    "NO": "#D3BC8D",
    "NYG": "#0B2265",
    "NYJ": "#125740",
    "PHI": "#004C54",
    "PIT": "#FFB612",
    "SEA": "#002244",
    "SF": "#AA0000",
    "TB": "#D50A0A",
    "TEN": "#0C2340",
    "WAS": "#5A1414",
}

NFL_ESPN_SLUG: dict[str, str] = {
    "LA": "lar",
    "WAS": "wsh",
}

CFB_ESPN_ID: dict[str, int] = {
    "Alabama": 333,
    "Arizona": 12,
    "Arizona State": 9,
    "Arkansas": 8,
    "Auburn": 2,
    "Baylor": 239,
    "Boston College": 103,
    "BYU": 252,
    "California": 25,
    "Cincinnati": 2132,
    "Clemson": 228,
    "Colorado": 38,
    "Duke": 150,
    "Florida": 57,
    "Florida State": 52,
    "Georgia": 61,
    "Georgia Tech": 59,
    "Houston": 248,
    "Illinois": 356,
    "Indiana": 84,
    "Iowa": 2294,
    "Iowa State": 66,
    "Kansas": 2305,
    "Kansas State": 2306,
    "Kentucky": 96,
    "Louisville": 97,
    "LSU": 99,
    "Maryland": 120,
    "Miami": 2390,
    "Michigan": 130,
    "Michigan State": 127,
    "Minnesota": 135,
    "Mississippi State": 344,
    "Missouri": 142,
    "NC State": 152,
    "Nebraska": 158,
    "North Carolina": 153,
    "Northwestern": 77,
    "Notre Dame": 87,
    "Ohio State": 194,
    "Oklahoma": 201,
    "Oklahoma State": 197,
    "Ole Miss": 145,
    "Oregon": 2483,
    "Penn State": 213,
    "Pittsburgh": 221,
    "Purdue": 2509,
    "Rutgers": 164,
    "SMU": 2567,
    "South Carolina": 2579,
    "Stanford": 24,
    "Syracuse": 183,
    "TCU": 2628,
    "Tennessee": 2633,
    "Texas": 251,
    "Texas A&M": 245,
    "Texas Tech": 2641,
    "UCF": 2116,
    "UCLA": 26,
    "USC": 30,
    "Utah": 254,
    "Vanderbilt": 238,
    "Virginia": 258,
    "Virginia Tech": 259,
    "Wake Forest": 154,
    "Washington": 264,
    "West Virginia": 277,
    "Wisconsin": 275,
}

# School primaries for the Predictions CFB roster (same role as NFL_PRIMARY).
CFB_PRIMARY: dict[str, str] = {
    "Alabama": "#9E1B32",
    "Arizona": "#CC0033",
    "Arizona State": "#8C1D40",
    "Arkansas": "#9D2235",
    "Auburn": "#0C2340",
    "Baylor": "#154734",
    "Boston College": "#8A100B",
    "BYU": "#002E5D",
    "California": "#003262",
    "Cincinnati": "#E00122",
    "Clemson": "#F56600",
    "Colorado": "#CFB87C",
    "Duke": "#003087",
    "Florida": "#0021A5",
    "Florida State": "#782F40",
    "Georgia": "#BA0C2F",
    "Georgia Tech": "#B3A369",
    "Houston": "#C8102E",
    "Illinois": "#E84A27",
    "Indiana": "#990000",
    "Iowa": "#FFCD00",
    "Iowa State": "#C8102E",
    "Kansas": "#0051BA",
    "Kansas State": "#512888",
    "Kentucky": "#0033A0",
    "Louisville": "#AD0000",
    "LSU": "#461D7C",
    "Maryland": "#E03A3E",
    "Miami": "#F47321",
    "Michigan": "#00274C",
    "Michigan State": "#18453B",
    "Minnesota": "#7A0019",
    "Mississippi State": "#660000",
    "Missouri": "#F1B82D",
    "NC State": "#CC0000",
    "Nebraska": "#E41C38",
    "North Carolina": "#7BAFD4",
    "Northwestern": "#4E2A84",
    "Notre Dame": "#0C2340",
    "Ohio State": "#BB0000",
    "Oklahoma": "#841617",
    "Oklahoma State": "#FF7300",
    "Ole Miss": "#CE1126",
    "Oregon": "#154733",
    "Penn State": "#041E42",
    "Pittsburgh": "#003594",
    "Purdue": "#CEB888",
    "Rutgers": "#CC0033",
    "SMU": "#C8102E",
    "South Carolina": "#73000A",
    "Stanford": "#8C1515",
    "Syracuse": "#F76900",
    "TCU": "#4D1979",
    "Tennessee": "#FF8200",
    "Texas": "#BF5700",
    "Texas A&M": "#500000",
    "Texas Tech": "#CC0000",
    "UCF": "#BA9B37",
    "UCLA": "#2D68C4",
    "USC": "#990000",
    "Utah": "#CC0000",
    "Vanderbilt": "#866D4B",
    "Virginia": "#232D4B",
    "Virginia Tech": "#630031",
    "Wake Forest": "#9E7E38",
    "Washington": "#4B2E83",
    "West Virginia": "#002855",
    "Wisconsin": "#C5050C",
}

CONFERENCE_PRIMARY: dict[str, str] = {
    "AFC": "#00338D",
    "NFC": "#9B2743",
    "B1G": "#0088CE",
    "SEC": "#9D2235",
    "ACC": "#013CA6",
    "Big 12": "#C41230",
}


def logo_url(league: League, team: str) -> str | None:
    if league == League.NFL:
        code = abbrev(league, team)
        slug = NFL_ESPN_SLUG.get(code, code.lower())
        return f"https://a.espncdn.com/i/teamlogos/nfl/500/{slug}.png"
    espn_id = CFB_ESPN_ID.get(team.strip())
    if espn_id is None:
        return None
    return f"https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png"


TTUN_DISPLAY = "The Team Up North"
TTUN_ABBREV = "TTUN"
TTUN_MARK = "❌"


def _is_ttun(league: League, team: str) -> bool:
    return league == League.CFB and _cfb_key(team) == "michigan"


def render_display_name(league: League, team: str) -> str:
    if _is_ttun(league, team):
        return TTUN_DISPLAY
    return display_name(league, team)


def render_abbrev(league: League, team: str) -> str:
    if _is_ttun(league, team):
        return TTUN_ABBREV
    return abbrev(league, team)


def render_logo_url(league: League, team: str) -> str | None:
    if _is_ttun(league, team):
        return None
    return logo_url(league, team)


def render_logo_mark(league: League, team: str) -> str | None:
    if _is_ttun(league, team):
        return TTUN_MARK
    return None


def team_color(league: League, team: str, conference: str | None = None) -> str | None:
    if league == League.NFL:
        return NFL_PRIMARY.get(abbrev(league, team))
    school = CFB_PRIMARY.get(team.strip())
    if school:
        return school
    if conference and conference in CONFERENCE_PRIMARY:
        return CONFERENCE_PRIMARY[conference]
    mapped = cfb_p4_conference(team)
    if mapped:
        return CONFERENCE_PRIMARY.get(mapped)
    return None


def abbrev(league: League, team: str) -> str:
    raw = team.strip()
    if league == League.NFL:
        code = raw.upper()
        if code in NFL_DISPLAY:
            return code
        lowered = raw.lower()
        for key, names in NFL_ALIASES.items():
            if lowered == key.lower() or lowered in names:
                return key
        return code
    mapped = CFB_ABBREV.get(_cfb_key(raw))
    if mapped:
        return mapped
    compact = "".join(ch for ch in raw.upper() if ch.isalnum())
    return compact[:3] if compact else raw


def display_name(league: League, team: str) -> str:
    raw = team.strip()
    if league == League.NFL:
        return NFL_DISPLAY.get(abbrev(league, raw), raw)
    nick = CFB_NICKNAMES.get(_cfb_key(raw), [])
    if nick:
        nickname = nick[0] if nick[0][:1].isdigit() else nick[0].title()
        if nickname.lower() not in raw.lower():
            return f"{raw} {nickname}"
    return raw


def abbrev_side(league: League, team_or_side: str) -> str:
    token = team_or_side.strip().lower()
    if token in {"over", "under"}:
        return token
    return abbrev(league, team_or_side)


def matchup_abbrev(league: League, away_team: str, home_team: str) -> str:
    return f"{abbrev(league, away_team)}@{abbrev(league, home_team)}"


def book_ticket_label(
    *,
    column: str,
    league: League,
    week: int,
    away_team: str,
    home_team: str,
    team_or_side: str,
    market: str,
) -> str:
    matchup = matchup_abbrev(league, away_team, home_team)
    side = abbrev_side(league, team_or_side)
    return (
        f"{column.title()} · {league.value.upper()} w{week} "
        f"{matchup} {side} {market}"
    )


def aliases_for(league: League, team: str) -> list[str]:
    raw = team.strip()
    key = raw.lower()
    extra: list[str] = []
    if league == League.NFL:
        extra = list(NFL_ALIASES.get(raw.upper(), []))
        extra.append(raw)
    else:
        extra = list(CFB_NICKNAMES.get(key, []))
        extra.append(raw)
        extra.extend(key.replace("&", " ").replace("-", " ").split())
    return extra


def search_blob(league: League, *teams: str) -> str:
    parts: list[str] = []
    for team in teams:
        parts.extend(aliases_for(league, team))
        parts.append(abbrev(league, team))
        parts.append(display_name(league, team))
    return " ".join(parts).lower()
