"""Games other people already reported on in Playden's issue tracker, or that Playden's compatibility list
(COMPATIBILITY.md) already covers, so a campaign can skip them.

A test report (label "test report") counts for a game of the list when it links the game's Steam store or SteamDB
page, or when its title, without the "[Test]" prefix, is the game's name. Bug reports do not count. A row of the
compatibility list counts when it links the game's store page.
"""
import json
import re
import urllib.error
import urllib.request

REPO = "leolobato/playden-ps5"
API = "https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}"
COMPATIBILITY = "https://api.github.com/repos/{repo}/contents/COMPATIBILITY.md"
COMPATIBILITY_ROW = re.compile(r"^\|\s*\[([^\]]+)\]\(https://store\.steampowered\.com/app/(\d+)[^)]*\)\s*\|\s*([^|]+?)\s*\|", re.M)
LABEL = "test report"
APP_LINK = re.compile(r"(?:store\.steampowered\.com|steamdb\.info)/app/(\d+)")
TEST_PREFIX = re.compile(r"^\[+\s*test(?:\s+report)?\s*\]+\s*", re.I)


class ReportedError(Exception):
    pass


def fetch_issues(repo=REPO, token=None, timeout=30, max_pages=50):
    """Every issue of the repository, open and closed (pull requests left out)."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "playden-auto-tester"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    issues = []
    for page in range(1, max_pages + 1):
        request = urllib.request.Request(API.format(repo=repo, page=page), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                rows = json.loads(response.read().decode("utf-8"))
        except OSError as error:
            raise ReportedError(f"could not read {repo}'s issues: {error}") from error
        issues += [row for row in rows if "pull_request" not in row]
        if len(rows) < 100:
            break
    return issues


def fetch_compatibility(repo=REPO, token=None, timeout=30):
    """The text of the repository's COMPATIBILITY.md ("" when it has none)."""
    headers = {"Accept": "application/vnd.github.raw", "User-Agent": "playden-auto-tester"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(COMPATIBILITY.format(repo=repo), headers=headers),
                                    timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return ""
        raise ReportedError(f"could not read {repo}'s compatibility list: {error}") from error
    except OSError as error:
        raise ReportedError(f"could not read {repo}'s compatibility list: {error}") from error


def compatibility_games(text, games, repo=REPO):
    """{Steam app: [entry]} for the games of the list in the compatibility list, with its result."""
    apps = {int(g["app"]) for g in games}
    found = {}
    for name, app, result in COMPATIBILITY_ROW.findall(text):
        if int(app) in apps:
            found.setdefault(int(app), []).append({"number": None, "title": f"COMPATIBILITY.md: {name}",
                                                   "state": result,
                                                   "url": f"https://github.com/{repo}/blob/main/COMPATIBILITY.md"})
    return found


def _key(text):
    return "".join(c for c in text.lower() if c.isalnum())


def reported_games(issues, games):
    """{Steam app: [issue, ...]} for the games (dicts with app and title) that have a test report."""
    apps = {str(g["app"]) for g in games}
    by_name = {_key(g["title"]): str(g["app"]) for g in games}
    found = {}
    for issue in issues:
        if LABEL not in [label["name"] for label in issue.get("labels", [])]:
            continue
        title = issue.get("title") or ""
        matched = {app for app in APP_LINK.findall(title + "\n" + (issue.get("body") or "")) if app in apps}
        name = by_name.get(_key(TEST_PREFIX.sub("", title).strip("<> ")))
        if name:
            matched.add(name)
        for app in matched:
            found.setdefault(int(app), []).append({"number": issue["number"], "title": title,
                                                   "state": issue.get("state"), "url": issue.get("html_url")})
    return found


def load_apps(path):
    """The Steam apps in a list of games (JSON rows with an "app"), such as one 'reported' writes."""
    return {row["app"] for row in json.loads(path.read_text(encoding="utf-8"))}
