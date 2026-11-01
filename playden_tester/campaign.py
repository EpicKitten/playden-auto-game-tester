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
                 ready_timeout=3600):
        self.console, self.ui, self.files = console, ui, console.files
        self.settings, self.say, self.keep, self.max_gb = settings, say, keep, max_gb
        self.ready_timeout = ready_timeout
        self.out = Path(out)
        self.writer = RunWriter(self.out, meta)
        self.runner = Runner(console, settings, say=say, capture=capture, shots=self.out)
        self.logs = LogCollector(self.files)
        self.state_path = self.out / "campaign.json"
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {}

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
            if self.ui.home_visible(lines):
                return
            self.ui.press("circle", gap=1.0)  # close a sheet or dialog left open
        raise UIError("Playden's tabs are not on screen")

    def download(self, game):
        """Install the game through Playden and wait until it can be played; its new PS5 title ID."""
        before = self.titles()
        if not game.description:
            from .library import store_details
            try:
                game.description = store_details(game.app).get("short_description", "")
            except OSError:
                pass
        self.playden_front()
        lines = self.ui.open_game(game)
        button = " ".join(l.text for l in lines if 640 < l.y < 720 and l.x < 1240)
        gb = size_gb(button)
        if self.max_gb and gb and gb > self.max_gb:
            self.ui.press("circle")
            raise SkipGame(f"{gb:.1f} GB is over the {self.max_gb:g} GB limit")
        self.say(f"[{game.app}] {game.title}: installing ({button.strip()})")
        self.ui.install(game, self.files)
        deadline = time.monotonic() + self.ready_timeout
        while time.monotonic() < deadline:
            time.sleep(30)
            new = self.titles() - before
            if not new:
                continue
            # The title exists; Playden is ready when the game's page offers Play.
            self.playden_front()
            lines = self.ui.open_game(game)
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
            self.playden_front()
            self.ui.uninstall(game.title, self.files, game.app, title)
            self.mark(game, uninstalled=True)
            self.say(f"[{game.app}] {game.title}: uninstalled (saves kept)")
        return result

    def run(self, games, limit=None):
        done = {app for app, entry in self.state.items() if entry.get("status") not in (None, "testing")}
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


def load_list(path):
    """The games of a `library` list (JSON): OwnedGame-like objects."""
    from .library import OwnedGame
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    rows.sort(key=lambda row: not row.get("installed"))  # installed games first: no download to wait for
    fields = set(OwnedGame.__dataclass_fields__)
    return [OwnedGame(**{k: v for k, v in row.items() if k in fields}) for row in rows]
