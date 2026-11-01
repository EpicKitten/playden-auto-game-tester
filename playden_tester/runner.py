"""Run each game once and decide how far it got."""
import time
from dataclasses import dataclass, field

from . import titlelog
from .console import LaunchError

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
    log_timeout: float = 30.0     # seconds to wait for Playden to write the session to the log
    poll: float = 2.0
    auto_close: bool = False      # close a game that survived through padd, instead of waiting for a person


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

    @property
    def passed(self):
        return self.status == SURVIVED


class Runner:
    def __init__(self, console, settings=None, say=print, clock=time.monotonic, sleep=time.sleep):
        self.console = console
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
            result.status, result.detail = LAUNCH_FAILED, str(error)
            return result

        if self._wait(lambda: self.console.is_running(game.title), s.start_timeout) is None:
            result.status, result.detail = NO_START, f"no sandbox after {s.start_timeout:.0f} s"
            self._read_session(result, before)
            return result

        self.say(f"[{game.title}] running, watching for {s.watch:.0f} s")
        start = self.clock()
        quit_after = self._wait(lambda: not self.console.is_running(game.title), s.watch)
        if quit_after is None:
            result.seconds_running = self.clock() - start
            result.status = SURVIVED
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
                result.status, result.detail = STUCK, "still running; the run stopped here"
                return result
        else:
            result.seconds_running = quit_after

        self._read_session(result, before)
        if result.status != SURVIVED:
            result.status = CRASHED if result.problems else EXITED
            result.detail = "; ".join(filter(None, [f"quit after {result.seconds_running:.0f} s", result.detail]))
        return result

    def _read_session(self, result, before):
        """Fill in the new session from the title log, once Playden has written it."""
        found = []

        def written():
            sessions = [x for x in titlelog.parse(self.console.title_log(result.title)) if x.start not in before]
            found[:] = sessions
            return bool(sessions)

        if self._wait(written, self.settings.log_timeout) is None:
            result.detail = (result.detail + "; " if result.detail else "") + "no new session in the title log"
            return
        session = found[0]
        result.session = session.name
        result.session_seconds = session.duration
        result.problems = [f"{label}: {line}" for label, line in session.problems]
        result.wine_errors = session.wine_errors
        result.log_tail = session.tail()
