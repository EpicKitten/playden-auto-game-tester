"""Which games of a list also came out on consoles, from Wikidata (platforms of the item with the Steam app ID), so a
campaign can test the games with no console version first: a PS4 or PS5 version plays on the PS5 without Playden.
"""
import json
import urllib.parse
import urllib.request

SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "playden-auto-tester/0.1 (https://github.com/EpicKitten/playden-auto-game-tester)"
STEAM_APP = "P1733"
PLATFORM = "P400"

PLAYSTATION = {"Q5014725": "PlayStation 4", "Q63184502": "PlayStation 5"}
OLD_PLAYSTATION = {"Q10683": "PlayStation 3", "Q10680": "PlayStation 2", "Q10677": "PlayStation",
                   "Q188808": "PlayStation Vita", "Q170325": "PlayStation Portable"}
OTHER_CONSOLES = {
    "Q13361286": "Xbox One", "Q98973368": "Xbox Series X/S", "Q48263": "Xbox 360", "Q132020": "Xbox",
    "Q19610114": "Nintendo Switch", "Q122761124": "Nintendo Switch 2", "Q56942": "Wii U", "Q8079": "Wii",
    "Q182172": "GameCube", "Q184839": "Nintendo 64", "Q203597": "Nintendo 3DS", "Q170323": "Nintendo DS",
    "Q188642": "Game Boy Advance", "Q184198": "Dreamcast", "Q200912": "Sega Saturn",
}
# Campaign order: no console version first, then other consoles only, then any PlayStation release, and games
# already on PS4 or PS5 (which play on the PS5 without Playden) last.
NO_PORT, OTHER_PORT, OLD_PLAYSTATION_PORT, PLAYSTATION_PORT = 0, 1, 2, 3


class PortsError(Exception):
    pass


def fetch_platforms(apps, batch=150, timeout=90):
    """{Steam app: set of platform QIDs} for the apps that have a Wikidata item."""
    found = {}
    apps = [str(app) for app in apps]
    for start in range(0, len(apps), batch):
        values = " ".join(f'"{app}"' for app in apps[start:start + batch])
        query = (f"SELECT ?app ?platform WHERE {{ VALUES ?app {{ {values} }} ?item wdt:{STEAM_APP} ?app . "
                 f"OPTIONAL {{ ?item wdt:{PLATFORM} ?platform . }} }}")
        request = urllib.request.Request(SPARQL, data=urllib.parse.urlencode({"query": query, "format": "json"}).encode(),
                                         headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                rows = json.loads(response.read().decode("utf-8"))["results"]["bindings"]
        except (OSError, ValueError, KeyError) as error:
            raise PortsError(f"could not ask Wikidata: {error}") from error
        for row in rows:
            platforms = found.setdefault(int(row["app"]["value"]), set())
            if "platform" in row:
                platforms.add(row["platform"]["value"].rsplit("/", 1)[-1])
    return found


def console_ports(platforms):
    """(rank, console names) for one game's platform QIDs."""
    new = [PLAYSTATION[q] for q in PLAYSTATION if q in platforms]
    old = [OLD_PLAYSTATION[q] for q in OLD_PLAYSTATION if q in platforms]
    others = [OTHER_CONSOLES[q] for q in OTHER_CONSOLES if q in platforms]
    rank = (PLAYSTATION_PORT if new else OLD_PLAYSTATION_PORT if old else OTHER_PORT if others else NO_PORT)
    return rank, new + old + others


def load_ranks(path):
    """{Steam app: rank} from a list written by the 'ports' command."""
    return {row["app"]: row["rank"] for row in json.loads(path.read_text(encoding="utf-8"))}
