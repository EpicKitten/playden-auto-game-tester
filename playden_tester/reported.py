"""Games other people already reported on in Playden's issue tracker, or that Playden's compatibility list
(COMPATIBILITY.md) already covers, so a campaign can skip them.

A test report (label "test report") counts for a game of the list when it links the game's Steam store or SteamDB
page, or when its title, without the "[Test]" prefix, is the game's name. Bug reports do not count. A row of the
compatibility list counts when it links the game's store page. The whole list is kept in data/compatibility.json for
the dashboard, which shows games that are not in the library too. So are test reports on games nothing else knows:
they go in tested-by-others.json as well, where they change nothing for a campaign, which only tests library games.
"""
import json
import re
import urllib.error
import urllib.request

REPO = "leolobato/playden-ps5"
API = "https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}"
COMPATIBILITY = "https://api.github.com/repos/{repo}/contents/COMPATIBILITY.md"
GAME_LINK = re.compile(r"\[(.+)\]\((.+)\)")
IMPORTED = re.compile(r"\s*\([^)]*\bimported\)\s*$", re.I)
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


def _cells(line):
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def _dash(text):
    return "" if text in (None, "—", "-", "–") else text


def parse_compatibility(text):
    """The rows of COMPATIBILITY.md's games table: game, app (None without a Steam store link), url, status, kit,
    engine and notes. The kit is the Playden runtime kit the game was last checked on. Other tables are left out."""
    rows, columns = [], None
    for line in text.splitlines():
        if not line.startswith("|"):
            columns = None
            continue
        cells = _cells(line)
        if columns is None:
            columns = [cell.lower() for cell in cells] if cells[:1] == ["Game"] else []
        elif columns and len(cells) >= 2 and set(cells[0]) - set("-: "):
            fields = dict(zip(columns, cells))
            link = GAME_LINK.fullmatch(cells[0])
            name, url = link.groups() if link else (cells[0], "")
            app = APP_LINK.search(url)
            rows.append({"game": name, "app": int(app[1]) if app else None, "url": url, "status": cells[1],
                         "kit": _dash(fields.get("kit")), "notes": _dash(fields.get("notes")),
                         "engine": _dash(next((v for k, v in fields.items() if k.startswith("engine")), None))})
    return rows


def compatibility_games(text, games, repo=REPO):
    """{Steam app: [entry]} for the games of the list in the compatibility list, with its result."""
    apps = {int(g["app"]) for g in games}
    found = {}
    for row in parse_compatibility(text):
        if row["app"] in apps:
            found.setdefault(row["app"], []).append({"number": None, "title": f"COMPATIBILITY.md: {row['game']}",
                                                     "state": row["status"],
                                                     "url": f"https://github.com/{repo}/blob/main/COMPATIBILITY.md"})
    return found


def _key(text):
    return "".join(c for c in text.lower() if c.isalnum())


def compatibility_key(name):
    """A compatibility row's name, for comparing with library titles: "Blur (GOG, imported)" is "blur"."""
    return _key(IMPORTED.sub("", name))


def _entry(issue):
    return {"number": issue["number"], "title": issue.get("title") or "", "state": issue.get("state"),
            "url": issue.get("html_url")}


def _report_name(title):
    return TEST_PREFIX.sub("", title).strip("<> ")


def _is_report(issue):
    return LABEL in [label["name"] for label in issue.get("labels", [])]


def reported_games(issues, games):
    """{Steam app: [issue, ...]} for the games (dicts with app and title) that have a test report."""
    apps = {str(g["app"]) for g in games}
    by_name = {_key(g["title"]): str(g["app"]) for g in games}
    found = {}
    for issue in issues:
        if not _is_report(issue):
            continue
        title = issue.get("title") or ""
        matched = {app for app in APP_LINK.findall(title + "\n" + (issue.get("body") or "")) if app in apps}
        name = by_name.get(_key(_report_name(title)))
        if name:
            matched.add(name)
        for app in matched:
            found.setdefault(int(app), []).append(_entry(issue))
    return found


def unplaced_reports(issues, found):
    """The test reports reported_games matched to no game. Returns {Steam app: name}, {Steam app: [issue, ...]} for
    those that link a store or SteamDB page, and the number that link none. The first link is the game under test;
    reports that matched a game are left out, as their other links can be to anything."""
    placed = {entry["number"] for entries in found.values() for entry in entries}
    names, reports, unlinked = {}, {}, 0
    for issue in issues:
        if not _is_report(issue) or issue["number"] in placed:
            continue
        title = issue.get("title") or ""
        link = APP_LINK.search(title + "\n" + (issue.get("body") or ""))
        if not link:
            unlinked += 1
            continue
        app = int(link[1])
        names.setdefault(app, _report_name(title) or str(app))
        reports.setdefault(app, []).append(_entry(issue))
    return names, reports, unlinked


def load_apps(path):
    """The Steam apps in a list of games (JSON rows with an "app"), such as one 'reported' writes."""
    return {row["app"] for row in json.loads(path.read_text(encoding="utf-8"))}
