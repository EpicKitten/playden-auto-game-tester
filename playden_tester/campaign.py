"""Test a list of Steam games one by one: download through Playden if needed, test, collect logs, uninstall.

Progress lives in <out>/campaign.json, so a campaign that stops (console restart, a game that would not close)
goes on where it was when it is run again.
"""
import json
import re
import shutil
import time
from dataclasses import asdict
from pathlib import Path

from . import catalog
from .capture import CaptureError
from .console import HOMEBREW, LOGS, PLAYDEN, LaunchError
from .filemanager import FileManagerError
from .logs import LogCollector
from .playden_ui import DownloadFailed, NotInLibrary, UIError, same_name
from .report import RunWriter
from .runner import LAUNCH_FAILED, STUCK, Runner
from .webaccess import WebAccessError

SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(KB|MB|GB|TB)", re.IGNORECASE)
UNITS = {"kb": 1 / 1048576, "mb": 1 / 1024, "gb": 1, "tb": 1024}


def slug(text):
    """A folder name from a game's name: "BioShock™ 2" -> "bioshock-2"."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "game"


def size_gb(text):
    match = SIZE.search(text or "")
    return float(match.group(1).replace(",", ".")) * UNITS[match.group(2).lower()] if match else None


class Campaign:
    def __init__(self, console, ui, capture, settings, out, meta, say=print, keep=False, max_gb=None,
                 reserve_gb=15.0, reports=None, web=None):
        self.console, self.ui, self.files = console, ui, console.files
        self.capture = capture
        # A folder per game in reports: its screenshot and Playden's report zip from web (a WebAccess).
        self.reports, self.web = Path(reports) if reports else None, web
        self.settings, self.say, self.keep, self.max_gb = settings, say, keep, max_gb
        self.reserve_gb = reserve_gb  # free space always left on the console
        self.out = Path(out)
        self.writer = RunWriter(self.out, meta, resume=True)
        self.runner = Runner(console, settings, say=say, capture=capture, shots=self.out)
        self.logs = LogCollector(self.files)
        self.state_path = self.out / "campaign.json"
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {}
        self.library = None  # every owned game (library cache), to predict Library search results

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=1, ensure_ascii=False), encoding="utf-8")

    def mark(self, game, **fields):
        entry = self.state.setdefault(str(game.app), {"app": game.app, "title": game.title})
        entry.update(fields, updated=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.save()

    def titles(self):
        return {e["name"] for e in self.files.list(HOMEBREW) if e["type"] == "d" and e["name"].startswith("FAKE")}

    def installed_title(self, game):
        """The game's PS5 title, by the name in its param.json. Not by title logs: Playden reuses the IDs of
        uninstalled titles and their old logs stay, so FAKE78012 held Half-Life 2 with Balatro's log."""
        for title in catalog.games(self.files, read_logs=False):
            if same_name(title.name, game.title):
                return title.title
        return None

    def playden_front(self):
        """Playden open, on a screen with its tabs."""
        for attempt in range(2):
            if not self.console.is_running(PLAYDEN):
                self.console.launch(PLAYDEN)
                time.sleep(10)
            for _ in range(6):
                lines, _, _ = self.ui.read(1.0)
                # The tabs show through a sheet, a dialog or the keyboard, but do not take R1 while one is open.
                if self.ui.home_visible(lines) and not self.ui.overlay_open(lines):
                    return
                self.ui.press("circle", gap=1.0)
            if attempt == 0:
                # Running but not in front (suspended behind the PS5's Home, as Playden 0.10 is after a game):
                # launching it again does not bring it back, its tile on the PS5's Home does.
                self.say("Playden is running but not on screen; opening it from the PS5's Home")
                if not self.ui.open_from_ps_home():
                    try:
                        self.console.close(PLAYDEN)
                    except LaunchError as error:
                        raise UIError(f"Playden is not on screen and could not be closed: {error}") from None
                    time.sleep(3)
        raise UIError("Playden's tabs are not on screen")

    def evictable(self):
        """Games this campaign tested that are still installed, oldest first: what can go to make room."""
        entries = [e for e in self.state.values() if e.get("ps5_title") and e.get("uninstalled") is not True
                   and e.get("status") not in (None, "testing", "error", "skipped", "deferred")
                   and not e.get("uninstall_error")]
        titles = self.titles()
        return sorted((e for e in entries if e["ps5_title"] in titles), key=lambda e: e.get("updated", ""))

    def make_room(self, game, need_gb, free_gb):
        """Uninstall tested games until need_gb fits with reserve_gb left free. The free space afterwards, read
        again from the game's page; None when it cannot fit."""
        for entry in self.evictable():
            self.say(f"[{game.app}] {game.title}: needs {need_gb:.1f} GB, {free_gb:.1f} GB free; "
                     f"uninstalling tested {entry['title']}")
            self.ui.press("circle")
            self.playden_front()
            try:
                self.ui.uninstall(entry["title"], self.files, entry["app"], entry["ps5_title"])
                entry.update(uninstalled=True, evicted_for=game.app, updated=time.strftime("%Y-%m-%d %H:%M:%S"))
            except UIError as error:
                entry.update(uninstall_error=str(error))
            self.save()
            self.playden_front()
            lines = self.ui.open_game(game, self.library)
            free_gb = free_space(lines) or free_gb
            if free_gb - self.reserve_gb >= need_gb:
                return free_gb
        return None

    def download(self, game):
        """Install the game through Playden, making room first when it does not fit, and wait until it can be
        played; its new PS5 title ID."""
        before = self.titles()
        if not game.description:
            from .library import store_details
            try:
                game.description = store_details(game.app).get("short_description", "")
            except OSError:
                pass
        if any(e["name"] == str(game.app) for e in self.files.list("/data/playden-games")):
            # Installed by an earlier run that stopped while it downloaded: only wait for it.
            self.say(f"[{game.app}] {game.title}: already downloading; waiting until it can be played")
            return self.wait_ready(game, before, None)
        self.playden_front()
        lines = self.ui.open_game(game, self.library)
        button = " ".join(l.text for l in lines if 640 < l.y < 720 and l.x < 1240)
        gb = size_gb(button)
        if self.max_gb and gb and gb > self.max_gb:
            self.ui.press("circle")
            raise SkipGame(f"{gb:.1f} GB is over the {self.max_gb:g} GB limit")
        free = free_space(lines)
        need = (gb or 0) * INSTALL_OVERHEAD
        if free is not None and free - self.reserve_gb < need:
            if self.make_room(game, need, free) is None:
                self.ui.press("circle")
                raise DeferGame(f"needs {need:.1f} GB with {self.reserve_gb:g} GB kept free; {free:.1f} GB free "
                                "and no tested game left to uninstall")
        self.say(f"[{game.app}] {game.title}: installing ({button.strip()}; "
                 f"{'?' if free is None else f'{free:.1f}'} GB free)")
        self.ui.install(game, self.files)
        return self.wait_ready(game, before, gb)

    def wait_ready(self, game, before, gb):
        """Wait until the game has its PS5 title; the title ID.

        Some games get their title when the download ends; others wait on their page with "Play - Sets up
        first" (A Way Out) until Play is pressed, so the page is looked at every few minutes and set up."""
        # A download of g GB at no less than about 4 MB/s, plus preparation.
        limit = max(1800, (gb or 30) * 300)
        started = time.monotonic()
        deadline, next_look = started + limit, started + 120
        while time.monotonic() < deadline:
            time.sleep(30)
            title = self.installed_title(game)
            if title:
                return title
            if time.monotonic() < next_look:
                continue
            next_look = time.monotonic() + 180
            self.playden_front()
            lines = self.ui.open_game(game, self.library)
            button = " ".join(l.text for l in lines if 640 < l.y < 720 and l.x < 1240)
            if "play" in button.lower() and "set" in button.lower():
                return self.set_up(game)
            if "queued" in button.lower() and time.monotonic() - started < QUEUE_WAIT:
                # Waiting behind another download (Playden 0.10's queue): its own time starts once it runs.
                deadline = max(deadline, time.monotonic() + limit)
            self.ui.press("circle")
        raise UIError(f"{game.title}: no PS5 title {int(limit)} s after Install")

    def set_up(self, game, timeout=1200):
        """Press "Play - Sets up first" on the game's page: Playden prepares the game, makes its title and starts
        it. Close it once the title is there; its title ID. Playden's refusal (a dialog) becomes RefusedGame."""
        self.say(f"[{game.app}] {game.title}: downloaded; pressing Play so Playden sets it up")
        self.ui.press("cross", gap=3.0)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(10)
            title = self.installed_title(game)
            if title:
                if self.console.is_running(title):
                    self.console.close(title)
                    time.sleep(5)
                return title
            if self.console.is_running(PLAYDEN):
                lines, _, _ = self.ui.read(0.3)
                dialog = [l.text for l in lines if 250 < l.y < 760 and 480 < l.x < 1440]
                text = " ".join(dialog).lower()
                if any(word in text for word in ("can't", "cannot", "refuse", "not supported", "failed", "error")):
                    self.ui.press("circle")
                    raise RefusedGame(" ".join(dialog)[:300])
        raise UIError(f"{game.title}: not set up {timeout} s after Play")

    def wait_prepared(self, game, timeout=1200):
        """Wait until Playden has finished preparing the game. Playden 0.10 reserves the PS5 title when it starts
        preparing and needs a minute or two more (stage-title, copy-template, validate, publish); a game started
        before that quits at once or is refused (0x80940031), and the prepare is left unfinished."""
        deadline = time.monotonic() + timeout
        while True:
            state, line = prepare_state(self.runtime_log(), game.app)
            if state in (None, "ready"):
                return
            if state == "failed":
                raise RefusedGame(f"Playden could not prepare it: {line[:300]}")
            if time.monotonic() > deadline:
                raise UIError(f"{game.title}: still being prepared {timeout} s on: {line[:200]}")
            time.sleep(10)

    def runtime_log(self):
        text = ""
        for name in ("runtime.log.1", "runtime.log"):
            try:
                text += self.files.download(f"{LOGS}/{name}").decode("utf-8", "replace")
            except FileManagerError:
                pass
        return text

    def refused(self, game, reason):
        """A game Playden would not prepare: a "Refused" issue draft with the logs, then remove its download."""
        from .runner import Result
        result = Result("", game.title, game.app, status="refused", detail=reason,
                        started_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.writer.add(result)
        zip_name = f"refused-{game.app}-logs.zip"
        versions = self.logs.collect("none", game.app, self.out / "logs" / zip_name)
        issue = self.writer.write_issue(result, versions, zip_name)
        self.mark(game, status="refused", detail=reason, logs=f"logs/{zip_name}",
                  issue=str(issue.relative_to(self.out)) if issue else "")
        self.save_report(game, None, result, versions, self.out / "logs" / zip_name)
        self.remove_download(game)

    def show_overlay(self, game):
        """Turn on the game's performance overlay at full detail, so its screenshots show frame rate, frame times,
        memory and GPU load. Its Game settings exist only once it is installed, so this comes after the install."""
        if not game.description:
            from .library import store_details
            try:
                game.description = store_details(game.app).get("short_description", "")
            except OSError:
                pass
        try:
            self.ui.open_game(game, self.library)
            self.ui.set_overlay(game)
            self.ui.press("circle", gap=1.0)  # back to the Library
        except UIError as error:
            self.say(f"[{game.app}] {game.title}: performance overlay not set: {error}")
            self.playden_front()

    def report_folder(self, game):
        return self.reports / f"{game.app}-{slug(game.title)}"

    def save_screenshot(self, game, result):
        """The game's screenshots in its report folder: screenshot-30s.jpg (30 s after it started running) and
        screenshot-90s.jpg (just before it was closed), or, for a game that quit before them, screenshot.jpg of the
        screen now (a crash dialog, Home), before Playden comes back to the front."""
        if not self.reports:
            return
        folder = self.report_folder(game)
        folder.mkdir(parents=True, exist_ok=True)
        for old in SCREENSHOTS:
            (folder / old).unlink(missing_ok=True)  # from an earlier test of the same game
        try:
            copied = False
            for taken, name in ((result.first_screenshot, SCREENSHOTS[0]), (result.screenshot, SCREENSHOTS[1])):
                if taken and (self.out / taken).exists():
                    shutil.copyfile(self.out / taken, folder / name)
                    copied = True
            if not copied:
                self.capture.snapshot(str(folder / SCREENSHOTS[2]))
        except (OSError, CaptureError) as error:
            self.say(f"[{game.app}] {game.title}: no screenshot for the report folder: {error}")

    def save_report(self, game, title, result, versions, logs_zip):
        """In the game's report folder: Playden's report zip (or else the tester's own logs zip, logs_zip), the test
        result, and issue.md, a draft for Playden's test-report form that names the files there to attach."""
        if not self.reports:
            return
        folder = self.report_folder(game)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "result.json").write_text(json.dumps(
            {"app": game.app, "game": game.title, "ps5_title": title, "status": result.status,
             "detail": result.detail, "screen": result.screen.get("verdict", ""),
             "tested": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1, ensure_ascii=False), encoding="utf-8")
        zip_name = "playden-report.zip"
        try:
            if not self.web:
                raise WebAccessError("no web access (Playden 0.9.0 or later, port 7031)")
            self.web.report_zip(title if title and title != "none" else None, folder / zip_name)
        except WebAccessError as error:
            self.say(f"[{game.app}] {game.title}: no Playden report zip, keeping the tester's logs zip: {error}")
            zip_name = "logs.zip"
            if logs_zip.exists():
                shutil.copyfile(logs_zip, folder / zip_name)
        shots = [name for name in SCREENSHOTS if (folder / name).exists()]
        self.writer.write_issue(result, versions, zip_name, path=folder / "issue.md", screenshot=shots)

    def remove_download(self, game):
        if self.keep:
            return
        try:
            self.playden_front()
            self.ui.uninstall(game.title, self.files, game.app, None)
            self.mark(game, uninstalled=True, uninstall_error="")
            self.say(f"[{game.app}] {game.title}: download removed (saves kept)")
        except UIError as error:
            self.mark(game, uninstalled=False, uninstall_error=str(error))
            self.say(f"[{game.app}] {game.title}: download not removed: {error}")

    def run_one(self, game):
        """Test one game; its Result, or None when it was skipped."""
        title = self.installed_title(game)
        downloaded = False
        if not title:
            try:
                title = self.download(game)
                downloaded = True
            except SkipGame as reason:
                self.say(f"[{game.app}] {game.title}: skipped, {reason}")
                self.mark(game, status="skipped", detail=str(reason))
                return None
            except DownloadFailed as reason:
                self.say(f"[{game.app}] {game.title}: skipped, {reason}")
                self.mark(game, status="skipped", detail=str(reason))
                self.ui.press("circle")
                return None
            except NotInLibrary as reason:
                # Not something the tester got wrong, so it does not count towards the three in a row.
                self.say(f"[{game.app}] {game.title}: skipped, not in Playden's Library ({reason})")
                self.mark(game, status="skipped", detail=f"not in Playden's Library: {reason}")
                self.ui.press("circle")
                return None
            except DeferGame as reason:
                self.say(f"[{game.app}] {game.title}: deferred, {reason}")
                self.mark(game, status="deferred", detail=str(reason))
                return None
            except RefusedGame as reason:
                self.say(f"[{game.app}] {game.title}: Playden refused to set it up: {reason}")
                self.refused(game, str(reason))
                return None
        try:
            self.wait_prepared(game)
        except RefusedGame as reason:
            self.say(f"[{game.app}] {game.title}: {reason}")
            self.refused(game, str(reason))
            return None
        self.mark(game, status="testing", ps5_title=title, downloaded=downloaded)
        # Games are started with Playden in front, as when Escape Simulator ran; started while Playden was stuck
        # behind the PS5's Home, Funguys Swarm and Looking Up I See Only A Ceiling quit after 2 s.
        try:
            self.playden_front()
            self.show_overlay(game)
        except (UIError, LaunchError) as error:
            self.say(f"[{game.app}] {game.title}: Playden not on screen before the test: {error}")
        result = self.runner.run(catalog.Game(title, game.title, game.app))
        if result.status == LAUNCH_FAILED and "0x80940031" in result.detail:
            # Seen now and then on Playden 0.10 right after an install (Escape Simulator 2, The Mermaid Mask); the
            # same title started on the next try.
            self.say(f"[{game.app}] {game.title}: launch refused (0x80940031); trying once more")
            time.sleep(15)
            try:
                self.playden_front()
            except (UIError, LaunchError) as error:
                self.say(f"[{game.app}] {game.title}: Playden not on screen before the retry: {error}")
            result = self.runner.run(catalog.Game(title, game.title, game.app))
        self.writer.add(result)
        self.save_screenshot(game, result)
        if result.status == STUCK:
            self.mark(game, status="stuck")
            return result
        # Start Playden: it writes the session to the title log, and the uninstall happens there. It has to be in
        # front for that (and for its web access): 0.10 stays suspended after a game.
        try:
            self.playden_front()
        except (UIError, LaunchError) as error:
            self.say(f"[{game.app}] {game.title}: Playden not on screen after the test: {error}")
        self.writer.rewrite(self.runner.fill_pending(close_playden=False))
        zip_name = f"{title}-{game.app}-logs.zip"
        versions = self.logs.collect(title, game.app, self.out / "logs" / zip_name)
        issue = self.writer.write_issue(result, versions, zip_name)
        self.save_report(game, title, result, versions, self.out / "logs" / zip_name)
        self.mark(game, status=result.status, screen=result.screen.get("verdict", ""), detail=result.detail,
                  issue=str(issue.relative_to(self.out)) if issue else "", logs=f"logs/{zip_name}")
        if not self.keep and result.status != LAUNCH_FAILED:
            # A failed uninstall leaves the test result as it is. Some games have a PS5 title and files but are
            # missing from Playden's Installed games (Hotline Miami, Aperture Desk Job on this console).
            try:
                self.playden_front()
                how = self.ui.uninstall(game.title, self.files, game.app, title)
                self.mark(game, uninstalled=True, uninstall_error="")
                self.say(f"[{game.app}] {game.title}: uninstalled (saves kept"
                         f"{'; files still being deleted' if how != 'done' else ''})")
            except UIError as error:
                self.mark(game, uninstalled=False, uninstall_error=str(error))
                self.say(f"[{game.app}] {game.title}: tested, but not uninstalled: {error}")
        return result

    def recover(self):
        """Before going on after a stop: close a game left running, and give back the test result of games whose
        uninstall failed under the older code (their status then read "error")."""
        for title in sorted(t for t in self.console.running_titles() if t.startswith("FAKE78")):
            self.say(f"closing {title}, left running by the last run")
            try:
                self.console.close(title)
            except LaunchError as error:
                raise UIError(f"{title} is still running and could not be closed: {error}") from None
        titles = self.titles()
        for entry in self.state.values():
            # An uninstall that timed out while Playden was still deleting files: the title went, so it worked.
            if "still on the console" in entry.get("uninstall_error", "") and entry.get("ps5_title") not in titles:
                entry.update(uninstalled=True, uninstall_error="")
        downloads = {e["name"] for e in self.files.list("/data/playden-games")}
        for entry in list(self.state.values()):
            # Refused before refused games were cleaned up: remove the download they left.
            if entry.get("status") == "refused" and entry.get("uninstalled") is not True \
                    and str(entry["app"]) in downloads and not entry.get("uninstall_error"):
                from .library import OwnedGame
                self.remove_download(OwnedGame(entry["app"], entry["title"]))
        by_title = {r.title: r for r in self.writer.results}
        for entry in self.state.values():
            result = by_title.get(entry.get("ps5_title"))
            if entry.get("status") == "error" and "not in Installed games" in entry.get("detail", "") and result:
                entry.update(status=result.status, screen=result.screen.get("verdict", ""), uninstalled=False,
                             uninstall_error=entry["detail"], detail=result.detail)
        self.save()

    def run(self, games, limit=None):
        self.recover()
        done = done_apps(self.state)
        todo = [g for g in games if str(g.app) not in done][:limit]
        self.say(f"{len(todo)} games to test ({len(done)} already done); results in {self.out}")
        failures = 0
        for number, game in enumerate(todo, 1):
            self.say(f"=== {number}/{len(todo)}: {game.title} (app {game.app})")
            try:
                result = self.run_one(game)
            except (UIError, LaunchError, FileManagerError) as error:
                self.say(f"[{game.app}] {game.title}: {error}")
                self.mark(game, status="error", detail=str(error))
                failures += 1
                if failures >= 3:
                    self.say("Stopping: three games in a row went wrong. Check the PS5, then run again to go on.")
                    return 3
                continue
            if result and result.status == STUCK:
                self.say("Stopping: a game could not be closed.")
                return 2
            failures = failures + 1 if result and result.status == LAUNCH_FAILED else 0
            if failures >= 2:
                self.say("Stopping: launches keep failing. Check that kstuff and ShadowMountPlus are loaded.")
                return 3
        return 0


class SkipGame(Exception):
    pass


class RefusedGame(Exception):
    """Playden would not prepare the game (its dialog's text)."""


class DeferGame(Exception):
    """Not enough room now; the next run tries again."""


# In a report folder: 30 s after the start, just before the close (90 s), or the screen after a game that quit.
SCREENSHOTS = ["screenshot-30s.jpg", "screenshot-90s.jpg", "screenshot.jpg"]
INSTALL_OVERHEAD = 1.25  # the download plus preparation (bottle, shader caches) over the size Playden shows
QUEUE_WAIT = 6 * 3600  # the longest a game waits in Playden's download queue before it counts as stuck


def free_space(lines):
    """GB free on the install volume, from a details page ("Installs to Console storage - 172.7 GB free")."""
    for line in lines:
        if "free" in line.text.lower() and "install" in line.text.lower():
            return size_gb(line.text)
    return None


def prepare_state(runtime_log, app):
    """Where Playden's preparation of an app stands, from its runtime.log: (None, "") when the log has no prepare
    of it, ("ready", line) once the newest one ended with "prepare result app=<app> ready", ("failed", line) when
    it ended otherwise, and ("preparing", line) while it runs."""
    lines = [l for l in runtime_log.splitlines() if " prepare " in l and re.search(rf"\bapp={app}\b", l)]
    if not lines:
        return None, ""
    newest = lines[-1]
    if " prepare result " in newest:
        return ("ready" if newest.rstrip().endswith(" ready") else "failed"), newest
    return ("failed" if " ok=0" in newest else "preparing"), newest


def done_apps(state):
    """The apps (as strings) a campaign's progress counts as tested. A game whose run went wrong in the tester itself
    ("error", such as a Playden screen it could not read) is tested again."""
    return {app for app, entry in state.items() if entry.get("status") not in (None, "testing", "deferred", "error")}


def read_lists(paths):
    """The rows of one or more `library` lists (JSON), each game once; lists that don't exist are left out."""
    rows, seen = [], set()
    for path in [paths] if isinstance(paths, (str, Path)) else paths:
        if Path(path).exists():
            for row in json.loads(Path(path).read_text(encoding="utf-8")):
                if row["app"] not in seen:
                    seen.add(row["app"])
                    rows.append(row)
    return rows


def sort_rows(rows, ranks=None, pads=None, tiers=None):
    """Rows of a `library` list in campaign order. Installed games first (no download to wait for), then games with
    full controller support before partial ones (whose menus may need a mouse), then by ProtonDB tier ({app: rank},
    best rated first; see protondb.py), then by console rank ({app: rank}, lower first; see ports.py), then by pad
    rank ({app: rank}: DualSense games first; see storefeatures.py), keeping the list's order otherwise."""
    from .protondb import UNRATED
    from .storefeatures import NO_PAD
    ranks, pads, tiers = ranks or {}, pads or {}, tiers or {}
    return sorted(rows, key=lambda row: (not row.get("installed"), row.get("controller") == "partial",
                                         tiers.get(row["app"], UNRATED), ranks.get(row["app"], 0),
                                         pads.get(row["app"], NO_PAD)))


def load_list(paths, ranks=None, pads=None, tiers=None):
    """The games of one or more `library` lists (JSON) as OwnedGame-like objects, in campaign order (see
    sort_rows)."""
    from .library import OwnedGame
    rows = sort_rows(read_lists(paths), ranks, pads, tiers)
    fields = set(OwnedGame.__dataclass_fields__)
    return [OwnedGame(**{k: v for k, v in row.items() if k in fields}) for row in rows]
