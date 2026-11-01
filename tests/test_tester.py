import unittest

from playden_tester import titlelog
from playden_tester.catalog import Game
from playden_tester.console import LaunchError, launch_outcome
from playden_tester.runner import CRASHED, EXITED, LAUNCH_FAILED, NO_START, STUCK, SURVIVED, Runner, Settings

REPORT = "PW_REPORT/1 build=abc profile=playden-steam-{app} cycle=0 pid=1 time={time}"


def digest(*sessions):
    """A title log digest; sessions are (number, start, end, body lines), newest first."""
    parts = []
    for number, start, _, lines in sessions:
        parts += [f"== session-{number}.log", REPORT.format(app=220, time=start), *lines]
    parts.append("== reports")
    parts += [f"session-{number}.log bytes=100 time={end}" for number, _, end, _ in sessions]
    return "\n".join(parts) + "\n"


class TitleLogTest(unittest.TestCase):
    def test_sessions_newest_first_with_duration(self):
        text = digest((1, 2000, 2090, ["REC seq=1 ok"]), (0, 1000, 1005, ["REC seq=1 ok"]))
        sessions = titlelog.parse(text)
        self.assertEqual([s.name for s in sessions], ["session-1.log", "session-0.log"])
        self.assertEqual(sessions[0].duration, 90)
        self.assertEqual(sessions[0].steam_app, 220)
        self.assertEqual(titlelog.report_times(text), {1000, 2000})

    def test_problems_and_wine_errors(self):
        text = digest((0, 1000, 1004, [
            "REC seq=2 t=1 WINE 002c:err:setupapi:do_file_copyW Unsupported style(s) 0x10",
            "REC seq=3 t=2 WINE 002c:err:setupapi:again",
            "mono_win32_wait_for_single_object_ex failed with error 0",
            "Crash!!!",
        ]))
        session = titlelog.parse(text)[0]
        self.assertEqual([label for label, _ in session.problems], ["crash"])
        self.assertEqual(session.wine_errors, {"setupapi": 2})
        self.assertIn("Crash!!!", session.tail())

    def test_ok_status_lines_are_not_problems(self):
        text = digest((0, 1, 2, ["REC seq=19 PW_WINE64 load status=0 stage=6 module=0x60d2"]))
        self.assertEqual(titlelog.parse(text)[0].problems, [])


class LaunchOutcomeTest(unittest.TestCase):
    def test_outcomes(self):
        self.assertIsNone(launch_outcome("title=FAKE78001 wait state=0 s=0.00\n"))
        self.assertTrue(launch_outcome("title=FAKE78001 wait state=0 s=0.00\nsceLncUtilLaunchApp rc=0x00000000\n"))
        self.assertIsNone(launch_outcome("wait state=0\nsceLncUtilLaunchApp rc=0x80940005\n"))
        self.assertTrue(launch_outcome("wait state=0\nsceLncUtilLaunchApp rc=0x80940005\nsceSystemServiceLaunchApp rc=0x00000001\n"))
        self.assertFalse(launch_outcome("wait state=0\nsceLncUtilLaunchApp rc=0x80940005\nsceSystemServiceLaunchApp rc=0x80940005\n"))
        self.assertFalse(launch_outcome("title=FAKE78001 wait state=1 s=120.00\n"))
        self.assertFalse(launch_outcome("bad title id\n"))


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeConsole:
    """A console where the game runs from `starts_at` to `stops_at` (clock seconds after launch)."""

    def __init__(self, clock, starts_at=4, stops_at=None, log_after="", fail_launch=False):
        self.clock, self.starts_at, self.stops_at = clock, starts_at, stops_at
        self.log_before = digest((0, 1000, 1010, ["old"]))
        self.log_after = log_after
        self.fail_launch = fail_launch
        self.launched_at = None

    def launch(self, title):
        if self.fail_launch:
            raise LaunchError("elfldr is not running")
        self.launched_at = self.clock()

    def is_running(self, title):
        if self.launched_at is None or self.starts_at is None:
            return False
        t = self.clock() - self.launched_at
        return t >= self.starts_at and (self.stops_at is None or t < self.stops_at)

    def close(self, title):
        self.closed_at = self.clock() - self.launched_at
        self.stops_at = self.closed_at

    def title_log(self, title):
        if self.launched_at is not None and not self.is_running(title) and self.log_after:
            return self.log_after
        return self.log_before


