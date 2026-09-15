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
