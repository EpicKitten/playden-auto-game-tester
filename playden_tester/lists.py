"""The lists of games still to test, written as Markdown for people to read: data/games-to-test.md in campaign order,
data/games-by-players.md sorted by Steam players in the last 30 days, and data/games-by-size.md smallest first.

A game is still to test when it is on the `library` list, has no test report on Playden's tracker or row in its
compatibility list, is not a multiplayer game with anti-cheat, and the campaign has not tested it yet.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .ports import SPARQL, STEAM_APP, USER_AGENT
from .storefeatures import DUALSENSE, DUALSHOCK, pad_rank

PUBLICATION_DATE = "P577"
RELEASE_API = "https://store.steampowered.com/api/appdetails?appids={app}&filters=release_date"
PADS = {DUALSENSE: "Yes", DUALSHOCK: "DualShock only"}
DUALSENSE_FIELD = {DUALSENSE: "yes", DUALSHOCK: "dualshock"}
CONTROLLER = {"full": "Full controller support", "partial": "Partial controller support"}

TO_TEST_INTRO = """\
These are the Steam games that still need testing on Playden. The list includes only Windows games with full or \
partial controller support, and it's in the order the tester will run them.

**Not on this list**

- Games that someone has already tested, either in a test report on \
[Playden's issue tracker](https://github.com/leolobato/playden-ps5/issues) or on its \
[compatibility list](https://github.com/leolobato/playden-ps5/blob/main/COMPATIBILITY.md).
- Multiplayer games with anti-cheat (Easy Anti-Cheat, BattlEye, VAC and similar). Their online play doesn't work \
under Playden. Games with a single-player mode stay on the list when their anti-cheat only applies online (VAC, \
FairFight, PunkBuster).

**Order**

Games are sorted by how many people played them on Steam in the last 30 days, most first, so testing them helps the most people. The numbers come from [SteamCharts](https://steamcharts.com). Games it has no numbers for come after the rest, sorted by how much disk space they need, smallest first. The size is what the game's Steam store page asks for; games whose page doesn't say come last. Games of the same size are sorted by the rest of this section.

Games with full controller support come before games with partial support, whose menus or some parts may need a \
mouse or keyboard. Each of those two groups is sorted first by its games' [ProtonDB](https://www.protondb.com) rating, which says how well they run on Linux \
through Proton. Platinum games come first, then Gold, Silver, Bronze and Borked. Games with too few reports for a \
rating (Pending) or no reports at all come last.

Within each rating:

1. Games that never came out on a console come first.
2. Next come games that were also released on Xbox or Nintendo consoles, but not on a PlayStation.
3. Then games released on older PlayStations (PS1 to PS3, PSP, Vita).
4. Games with a PS4 or PS5 version come last, since they already play on the PS5 without Playden.

Within each of those groups, games that support the DualSense controller come first, then games that support the \
DualShock, then the rest.

**Columns**

- **Size** is the disk space the game's Steam store page asks for.
- **Year** is the first release on any platform.
- **Steam app** is the game's ID on the Steam store: `https://store.steampowered.com/app/<ID>`.
- **DualSense** says whether Steam lists DualSense support.
- **Console versions** comes from Wikidata. A dash means none were found.
- **ProtonDB** is the game's rating on ProtonDB. A dash means ProtonDB has no reports for it.
- **Note** gives the controller support level, plus anything to watch for when retesting."""

BY_PLAYERS_COLUMNS = """\
**Columns**

- **Average players** is the average number of people playing at once over the last 30 days.
- **Peak players** is the most people playing at once in that time.
- **Test order** is the game's place in [games-to-test.md](games-to-test.md), the order the tester runs them in.
- **Steam app** is the game's ID on the Steam store: `https://store.steampowered.com/app/<ID>`."""


def wikidata_years(apps, batch=150, timeout=90):
    """{Steam app: first publication year} for the apps whose Wikidata item has a publication date."""
    found = {}
    apps = [str(app) for app in apps]
    for start in range(0, len(apps), batch):
        values = " ".join(f'"{app}"' for app in apps[start:start + batch])
        query = (f"SELECT ?app (MIN(YEAR(?date)) AS ?year) WHERE {{ VALUES ?app {{ {values} }} "
                 f"?item wdt:{STEAM_APP} ?app . ?item wdt:{PUBLICATION_DATE} ?date . }} GROUP BY ?app")
        request = urllib.request.Request(SPARQL, data=urllib.parse.urlencode({"query": query, "format": "json"}).encode(),
                                         headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for row in json.loads(response.read().decode("utf-8"))["results"]["bindings"]:
                found[int(row["app"]["value"])] = int(row["year"]["value"])
    return found


def steam_year(date):
    """The year of a Steam release date ("Jun 20, 2024", "14 Nov, 2011"), or None."""
    match = re.search(r"\b(19|20)\d\d\b", date or "")
    return int(match[0]) if match else None


def fill_years(apps, cache, say=print, pause=1.0):
    """Look up the release years of the apps not in cache yet ({"wikidata": {app: year}, "steam": {app: {...}}},
    updated in place): Wikidata's first publication date, and the release date on the Steam store."""
    wikidata, steam = cache.setdefault("wikidata", {}), cache.setdefault("steam", {})
    new = [app for app in apps if str(app) not in steam]
    if not new:
        return cache
    try:
        years = wikidata_years(new)
    except (OSError, ValueError, KeyError) as error:
        say(f"could not ask Wikidata for release years: {error}")
        years = {}
    wikidata.update({str(app): year for app, year in years.items()})
    for app in new:
        for attempt in range(5):
            try:
                with urllib.request.urlopen(RELEASE_API.format(app=app), timeout=30) as response:
                    entry = (json.loads(response.read()).get(str(app)) or {}).get("data") or {}
                date = (entry.get("release_date") or {})
                steam[str(app)] = {"year": steam_year(date.get("date")), "coming_soon": bool(date.get("coming_soon")),
                                   "date": date.get("date") or ""}
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 403, 502, 503):
                    raise
                say(f"store busy (HTTP {error.code}); waiting {60 * (attempt + 1)} s")
                time.sleep(60 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                say(f"[{app}] release date lookup failed: {error}")
                time.sleep(5)
        time.sleep(pause)
    return cache


def release_year(app, years):
    found = [y for y in ((years.get("wikidata") or {}).get(str(app)),
                         ((years.get("steam") or {}).get(str(app)) or {}).get("year")) if y]
    return min(found) if found else None


def still_to_test(games, skip, done):
    """The games of a `library` list still to test: not in skip (a set of apps) or done (apps the campaign tested,
    as strings; see campaign.done_apps), and with full or partial controller support."""
    return [g for g in games if g.get("controller") in CONTROLLER and g["app"] not in skip and str(g["app"]) not in done]


def note(game, state):
    entry = state.get(str(game["app"])) or {}
    text = CONTROLLER.get(game.get("controller"), "")
    if entry.get("status") == "error":
        text += f"; retest: {entry.get('detail') or 'the last run went wrong'}"
    return text


def _cell(text):
    return str(text).replace("|", "\\|")


def to_test_rows(games, years, features, sizes=None):
    """The rows of data/games-to-test.json: the list's rows plus DualSense support, release years and the disk
    space the store says the game needs (sizes: {app: GB})."""
    rows = []
    for g in games:
        rank = pad_rank((features.get(str(g["app"])) or {}).get("categories"))
        rows.append({**g, "dualsense": DUALSENSE_FIELD.get(rank, "no"), "release_year": release_year(g["app"], years),
                     "steam_year": ((years.get("steam") or {}).get(str(g["app"])) or {}).get("year"),
                     "size_gb": (sizes or {}).get(g["app"])})
    return rows


def size_text(gb):
    if not gb:
        return "–"
    return f"{gb * 1024:.0f} MB" if gb < 1 else f"{gb:g} GB"


def to_test_markdown(rows, total, ports, tiers, state):
    """data/games-to-test.md. rows are in campaign order; ports is {app: [console names]}, tiers {app: tier}."""
    lines = [f"# Games still to test ({len(rows)} of {total})", "", TO_TEST_INTRO, "",
             "| # | Game | Size | Year | Steam app | DualSense | Console versions | ProtonDB | Note |",
             "|---|---|---|---|---|---|---|---|---|"]
    for number, row in enumerate(rows, 1):
        tier = tiers.get(row["app"]) or "unknown"
        lines.append(f"| {number} | {_cell(row['title'].strip())} | {size_text(row.get('size_gb'))} | "
                     f"{row.get('release_year') or '–'} | {row['app']} | "
                     f"{PADS.get(_pad(row), '–')} | {', '.join(ports.get(row['app']) or []) or '–'} | "
                     f"{'–' if tier == 'unknown' else tier.capitalize()} | {note(row, state)} |")
    return "\n".join(lines) + "\n"


def _pad(row):
    return {"yes": DUALSENSE, "dualshock": DUALSHOCK}.get(row.get("dualsense"))


def by_size_markdown(rows, ports):
    """data/games-by-size.md: the rows of games-to-test (in campaign order) by the disk space they need, smallest
    first; games whose store page doesn't say go last, in test order."""
    order = {row["app"]: number for number, row in enumerate(rows, 1)}
    known = [row for row in rows if row.get("size_gb")]
    ranked = sorted(known, key=lambda row: row["size_gb"]) + [row for row in rows if not row.get("size_gb")]
    lines = [f"# Games still to test, by size ({len(rows)} games)", "",
             "The same games as [games-to-test.md](games-to-test.md), sorted by how much disk space each one needs, "
             "smallest first, so the most games get tested in the least time. To run a campaign in this order, use "
             "`campaign --players ''`.", "",
             "The size is what the game's Steam store page asks for, so the real install can differ. "
             f"{len(rows) - len(known)} of the games' pages don't say, so they're at the bottom, in test order.", "",
             "| # | Game | Size | Year | Steam app | DualSense | Console versions | Test order |",
             "|---|---|---|---|---|---|---|---|"]
    for number, row in enumerate(ranked, 1):
        lines.append(f"| {number} | {_cell(row['title'].strip())} | {size_text(row.get('size_gb'))} | "
                     f"{row.get('release_year') or '–'} | {row['app']} | {PADS.get(_pad(row), '–')} | "
                     f"{', '.join(ports.get(row['app']) or []) or '–'} | {order[row['app']]} |")
    return "\n".join(lines) + "\n"


def by_players_markdown(rows, players, ports, read_on):
    """data/games-by-players.md: the rows of games-to-test (in campaign order) by average players, most first; the
    games SteamCharts has no numbers for go last, in test order. players is {app (str): {avg, peak} or None}."""
    order = {row["app"]: number for number, row in enumerate(rows, 1)}
    known = [row for row in rows if players.get(str(row["app"]))]
    ranked = sorted(known, key=lambda row: -players[str(row["app"])]["avg"]) + [r for r in rows if r not in known]
    lines = [f"# Games still to test, by players ({len(rows)} games)", "",
             "The same games as [games-to-test.md](games-to-test.md), sorted by how many people played each one on "
             "Steam in the last 30 days. Popular games come first, so testing them helps the most people.", "",
             f"Player numbers come from [SteamCharts](https://steamcharts.com) and were read on {read_on}. SteamCharts "
             f"had no numbers for {len(rows) - len(known)} of the games, so they're at the bottom, in test order.", "",
             BY_PLAYERS_COLUMNS, "",
             "| # | Game | Average players | Peak players | Year | Steam app | DualSense | Console versions | Test order |",
             "|---|---|---|---|---|---|---|---|---|"]
    for number, row in enumerate(ranked, 1):
        p = players.get(str(row["app"]))
        avg, peak = (f"{p['avg']:,.0f}", f"{p['peak']:,}") if p else ("–", "–")
        lines.append(f"| {number} | {_cell(row['title'].strip())} | {avg} | {peak} | {row.get('release_year') or '–'} | "
                     f"{row['app']} | {PADS.get(_pad(row), '–')} | {', '.join(ports.get(row['app']) or []) or '–'} | "
                     f"{order[row['app']]} |")
    return "\n".join(lines) + "\n"
