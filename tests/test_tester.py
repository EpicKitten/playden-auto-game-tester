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


class LateLogConsole(FakeConsole):
    """Playden only writes the title log when it starts, as on the console."""

    def __init__(self, clock, **kw):
        super().__init__(clock, **kw)
        self.playden_started = False
        self.closed = []

    def launch(self, title):
        if title == "FAKE77031":
            self.playden_started = True
        else:
            super().launch(title)

    def close(self, title):
        if title == "FAKE77031":
            self.closed.append(title)
        else:
            super().close(title)

    def title_log(self, title):
        return self.log_after if self.playden_started else self.log_before


class FillPendingTest(unittest.TestCase):
    def test_sessions_come_from_playden_start(self):
        clock = FakeClock()
        new = digest((1, 2000, 2004, ["Crash!!!"]), (0, 1000, 1010, ["old"]))
        fake = LateLogConsole(clock, stops_at=10, log_after=new)
        settings = Settings(start_timeout=20, watch=60, close_timeout=30, log_timeout=4, poll=2, auto_close=True)
        runner = Runner(fake, settings, say=lambda _: None, clock=clock, sleep=clock.sleep)
        result = runner.run(RunnerTest.game)
        self.assertEqual(result.status, EXITED)
        self.assertIn("no new session", result.detail)
        self.assertEqual(runner.fill_pending(), [result])
        self.assertEqual(result.status, CRASHED)
        self.assertEqual(result.detail, "quit after 6 s")
        self.assertEqual(fake.closed, ["FAKE77031"])
        self.assertEqual(runner.pending, [])


class ReportTest(unittest.TestCase):
    def test_report_and_issue_draft(self):
        import tempfile
        from pathlib import Path
        from playden_tester.report import RunWriter
        from playden_tester.runner import Result
        with tempfile.TemporaryDirectory() as folder:
            writer = RunWriter(folder, {"playden_version": "0.8.0", "firmware": "12.20"})
            works = Result("FAKE78022", "Hollow Knight", 367520, status=SURVIVED, seconds_running=60,
                           screen={"verdict": "still", "brightness": 37.0, "motion": 0.41, "frames": 16},
                           screenshot="FAKE78022.jpg", log_tail="REC alive")
            spinner = Result("FAKE78012", "Balatro", 2379780, status=SURVIVED, seconds_running=60,
                             screen={"verdict": "black", "brightness": 0.0, "motion": 0.2, "frames": 16})
            for result in (works, spinner):
                writer.add(result)
            text = writer.write_issue(works, "| Field | Value |", "FAKE78022-logs.zip").read_text(encoding="utf-8")
            self.assertIn("✅ Works", text)
            self.assertIn("367520", text)
            self.assertIn("❌ Does not start", writer.write_issue(spinner, "|", "x.zip").read_text(encoding="utf-8"))
            self.assertIsNone(writer.write_issue(Result("FAKE1", "X", status=LAUNCH_FAILED), "|", "x.zip"))
            self.assertTrue((Path(folder) / "summary.csv").exists())


class AliveTest(unittest.TestCase):
    def test_black_screen_with_frames_is_broken_not_stuck(self):
        import tempfile
        from playden_tester.report import RunWriter, alive_stats
        from playden_tester.runner import Result
        tail = "REC seq=423 t=1 PW_WINE64 alive tick=5340 frames_put=1 shown=0 vk_shown=1029 audio=16279 audible=15874"
        self.assertEqual(alive_stats(tail)["vk_shown"], 1029)
        with tempfile.TemporaryDirectory() as folder:
            writer = RunWriter(folder, {})
            r = Result("FAKE78030", "Balatro", 2379780, status=SURVIVED, seconds_running=90, log_tail=tail,
                       screen={"verdict": "black", "brightness": 0.3, "motion": 0.2, "frames": 16})
            writer.add(r)
            self.assertIn("❌ Broken: starts", writer.write_issue(r, "|", "x.zip").read_text(encoding="utf-8"))


