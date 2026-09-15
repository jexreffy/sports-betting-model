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
}


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
    return " ".join(parts).lower()
