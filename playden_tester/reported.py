"""Games other people already reported on in Playden's issue tracker, so a campaign can skip them.

A test report (label "test report") counts for a game of the list when it links the game's Steam store or SteamDB
page, or when its title, without the "[Test]" prefix, is the game's name. Bug reports do not count.
"""
import json
import re
import urllib.request

REPO = "leolobato/playden-ps5"
API = "https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}"
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


def load_reported(path):
    """The Steam apps in a list written by the 'reported' command."""
    return {row["app"] for row in json.loads(path.read_text(encoding="utf-8"))}
