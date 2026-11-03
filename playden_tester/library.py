"""Your Steam library as Playden caches it, and each game's controller support from the Steam store.

The cache is /data/playden/user/library-<SteamID>.cache (Playden src/library/cache.cpp). Only that file is read:
session.v1 beside it holds the Steam sign-in token.
"""
import json
import re
import struct
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import asdict, dataclass

USER = "/data/playden/user"
CACHE_NAME = re.compile(r"^library-(\d+)\.cache$")
MAGIC = b"PDLIB\0"
STEAM = 1
STORE_API = "https://store.steampowered.com/api/appdetails?appids={app}&l=english"
# The store's controller_support field only ever says "full"; partial support shows only as this category.
PARTIAL_CONTROLLER = 18


class LibraryError(Exception):
    pass


@dataclass
class OwnedGame:
    app: int
    title: str
    developer: str = ""
    description: str = ""
    playtime_minutes: int = 0
    demo: bool = False
    family_shared: bool = False
    controller: str = ""     # "full", "partial", "none" (Steam lists none), or "" before the store was asked
    platforms: str = ""      # e.g. "windows,mac"
    store_type: str = ""     # "game", "dlc", "demo", ...

    def as_dict(self):
        return asdict(self)


class _Reader:
    def __init__(self, data, offset, limit):
        self.data, self.offset, self.limit = data, offset, limit

    def number(self, count):
        if self.offset + count > self.limit:
            raise LibraryError("library cache ends early")
        value = int.from_bytes(self.data[self.offset:self.offset + count], "little")
        self.offset += count
        return value

    def string(self):
        size = self.number(4)
        if self.offset + size > self.limit:
            raise LibraryError("library cache ends early")
        value = self.data[self.offset:self.offset + size].decode("utf-8", "replace")
        self.offset += size
        return value


def parse_cache(data):
    """The Steam games in a library cache, as OwnedGame."""
    if len(data) < 12 or data[:6] != MAGIC or data[7] != 0:
        raise LibraryError("not a Playden library cache")
    schema = data[6]
    if not 1 <= schema <= 7:
        raise LibraryError(f"unknown library cache schema {schema}")
    if struct.unpack("<I", data[-4:])[0] != zlib.crc32(data[:-4]):
        raise LibraryError("library cache checksum does not match")
    r = _Reader(data, 8, len(data) - 4)
    r.string()          # account
    r.number(8)         # retrieved at
    if schema >= 3:
        r.number(1)     # metadata partial
    games = []
    for _ in range(r.number(4)):
        if schema >= 5:
            store, value = r.number(1), r.string()
        else:
            store, value = STEAM, str(r.number(4))
        title = r.string()
        r.string()      # artwork
        description = r.string()
        developer = r.string()
        playtime, demo, shared = 0, False, False
        if schema >= 2:
            flags = r.number(1)
            if flags & 1:
                playtime = r.number(8)
            if flags & 2:
                r.number(8)
            if flags & 4:
                r.number(8)
            demo, shared = bool(flags & 8), bool(flags & 16)
        if store == STEAM and value.isdigit():
            games.append(OwnedGame(int(value), title, developer, description, playtime, demo, shared))
    return games


def read_library(files):
    """The library of the account Playden has cached (the newest cache when there are several)."""
    caches = [e for e in files.list(USER) if CACHE_NAME.match(e["name"])]
    if not caches:
        raise LibraryError(f"no library cache in {USER}: open Playden and sign in to Steam first")
    newest = max(caches, key=lambda e: e["mtime"])
    return parse_cache(files.download(f"{USER}/{newest['name']}"))


def store_details(app, timeout=15):
    """controller support, platforms and type of one app from the public Steam store API."""
    request = urllib.request.Request(STORE_API.format(app=app), headers={"User-Agent": "playden-auto-tester"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        entry = json.load(response).get(str(app)) or {}
    if not entry.get("success"):
        return {"controller": "", "platforms": "", "store_type": "unlisted"}
    data = entry.get("data") or {}
    platforms = ",".join(name for name, yes in (data.get("platforms") or {}).items() if yes)
    partial = any(c.get("id") == PARTIAL_CONTROLLER for c in data.get("categories") or [])
    return {"controller": data.get("controller_support") or ("partial" if partial else "none"), "platforms": platforms,
            "store_type": data.get("type", ""), "short_description": data.get("short_description", "")}


def fill_store_details(games, cache, say=print, pause=1.6):
    """Ask the store about each game not in `cache` (app -> details, updated in place). The store allows about
    200 requests per 5 minutes; a 429 waits and retries."""
    todo = [g for g in games if str(g.app) not in cache]
    for number, game in enumerate(todo, 1):
        for attempt in range(5):
            try:
                cache[str(game.app)] = store_details(game.app)
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 403, 502, 503):
                    raise
                wait = 60 * (attempt + 1)
                say(f"store busy (HTTP {error.code}); waiting {wait} s")
                time.sleep(wait)
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                say(f"[{game.app}] store lookup failed: {error}")
                time.sleep(5)
        if number % 25 == 0:
            say(f"store: {number}/{len(todo)}")
        time.sleep(pause)
    for game in games:
        details = cache.get(str(game.app), {})
        game.controller = details.get("controller", "")
        game.platforms = details.get("platforms", "")
        game.store_type = details.get("store_type", "")
    return games
