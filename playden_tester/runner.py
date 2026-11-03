"""Run each game once and decide how far it got."""
import time
from dataclasses import dataclass, field

from . import titlelog
from .capture import CaptureError
from .console import PLAYDEN, LaunchError

LAUNCH_FAILED = "launch_failed"   # the helper could not start the title
NO_START = "did_not_start"        # started, but no sandbox ever appeared
CRASHED = "crashed"               # quit before the watch time, with a fatal line in its log
EXITED = "exited_early"           # quit before the watch time, nothing fatal in its log
SURVIVED = "survived"             # still running when the watch time was over
STUCK = "not_closed"              # survived, and nobody closed it, so the run stopped


@dataclass
class Settings:
    start_timeout: float = 45.0   # seconds for the sandbox to appear
    watch: float = 120.0          # seconds a game must keep running to count as survived
    close_timeout: float = 600.0  # seconds to wait for the game to be closed after the watch
    log_timeout: float = 5.0      # seconds to wait for the session in the log right after a game ends
    refresh_timeout: float = 90.0 # seconds to wait for Playden, started afterwards, to write the sessions
    poll: float = 2.0
    auto_close: bool = False      # close a game that survived through padd, instead of waiting for a person
    screen_seconds: float = 4.0   # seconds of screen watched (with a capture card) before a surviving game is closed
    first_shot: float = 30.0      # seconds after the game starts running for a first screenshot (0: none)


@dataclass
class Result:
    title: str
    name: str
    steam_app: int = None
    status: str = ""
    detail: str = ""
    seconds_running: float = 0.0
    session: str = ""
    session_seconds: int = 0
    problems: list = field(default_factory=list)
    wine_errors: dict = field(default_factory=dict)
    log_tail: str = ""
    started_at: str = ""
    screen: dict = field(default_factory=dict)  # verdict (black, still, moving), brightness, motion
    screenshot: str = ""         # just before the game is closed, at the end of the watch
    first_screenshot: str = ""   # first_shot seconds after it started running
    notes: list = field(default_factory=list)  # what detail is made of

    @property
    def passed(self):
        return self.status == SURVIVED and self.screen.get("verdict") != "black"