class StorageTest(unittest.TestCase):
    def test_sizes_and_free_space(self):
        from playden_tester.campaign import free_space, size_gb
        from playden_tester.screen import Line
        self.assertAlmostEqual(size_gb("Install 67 MB"), 67 / 1024)
        self.assertEqual(size_gb("Install 22,1 GB"), 22.1)
        lines = [Line("Install 67 MB", 136, 672, 160, 20),
                 Line("Installs to Console storage · 172.7 GB free", 97, 762, 400, 21)]
        self.assertEqual(free_space(lines), 172.7)
        self.assertIsNone(free_space(lines[:1]))

    def test_evictable_are_tested_and_still_installed_oldest_first(self):
        import tempfile
        from playden_tester.campaign import Campaign

        class Files:
            def list(self, path):
                return [{"name": n, "type": "d"} for n in ("FAKE78001", "FAKE78002", "FAKE78003")]

        class Con:
            files = Files()

        with tempfile.TemporaryDirectory() as folder:
            c = Campaign(Con(), None, None, Settings(), folder, {})
            c.state = {
                "1": {"app": 1, "title": "Old", "ps5_title": "FAKE78001", "status": "survived", "updated": "2026-11-01 10:00"},
                "2": {"app": 2, "title": "New", "ps5_title": "FAKE78002", "status": "crashed", "updated": "2026-11-01 12:00"},
                "3": {"app": 3, "title": "Gone", "ps5_title": "FAKE78003", "status": "survived", "uninstalled": True},
                "4": {"app": 4, "title": "Orphan", "ps5_title": "FAKE78002", "status": "survived", "uninstall_error": "x"},
                "5": {"app": 5, "title": "Busy", "ps5_title": "FAKE78001", "status": "testing"},
            }
            self.assertEqual([e["title"] for e in c.evictable()], ["Old", "New"])

    def test_results_carry_over_when_a_campaign_goes_on(self):
        import tempfile
        from playden_tester.report import RunWriter
        from playden_tester.runner import Result
        with tempfile.TemporaryDirectory() as folder:
            first = RunWriter(folder, {})
            first.add(Result("FAKE78023", "Brotato", 1942280, status=SURVIVED))
            again = RunWriter(folder, {}, resume=True)
            self.assertEqual([r.name for r in again.results], ["Brotato"])
            self.assertEqual(RunWriter(folder, {}).results, [])


class NameMatchTest(unittest.TestCase):
    def test_a_name_that_starts_another_is_a_different_game(self):
        from playden_tester.playden_ui import same_name
        self.assertFalse(same_name("Half-Life 2", "Half-Life"))
        self.assertFalse(same_name("Half-Life", "Half-Life 2"))
        self.assertFalse(same_name("Portal 2", "Portal"))
        self.assertFalse(same_name("Call of Duty: Ghosts", "Call of Duty: Black Ops II"))

    def test_ocr_slips_still_match(self):
        from playden_tester.playden_ui import same_name
        self.assertTrue(same_name("Hollow Knight", "Hollow Knight"))
        self.assertTrue(same_name("Mirror's Edge", "Mirrors Edge"))
        self.assertTrue(same_name("Ouit Playden", "Quit Playden"))
        self.assertTrue(same_name("METAL GEAR SOLID 3: Snake Eater - Master Collection Version",
                                  "METAL GEAR SOLID 3: Snake Eater - Master Collection Version"))

    def test_the_dialog_must_name_exactly_this_game(self):
        from playden_tester.playden_ui import dialog_names
        from playden_tester.screen import Line
        def dialog(text):
            return [Line("Uninstall 1 game?", 528, 300, 300, 40), Line(text, 528, 390, 800, 25)]
        self.assertTrue(dialog_names(dialog("Balatro. Frees about 67 MB. Their files and PS5 titles are"), "Balatro"))
        self.assertFalse(dialog_names(dialog("Half-Life 2. Frees about 5.8 GB. Their files and PS5"), "Half-Life"))
        self.assertTrue(dialog_names(dialog("Half-Life 2. Frees about 5.8 GB. Their files and PS5"), "Half-Life 2"))


