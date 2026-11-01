"""Test a list of Steam games one by one: download through Playden if needed, test, collect logs, uninstall.

Progress lives in <out>/campaign.json, so a campaign that stops (console restart, a game that would not close)
goes on where it was when it is run again.
"""
import json
import re
import time
from dataclasses import asdict
from pathlib import Path

from . import catalog
from .console import HOMEBREW, PLAYDEN, LaunchError
from .filemanager import FileManagerError
from .logs import LogCollector
from .playden_ui import UIError
from .report import RunWriter
from .runner import LAUNCH_FAILED, STUCK, Runner

SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(KB|MB|GB|TB)", re.IGNORECASE)
UNITS = {"kb": 1 / 1048576, "mb": 1 / 1024, "gb": 1, "tb": 1024}


def size_gb(text):
    match = SIZE.search(text or "")
    return float(match.group(1).replace(",", ".")) * UNITS[match.group(2).lower()] if match else None


class Campaign:
    def __init__(self, console, ui, capture, settings, out, meta, say=print, keep=False, max_gb=None,
                 reserve_gb=15.0):
        self.console, self.ui, self.files = console, ui, console.files
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

    def installed_title(self, app):
        for game in catalog.games(self.files):
            if game.steam_app == app:
                return game.title
        return None

    def playden_front(self):
        """Playden open, on a screen with its tabs."""
        if not self.console.is_running(PLAYDEN):
            self.console.launch(PLAYDEN)
            time.sleep(8)
        for _ in range(6):
            lines, _, _ = self.ui.read(1.0)
            # The tabs show through a sheet, a dialog or the keyboard, but do not take R1 while one is open.
            if self.ui.home_visible(lines) and not self.ui.overlay_open(lines):
                return
            self.ui.press("circle", gap=1.0)
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
        # A download of g GB at no less than about 4 MB/s, plus preparation.
        deadline = time.monotonic() + max(1800, (gb or 10) * 300)
        while time.monotonic() < deadline:
            time.sleep(30)
            new = self.titles() - before
            if not new:
                continue
            # The title exists; Playden is ready when the game's page offers Play.
            self.playden_front()
            lines = self.ui.open_game(game, self.library)
            focused = " ".join(l.text for l in lines if 640 < l.y < 720 and l.x < 500).lower()
            self.ui.press("circle")
            if "play" in focused:
                return sorted(new)[0]
        raise UIError(f"{game.title}: not ready {self.ready_timeout} s after Install")

    def run_one(self, game):
        """Test one game; its Result, or None when it was skipped."""
        title = self.installed_title(game.app)
        downloaded = False
        if not title:
            try:
                title = self.download(game)
                downloaded = True
            except SkipGame as reason:
                self.say(f"[{game.app}] {game.title}: skipped, {reason}")
                self.mark(game, status="skipped", detail=str(reason))
                return None
            except DeferGame as reason:
                self.say(f"[{game.app}] {game.title}: deferred, {reason}")
                self.mark(game, status="deferred", detail=str(reason))
                return None
        self.mark(game, status="testing", ps5_title=title, downloaded=downloaded)
        result = self.runner.run(catalog.Game(title, game.title, game.app))
        self.writer.add(result)
        if result.status == STUCK:
            self.mark(game, status="stuck")
            return result
        # Start Playden: it writes the session to the title log, and the uninstall happens there.
        self.writer.rewrite(self.runner.fill_pending(close_playden=False))
        zip_name = f"{title}-{game.app}-logs.zip"
        versions = self.logs.collect(title, game.app, self.out / "logs" / zip_name)
        issue = self.writer.write_issue(result, versions, zip_name)
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
        by_title = {r.title: r for r in self.writer.results}
        for entry in self.state.values():
            result = by_title.get(entry.get("ps5_title"))
            if entry.get("status") == "error" and "not in Installed games" in entry.get("detail", "") and result:
                entry.update(status=result.status, screen=result.screen.get("verdict", ""), uninstalled=False,
                             uninstall_error=entry["detail"], detail=result.detail)
        self.save()

    def run(self, games, limit=None):
        self.recover()
        done = {app for app, entry in self.state.items()
                if entry.get("status") not in (None, "testing", "deferred")}
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


class DeferGame(Exception):
    """Not enough room now; the next run tries again."""


INSTALL_OVERHEAD = 1.25  # the download plus preparation (bottle, shader caches) over the size Playden shows


def free_space(lines):
    """GB free on the install volume, from a details page ("Installs to Console storage - 172.7 GB free")."""
    for line in lines:
        if "free" in line.text.lower() and "install" in line.text.lower():
            return size_gb(line.text)
    return None


def load_list(path):
    """The games of a `library` list (JSON): OwnedGame-like objects."""
    from .library import OwnedGame
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    rows.sort(key=lambda row: not row.get("installed"))  # installed games first: no download to wait for
    fields = set(OwnedGame.__dataclass_fields__)
    return [OwnedGame(**{k: v for k, v in row.items() if k in fields}) for row in rows]