class Runner:
    def __init__(self, console, settings=None, say=print, clock=time.monotonic, sleep=time.sleep,
                 capture=None, shots=None):
        self.console = console
        self.capture = capture  # a capture.Capture, or None without a capture card
        self.shots = shots      # folder for screenshots
        self.pending = []       # (result, session start times before its launch) whose session is not in its log yet
        self.settings = settings or Settings()
        self.say = say
        self.clock = clock
        self.sleep = sleep

    def _wait(self, condition, timeout):
        """Poll until condition() is true; the seconds it took, or None on timeout."""
        start = self.clock()
        while True:
            if condition():
                return self.clock() - start
            if self.clock() - start >= timeout:
                return None
            self.sleep(self.settings.poll)

    def run(self, game):
        s = self.settings
        result = Result(game.title, game.name, game.steam_app, started_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        before = titlelog.report_times(self.console.title_log(game.title))

        self.say(f"[{game.title}] {game.name}: launching")
        try:
            self.console.launch(game.title)
        except LaunchError as error:
            result.status = LAUNCH_FAILED
            result.notes.append(str(error))
            self._settle(result)
            return result

        if self._wait(lambda: self.console.is_running(game.title), s.start_timeout) is None:
            result.status = NO_START
            result.notes.append(f"no sandbox after {s.start_timeout:.0f} s")
            if not self._read_session(result, before, s.log_timeout):
                self.pending.append((result, before))
            self._settle(result)
            return result

        self.say(f"[{game.title}] running, watching for {s.watch:.0f} s")
        start = self.clock()
        first = min(s.first_shot, s.watch) if self.capture and self.shots and s.first_shot else 0
        quit_after = self._wait(lambda: not self.console.is_running(game.title), first) if first else None
        if first and quit_after is None:
            try:
                result.first_screenshot = self.capture.snapshot(f"{self.shots}/{game.title}-{first:.0f}s.jpg").name
            except CaptureError as error:
                self.say(f"[{game.title}] no screenshot at {first:.0f} s: {error}")
        if quit_after is None:
            rest = self._wait(lambda: not self.console.is_running(game.title), max(0.0, s.watch - (self.clock() - start)))
            quit_after = None if rest is None else self.clock() - start
        if quit_after is None:
            result.seconds_running = self.clock() - start
            result.status = SURVIVED
            self._look(result)
            if s.auto_close:
                self.say(f"[{game.title}] survived {s.watch:.0f} s, closing it")
                try:
                    self.console.close(game.title)
                except LaunchError as error:
                    self.say(f"[{game.title}] could not close it: {error}")
            else:
                self.say(f"[{game.title}] survived {s.watch:.0f} s. Close it on the PS5 (Home: Options on its tile, "
                         f"Close Game) (waiting up to {s.close_timeout:.0f} s)")
            if self._wait(lambda: not self.console.is_running(game.title), s.close_timeout) is None:
                result.status = STUCK
                result.notes.append("still running; the run stopped here")
                self._settle(result)
                return result
        else:
            result.seconds_running = quit_after

        if result.status != SURVIVED:
            result.status = EXITED
            result.notes.append(f"quit after {result.seconds_running:.0f} s")
        if not self._read_session(result, before, self.settings.log_timeout):
            self.pending.append((result, before))
        self._settle(result)
        return result

    def fill_pending(self, close_playden=None):
        """Read the sessions the logs did not have yet. Playden writes every game's title log when it starts,
        so start it, wait for the logs, and close it again when padd can. The results that changed."""
        if not self.pending:
            return []
        self.say(f"Starting Playden to bring {len(self.pending)} game log(s) up to date")
        try:
            if not self.console.is_running(PLAYDEN):
                self.console.launch(PLAYDEN)
        except LaunchError as error:
            self.say(f"Could not start Playden: {error}")
            return []
        filled, deadline = [], self.clock() + self.settings.refresh_timeout
        for result, before in self.pending:
            if self._read_session(result, before, max(0.0, deadline - self.clock())):
                filled.append(result)
        self.pending = [(r, b) for r, b in self.pending if r not in filled]
        for result in filled:
            self._settle(result)
        if self.settings.auto_close if close_playden is None else close_playden:
            try:
                self.console.close(PLAYDEN)
            except LaunchError as error:
                self.say(f"Could not close Playden: {error}")
        return filled

    def _settle(self, result):
        """The status and detail from what is known now."""
        if result.status in (EXITED, CRASHED):
            result.status = CRASHED if result.problems else EXITED
        notes = list(result.notes)
        if any(r is result for r, _ in self.pending):
            notes.append("no new session in the title log")
        result.detail = "; ".join(notes)

    def _look(self, result):
        """Screenshot and screen check of a running game, when there is a capture card."""
        if not self.capture:
            return
        try:
            check = self.capture.check(self.settings.screen_seconds)
            result.screen = check.as_dict()
            if self.shots:
                result.screenshot = self.capture.snapshot(f"{self.shots}/{result.title}.jpg").name
        except CaptureError as error:
            self.say(f"[{result.title}] no screen check: {error}")
            return
        self.say(f"[{result.title}] screen: {check.verdict} (brightness {check.brightness:.0f}, motion {check.motion:.2f})")

    def _read_session(self, result, before, timeout):
        """Fill in the new session from the title log, once Playden has written it. False if it has not."""
        found = []

        def written():
            sessions = [x for x in titlelog.parse(self.console.title_log(result.title)) if x.start not in before]
            found[:] = sessions
            return bool(sessions)

        if self._wait(written, timeout) is None:
            return False
        session = found[0]
        result.session = session.name
        result.session_seconds = session.duration
        result.problems = [f"{label}: {line}" for label, line in session.problems]
        result.wine_errors = session.wine_errors
        result.log_tail = session.tail()
        return True
