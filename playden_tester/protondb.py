"""How well each game of a list runs on Linux through Proton, from ProtonDB's community ratings, so a campaign can
test the games that run best under a compatibility layer first.
"""
import json
import time
import urllib.error
import urllib.request

SUMMARY = "https://www.protondb.com/api/v1/reports/summaries/{app}.json"
# Campaign order: best rated first; "pending" (too few reports for a rating) and games ProtonDB doesn't know last.
TIERS = ["platinum", "gold", "silver", "bronze", "borked"]
UNRATED = len(TIERS)


class ProtonDBError(Exception):
    pass


def summary(app, timeout=30):
    """ProtonDB's summary of one app ({tier, score, total, confidence, ...}), or None when it has no reports."""
    request = urllib.request.Request(SUMMARY.format(app=app), headers={"User-Agent": "Mozilla/5.0 (playden-auto-tester)"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def fetch_summaries(apps, say=print, pause=0.3):
    """{Steam app: summary or None}; a busy server waits and retries."""
    found = {}
    for app in apps:
        for attempt in range(4):
            try:
                found[app] = summary(app)
                break
            except urllib.error.HTTPError as error:
                say(f"ProtonDB busy (HTTP {error.code}); waiting {20 * (attempt + 1)} s")
                time.sleep(20 * (attempt + 1))
            except (OSError, ValueError) as error:
                say(f"[{app}] ProtonDB lookup failed: {error}")
                time.sleep(5)
        else:
            raise ProtonDBError(f"could not read ProtonDB's rating of {app}")
        time.sleep(pause)
    return found


def tier_rank(tier):
    return TIERS.index(tier) if tier in TIERS else UNRATED


def load_tiers(path):
    """{Steam app: tier rank} from a list written by the 'protondb' command."""
    return {row["app"]: tier_rank(row["tier"]) for row in json.loads(path.read_text(encoding="utf-8"))}
