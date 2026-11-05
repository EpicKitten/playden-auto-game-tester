"""How much disk space each game needs, from the minimum requirements on its Steam store page ("Storage: 4 GB
available space", "Hard Drive Space: 20 GB"). Campaigns test the smallest games first: they download fastest.

The store states what the publisher wrote, so it is close to, not exactly, what Playden downloads (Batman: Arkham
Origins says 20 GB; Playden's page says 19.6 GB).
"""
import json
import re
import time
import urllib.error
import urllib.request

STORE_API = "https://store.steampowered.com/api/appdetails?appids={app}&l=english"
SPACE = re.compile(r"(?:storage|hard\s*drive|hard\s*disk|hdd|disk\s*space|free\s*space|drive\s*space|space)[^:]{0,30}:"
                   r"\s*(?:at\s*least\s*)?(\d+(?:[.,]\d+)?)\s*(KB|MB|GB|TB)", re.IGNORECASE)
UNITS = {"kb": 1 / 1048576, "mb": 1 / 1024, "gb": 1, "tb": 1024}


def install_size_gb(requirements):
    """The disk space in GB from a store page's requirements (HTML, or {"minimum": HTML, ...}), or None."""
    if isinstance(requirements, dict):
        requirements = requirements.get("minimum") or requirements.get("recommended") or ""
    text = re.sub(r"<[^>]+>", " ", requirements or "")
    match = SPACE.search(text)
    if not match:
        return None
    return round(float(match[1].replace(",", ".")) * UNITS[match[2].lower()], 4)


def fill_sizes(apps, cache, say=print, pause=1.6, save=None):
    """Look up the apps not in cache yet (app (str) -> GB or None, updated in place). The store allows about 200
    requests per 5 minutes; a 429 waits and retries. save(cache) runs every 25 games."""
    todo = [app for app in apps if str(app) not in cache]
    for number, app in enumerate(todo, 1):
        for attempt in range(5):
            try:
                with urllib.request.urlopen(STORE_API.format(app=app), timeout=30) as response:
                    entry = (json.loads(response.read()).get(str(app)) or {}).get("data") or {}
                cache[str(app)] = install_size_gb(entry.get("pc_requirements"))
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 403, 502, 503):
                    raise
                say(f"store busy (HTTP {error.code}); waiting {60 * (attempt + 1)} s")
                time.sleep(60 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                say(f"[{app}] size lookup failed: {error}")
                time.sleep(5)
        if number % 25 == 0:
            say(f"sizes: {number}/{len(todo)}")
            if save:
                save(cache)
        time.sleep(pause)
    return cache


def load_sizes(path):
    """{app (int): GB} from a file written by 'sizes'; games with no size are left out."""
    return {int(app): gb for app, gb in json.loads(path.read_text(encoding="utf-8")).items() if gb}
