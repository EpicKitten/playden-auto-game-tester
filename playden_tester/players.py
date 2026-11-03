"""How many people played each game of a list on Steam in the last 30 days, from SteamCharts, for a list of the games
still to test sorted by players.
"""
import re
import time
import urllib.error
import urllib.request

PAGE = "https://steamcharts.com/app/{app}"
# The "Last 30 Days" row of a game's page: average players at once, gain, % gain, peak players at once.
LAST_30_DAYS = re.compile(r'Last 30 Days</td>\s*<td[^>]*>([\d.,]+)</td>.*?<td class="right num italic">([\d,]+)</td>',
                          re.S)


def last_30_days(html):
    """{avg, peak} from a SteamCharts page, or None when it has no numbers for the last 30 days."""
    match = LAST_30_DAYS.search(html)
    return {"avg": float(match[1].replace(",", "")), "peak": int(match[2].replace(",", ""))} if match else None


def players(app, timeout=30):
    request = urllib.request.Request(PAGE.format(app=app), headers={"User-Agent": "Mozilla/5.0 (playden-auto-tester)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return last_30_days(response.read().decode("utf-8", "replace"))


def fill_players(apps, cache, say=print, pause=0.5, save=None):
    """Read each app's numbers into cache (app -> {avg, peak} or None, updated in place). SteamCharts answers 404, or
    500 again and again, for games it doesn't track; those count as having no numbers. save(cache) runs every 25."""
    for number, app in enumerate(apps, 1):
        for attempt in range(4):
            try:
                cache[str(app)] = players(app)
                break
            except urllib.error.HTTPError as error:
                if error.code == 404 or (error.code == 500 and attempt >= 1):
                    cache[str(app)] = None
                    break
                time.sleep(5 if error.code == 500 else 30 * (attempt + 1))
            except (OSError, ValueError) as error:
                say(f"[{app}] SteamCharts lookup failed: {error}")
                time.sleep(10)
        if number % 25 == 0:
            say(f"SteamCharts: {number}/{len(apps)}")
            if save:
                save(cache)
        time.sleep(pause)
    return cache
