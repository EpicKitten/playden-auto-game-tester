"""What the Steam store says about each game of a list beyond controller support: its feature categories (which
pads it supports, multiplayer, VAC) and the anti-cheat its store page declares, so a campaign can test DualSense
games first and skip multiplayer games with anti-cheat. Games with a single-player mode whose anti-cheat only
matters online are still tested.

Anti-cheat comes from four places: the store page's anti-cheat notice, Steam's Steam Deck or SteamOS result
"unsupported anti-cheat", the "Valve Anti-Cheat enabled" category, and AreWeAntiCheatYet's list (by Steam app ID).
"""
import json
import re
import time
import urllib.error
import urllib.request

CATEGORIES_API = "https://store.steampowered.com/api/appdetails?appids={app}&filters=categories"
STORE_PAGE = "https://store.steampowered.com/app/{app}/?l=english"
AREWEANTICHEATYET = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/HEAD/games.json"
# The store page asks for a birth date before showing mature games; these cookies answer it.
AGE_COOKIES = "birthtime=0; wants_mature_content=1; lastagecheckage=1-0-1990"

DUALSENSE, DUALSHOCK, NO_PAD = 0, 1, 2  # campaign order: DualSense games first
MULTIPLAYER = {"Multi-player", "Online PvP", "Online Co-op", "MMO", "PvP", "Co-op", "Cross-Platform Multiplayer"}
VAC = "Valve Anti-Cheat enabled"
NOTICE = re.compile(r'class="anticheat_name">(.*?)</div>', re.S)
DECK_ANTICHEAT = "UnsupportedAntiCheat"
# These act on online play only (bans, server checks), so a single-player mode still starts under Playden.
ONLINE_ONLY = {"VAC", "FairFight", "PunkBuster"}


class StoreFeaturesError(Exception):
    pass


def _get(url, timeout=30, cookies=None):
    headers = {"User-Agent": "Mozilla/5.0 (playden-auto-tester)"}
    if cookies:
        headers["Cookie"] = cookies
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def page_flags(html):
    """(anti-cheat names from the store page's notice, whether a Steam Deck/SteamOS result says unsupported
    anti-cheat)."""
    notice = [re.sub(r"<[^>]+>", "", name).split(" - ")[0].strip() for name in NOTICE.findall(html)]
    return [name for name in notice if name], DECK_ANTICHEAT in html


def store_features(app):
    """{categories, notice, deck_anticheat} of one app from the store."""
    entry = json.loads(_get(CATEGORIES_API.format(app=app))).get(str(app)) or {}
    categories = [c["description"] for c in (entry.get("data") or {}).get("categories", [])]
    notice, deck = page_flags(_get(STORE_PAGE.format(app=app), cookies=AGE_COOKIES))
    return {"categories": categories, "notice": notice, "deck_anticheat": deck}


def fill_features(apps, cache, say=print, pause=1.0):
    """Ask the store about each app not in `cache` (app -> features, updated in place); a 429 waits and retries."""
    todo = [app for app in apps if str(app) not in cache]
    for number, app in enumerate(todo, 1):
        for attempt in range(5):
            try:
                cache[str(app)] = store_features(app)
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 403, 502, 503):
                    raise
                wait = 60 * (attempt + 1)
                say(f"store busy (HTTP {error.code}); waiting {wait} s")
                time.sleep(wait)
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                say(f"[{app}] store lookup failed: {error}")
                time.sleep(5)
        if number % 25 == 0:
            say(f"store: {number}/{len(todo)}")
        time.sleep(pause)
    return cache


def fetch_areweanticheatyet(timeout=60):
    """{Steam app: [anti-cheat names]} from AreWeAntiCheatYet."""
    try:
        rows = json.loads(_get(AREWEANTICHEATYET, timeout=timeout))
    except (OSError, ValueError) as error:
        raise StoreFeaturesError(f"could not read AreWeAntiCheatYet: {error}") from error
    found = {}
    for row in rows:
        steam = str((row.get("storeIds") or {}).get("steam") or "")
        if steam.isdigit() and row.get("anticheats"):
            found[int(steam)] = list(row["anticheats"])
    return found


def pad_rank(categories):
    categories = set(categories or [])
    if "DualSense Controller Support" in categories:
        return DUALSENSE
    return DUALSHOCK if "DualShock Controller Support" in categories else NO_PAD


def _name(name):
    return "VAC" if name.lower().startswith(("vac", "valve anti-cheat")) else name


def anticheats(features, listed=()):
    """The anti-cheat one game has, by name; listed is what AreWeAntiCheatYet says."""
    names = []
    for name in [*(features.get("notice") or []), *(["VAC"] if VAC in (features.get("categories") or []) else []),
                 *listed]:
        if _name(name) not in names:
            names.append(_name(name))
    if features.get("deck_anticheat") and not names:
        names.append("unknown (Steam Deck: unsupported anti-cheat)")
    return names


def playable_alone(row):
    """True for a row whose single-player mode is worth testing: its anti-cheat only applies online."""
    # Steam files "<game> - Multiplayer" apps as single-player too, but they hold no campaign.
    return (bool(row.get("single_player")) and set(row["anticheats"]) <= ONLINE_ONLY
            and not row["title"].lower().endswith("multiplayer"))


def multiplayer_anticheat(games, cache, awacy):
    """Rows for the multiplayer games of the list that have anti-cheat, leaving out the ones playable alone."""
    rows = []
    for game in games:
        features = cache.get(str(game["app"])) or {}
        categories = features.get("categories") or []
        names = anticheats(features, awacy.get(game["app"], ()))
        if names and MULTIPLAYER & set(categories):
            rows.append({"app": game["app"], "title": game["title"].strip(), "anticheats": names,
                         "single_player": "Single-player" in categories, "categories": categories})
    return [row for row in rows if not playable_alone(row)]


def load_pads(path):
    """{Steam app: pad rank} from a features file written by the 'features' command."""
    return {int(app): pad_rank(f.get("categories")) for app, f in json.loads(path.read_text(encoding="utf-8")).items()}