class RunnerTest(unittest.TestCase):
    game = Game("FAKE78001", "Half-Life 2", 220)

    def run_game(self, auto_close=False, **console):
        clock = FakeClock()
        self.fake = FakeConsole(clock, **console)
        settings = Settings(start_timeout=20, watch=60, close_timeout=30, log_timeout=10, poll=2, auto_close=auto_close)
        return Runner(self.fake, settings, say=lambda _: None, clock=clock, sleep=clock.sleep).run(self.game)

    def test_survived_and_closed_through_padd(self):
        new = digest((1, 2000, 2064, ["fine"]), (0, 1000, 1010, ["old"]))
        result = self.run_game(auto_close=True, stops_at=None, log_after=new)
        self.assertEqual(result.status, SURVIVED)
        self.assertGreaterEqual(self.fake.closed_at, 60)
        self.assertEqual(result.session, "session-1.log")

    def test_survived_then_closed(self):
        new = digest((1, 2000, 2100, ["fine"]), (0, 1000, 1010, ["old"]))
        result = self.run_game(stops_at=80, log_after=new)
        self.assertEqual(result.status, SURVIVED)
        self.assertEqual(result.session, "session-1.log")
        self.assertEqual(result.session_seconds, 100)

    def test_crashed(self):
        new = digest((1, 2000, 2004, ["Crash!!!"]), (0, 1000, 1010, ["old"]))
        result = self.run_game(stops_at=10, log_after=new)
        self.assertEqual(result.status, CRASHED)
        self.assertTrue(result.problems[0].startswith("crash"))

    def test_exited_without_fatal_lines(self):
        new = digest((1, 2000, 2004, ["bye"]), (0, 1000, 1010, ["old"]))
        self.assertEqual(self.run_game(stops_at=10, log_after=new).status, EXITED)

    def test_never_started(self):
        self.assertEqual(self.run_game(starts_at=None).status, NO_START)

    def test_launch_failed(self):
        self.assertEqual(self.run_game(fail_launch=True).status, LAUNCH_FAILED)

    def test_not_closed(self):
        self.assertEqual(self.run_game(stops_at=None).status, STUCK)

    def test_missing_session_is_noted(self):
        result = self.run_game(stops_at=10)
        self.assertEqual(result.status, EXITED)
        self.assertIn("no new session", result.detail)


if __name__ == "__main__":
    unittest.main()


class ScreenCheckTest(unittest.TestCase):
    def test_verdicts(self):
        from playden_tester.capture import check_frames
        black = [bytes([2]) * 100] * 3
        still = [bytes([90]) * 100] * 3
        moving = [bytes([90]) * 100, bytes([120]) * 100, bytes([60]) * 100]
        self.assertEqual(check_frames(black).verdict, "black")
        self.assertEqual(check_frames(still).verdict, "still")
        self.assertEqual(check_frames(moving).verdict, "moving")
        self.assertAlmostEqual(check_frames(moving).motion, 45.0)


class FakeCapture:
    def __init__(self, frames):
        self.frames = frames
        self.shots = []

    def check(self, seconds):
        from playden_tester.capture import check_frames
        return check_frames(self.frames)

    def snapshot(self, path):
        from pathlib import Path
        self.shots.append(path)
        return Path(path)


class RunnerScreenTest(unittest.TestCase):
    def test_black_screen_fails_a_survivor(self):
        clock = FakeClock()
        new = digest((1, 2000, 2064, ["fine"]), (0, 1000, 1010, ["old"]))
        fake = FakeConsole(clock, stops_at=None, log_after=new)
        camera = FakeCapture([bytes([1]) * 100] * 4)
        settings = Settings(start_timeout=20, watch=60, close_timeout=30, log_timeout=10, poll=2, auto_close=True)
        result = Runner(fake, settings, say=lambda _: None, clock=clock, sleep=clock.sleep,
                        capture=camera, shots="shots").run(RunnerTest.game)
        self.assertEqual(result.status, SURVIVED)
        self.assertEqual(result.screen["verdict"], "black")
        self.assertFalse(result.passed)
        self.assertEqual(result.screenshot, "FAKE78001.jpg")
        self.assertEqual(camera.shots, ["shots/FAKE78001.jpg"])