class SearchTest(unittest.TestCase):
    def test_typed_text_is_the_start_of_the_title_as_written(self):
        from playden_tester.playden_ui import search_text
        self.assertEqual(search_text("Half-Life 2"), "HALF")
        self.assertEqual(search_text("METAL GEAR SOLID 3: Snake Eater"), "METAL GEAR SOLID 3")
        self.assertEqual(search_text("Mirror's Edge"), "MIRROR")

    def test_predicted_results_follow_playden_order(self):
        from playden_tester.library import OwnedGame
        from playden_tester.playden_ui import predict_results, search_text
        library = [OwnedGame(620, "Portal 2"), OwnedGame(400, "Portal"), OwnedGame(220, "Half-Life 2"),
                   OwnedGame(360, "Half-Life 2: Deathmatch"), OwnedGame(70, "Half-Life"),
                   OwnedGame(684410, "Bridge Constructor Portal")]
        self.assertEqual([g.app for g in predict_results(library, search_text("Half-Life 2"))], [70, 220, 360])
        self.assertEqual([g.app for g in predict_results(library, "PORTAL")], [684410, 400, 620])

    def test_result_count_is_read_or_none(self):
        from playden_tester.playden_ui import PlaydenUI
        from playden_tester.screen import Line
        ui = PlaydenUI(None, None)
        self.assertEqual(ui.result_count([Line("2 games · Some game details", 96, 704, 300, 20)]), 2)
        self.assertEqual(ui.result_count([Line("1 games · Some", 96, 704, 300, 20)]), 1)
        self.assertEqual(ui.result_count([Line("O games · Some game details", 96, 704, 300, 20)]), 0)
        self.assertIsNone(ui.result_count([Line("Some game details are unavailable.", 96, 704, 300, 20)]))


class DescriptionTest(unittest.TestCase):
    def test_description_on_install_and_play_pages(self):
        from playden_tester.playden_ui import description_text
        from playden_tester.screen import Line
        play = [Line("Play", 140, 672, 60, 20), Line("Cloud saves Synced", 400, 673, 200, 20),
                Line("Reawakened from stasis in the occupied metropolis of City 17, Gordon Freeman", 97, 775, 900, 25),
                Line("L 2/ R2 Read more page 1 of 2", 97, 879, 300, 20), Line("PLAYTIME", 1304, 696, 80, 12)]
        install = [Line("Install 286 MB", 136, 672, 160, 20),
                   Line("Installs to Console storage - 220.3 GB free", 97, 762, 400, 21),
                   Line("Return to the Black Mesa Research Facility as one of the military", 97, 817, 900, 25)]
        self.assertTrue(description_text(play).startswith("Reawakened from stasis"))
        self.assertNotIn("Read more", description_text(play))
        self.assertTrue(description_text(install).startswith("Return to the Black Mesa"))


class RefusedTest(unittest.TestCase):
    def test_refused_game_gets_a_refused_draft(self):
        import tempfile
        from playden_tester.report import RunWriter
        from playden_tester.runner import Result
        with tempfile.TemporaryDirectory() as folder:
            writer = RunWriter(folder, {})
            r = Result("", "A Way Out", 1222700, status="refused",
                       detail="Can't play A Way Out - Steam lists no Windows program this console can start")
            writer.add(r)
            path = writer.write_issue(r, "| Field | Value |", "refused-1222700-logs.zip")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "refused-1222700.md")
            self.assertIn("\u26d4 Refused", text)
            self.assertIn("no Windows program", text)
            self.assertIn("Downloaded in Playden, then pressed Play.", text)
