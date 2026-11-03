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


class ReportedTest(unittest.TestCase):
    GAMES = [{"app": 892970, "title": "Valheim"}, {"app": 239140, "title": "Dying Light"},
             {"app": 1332010, "title": "Stray"}, {"app": 220, "title": "Half-Life 2"}]

    @staticmethod
    def issue(number, title, body="", label="test report"):
        return {"number": number, "title": title, "body": body, "state": "open", "html_url": f"u/{number}",
                "labels": [{"name": label}]}

    def test_store_link_and_title_count_for_test_reports_only(self):
        from playden_tester.reported import reported_games
        issues = [
            self.issue(1, "[Test] Valheim", "Valheim - https://store.steampowered.com/app/892970/Valheim/"),
            self.issue(2, "[Test] Half Life 2 (with -gamepadui)", "https://steamdb.info/app/220/"),
            self.issue(3, "[Test] Dying Light"),
            # Another game whose name holds one of ours: its own store page, not Dying Light's.
            self.issue(4, "[Test] Dying Light: The Beast", "https://store.steampowered.com/app/3008130/"),
            self.issue(5, "[[Test] <Stray Gods: The Roleplay Musical>"),
            self.issue(6, "Stray crashes", "https://store.steampowered.com/app/1332010/", label="bug"),
        ]
        found = reported_games(issues, self.GAMES)
        self.assertEqual(sorted(found), [220, 239140, 892970])
        self.assertEqual([i["number"] for i in found[892970]], [1])


class PortsTest(unittest.TestCase):
    def test_ranks_and_campaign_order(self):
        import json
        import tempfile
        from pathlib import Path
        from playden_tester.campaign import load_list
        from playden_tester.ports import NO_PORT, OLD_PLAYSTATION_PORT, OTHER_PORT, PLAYSTATION_PORT, console_ports
        self.assertEqual(console_ports({"Q1406"}), (NO_PORT, []))
        self.assertEqual(console_ports({"Q1406", "Q19610114"}), (OTHER_PORT, ["Nintendo Switch"]))
        self.assertEqual(console_ports({"Q13361286", "Q63184502"}), (PLAYSTATION_PORT, ["PlayStation 5", "Xbox One"]))
        self.assertEqual(console_ports({"Q13361286", "Q10683"}), (OLD_PLAYSTATION_PORT, ["PlayStation 3", "Xbox One"]))
        rows = [{"app": 1, "title": "On PS5"}, {"app": 6, "title": "On PS3"}, {"app": 2, "title": "PC only"},
                {"app": 3, "title": "On Switch"}, {"app": 4, "title": "Installed, on PS5", "installed": True},
                {"app": 5, "title": "Not on Wikidata"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "list.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            games = load_list(path, {1: PLAYSTATION_PORT, 2: NO_PORT, 3: OTHER_PORT, 4: PLAYSTATION_PORT,
                                     6: OLD_PLAYSTATION_PORT})
        self.assertEqual([g.app for g in games], [4, 2, 5, 3, 6, 1])


class ProtonDBTest(unittest.TestCase):
    def test_tiers_go_before_ports(self):
        import json
        import tempfile
        from pathlib import Path
        from playden_tester.campaign import load_list
        from playden_tester.ports import NO_PORT, PLAYSTATION_PORT
        from playden_tester.protondb import UNRATED, tier_rank
        self.assertEqual([tier_rank(t) for t in ("platinum", "gold", "borked", "pending", "unknown")],
                         [0, 1, 4, UNRATED, UNRATED])
        rows = [{"app": 1, "title": "Gold, PC only"}, {"app": 2, "title": "Platinum, on PS5"},
                {"app": 3, "title": "Not looked up"}, {"app": 4, "title": "Borked, installed", "installed": True},
                {"app": 5, "title": "Gold, on PS5"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "list.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            games = load_list(path, {1: NO_PORT, 2: PLAYSTATION_PORT, 5: PLAYSTATION_PORT}, None,
                              {1: tier_rank("gold"), 2: tier_rank("platinum"), 4: tier_rank("borked"),
                               5: tier_rank("gold")})
        self.assertEqual([g.app for g in games], [4, 2, 1, 5, 3])


class ReportFolderTest(unittest.TestCase):
    def test_folder_has_screenshot_zip_and_issue(self):
        import json
        import tempfile
        from pathlib import Path
        from playden_tester.campaign import Campaign, slug
        from playden_tester.library import OwnedGame
        from playden_tester.report import RunWriter
        from playden_tester.runner import Result
        from playden_tester.webaccess import WebAccessError
        self.assertEqual(slug("BioShock™ 2: Remastered"), "bioshock-2-remastered")

        class Web:
            def __init__(self, fail):
                self.fail, self.asked = fail, []

            def report_zip(self, title, path):
                self.asked.append(title)
                if self.fail:
                    raise WebAccessError("not answering")
                path.write_bytes(b"PK zip")

        with tempfile.TemporaryDirectory() as folder:
            out, reports = Path(folder) / "campaign", Path(folder) / "reports"
            for fail in (False, True):
                campaign = Campaign.__new__(Campaign)
                campaign.out, campaign.reports, campaign.web = out, reports, Web(fail)
                campaign.writer, campaign.say = RunWriter(out, {}), lambda text: None
                game = OwnedGame(8850, "BioShock 2")
                result = Result("FAKE78012", "BioShock 2", 8850, status="survived", screen={"verdict": "moving", "brightness": 80, "motion": 5.0},
                                screenshot="FAKE78012.jpg", started_at="2026-11-03 18:00:00")
                (out / "FAKE78012.jpg").write_bytes(b"jpg")
                (out / "logs").mkdir(exist_ok=True)
                (out / "logs" / "own.zip").write_bytes(b"PK own")
                campaign.save_screenshot(game, result)
                campaign.save_report(game, "FAKE78012", result, "| firmware | 12.20 |", out / "logs" / "own.zip")
                game_folder = reports / "8850-bioshock-2"
                issue = (game_folder / "issue.md").read_text(encoding="utf-8")
                zip_name = "logs.zip" if fail else "playden-report.zip"
                self.assertEqual(campaign.web.asked, ["FAKE78012"])
                self.assertTrue((game_folder / zip_name).exists())
                self.assertEqual((game_folder / "screenshot.jpg").read_bytes(), b"jpg")
                self.assertIn(f"`{zip_name}` (attach it), and `screenshot.jpg`.", issue)
                self.assertIn("### Result\n\n✅ Works", issue)
                self.assertEqual(json.loads((game_folder / "result.json").read_text(encoding="utf-8"))["status"],
                                 "survived")


class PrepareStateTest(unittest.TestCase):
    def test_prepare_state_from_runtime_log(self):
        from playden_tester.campaign import prepare_state
        log = "\n".join([
            "2026-11-03T18:45:59Z prepare reserved app=1696770 title=FAKE78023 ms=1436",
            "2026-11-03T18:46:01Z prepare start app=1696770 root=/data/playden-games/1696770 ok=1 ms=3494 message=",
            "2026-11-03T18:47:11Z prepare step app=1696770 from=publish-profile step_ms=1345 publish_ms=2928 ok=1 "
            "error=0 state=3 to= code=- message=",
            "2026-11-03T18:47:12Z prepare result app=1696770 ready",
            "2026-11-03T18:49:37Z prepare reserved app=2386720 title=FAKE78024 ms=1202",
            "2026-11-03T18:50:10Z prepare step app=2386720 from=stage-title step_ms=29824 publish_ms=1080 ok=1 "
            "error=0 state=1 to=copy-template code=- message=",
            "2026-11-03T18:51:00Z prepare step app=23867 from=stage-title ok=0 error=5 message=no space",
            "2026-11-03T18:51:00Z admission check title=FAKE78024 result=ok",
        ])
        self.assertEqual(prepare_state(log, 1696770)[0], "ready")
        self.assertEqual(prepare_state(log, 2386720)[0], "preparing")
        self.assertEqual(prepare_state(log, 23867)[0], "failed")
        self.assertEqual(prepare_state(log, 70), (None, ""))


class ListsTest(unittest.TestCase):
    def test_still_to_test(self):
        from playden_tester.campaign import done_apps
        from playden_tester.lists import note, still_to_test
        games = [{"app": 1, "title": "Tested", "controller": "full"}, {"app": 2, "title": "Error", "controller": "full"},
                 {"app": 3, "title": "Reported", "controller": "full"}, {"app": 4, "title": "New", "controller": "full"},
                 {"app": 5, "title": "Partial", "controller": "partial"}, {"app": 6, "title": "Deferred", "controller": "full"},
                 {"app": 7, "title": "No pad", "controller": "none"}]
        state = {"1": {"status": "survived"}, "2": {"status": "error", "detail": "could not select the library tab"},
                 "6": {"status": "deferred"}}
        todo = still_to_test(games, {3}, done_apps(state))
        self.assertEqual([g["app"] for g in todo], [2, 4, 5, 6])
        self.assertEqual(note(todo[0], state), "Full controller support; retest: could not select the library tab")
        self.assertEqual(note(todo[1], state), "Full controller support")
        self.assertEqual(note(todo[2], state), "Partial controller support")

    def test_partial_after_full_from_several_lists(self):
        import json
        import tempfile
        from pathlib import Path
        from playden_tester.campaign import load_list
        from playden_tester.protondb import tier_rank
        full = [{"app": 1, "title": "Full, gold", "controller": "full"},
                {"app": 2, "title": "Full, pending", "controller": "full"}]
        partial = [{"app": 3, "title": "Partial, platinum", "controller": "partial"},
                   {"app": 1, "title": "Listed twice", "controller": "partial"},
                   {"app": 4, "title": "Partial, installed", "controller": "partial", "installed": True}]
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / "full.json", Path(folder) / "partial.json", Path(folder) / "missing.json"]
            paths[0].write_text(json.dumps(full), encoding="utf-8")
            paths[1].write_text(json.dumps(partial), encoding="utf-8")
            games = load_list(paths, None, None, {1: tier_rank("gold"), 3: tier_rank("platinum")})
        self.assertEqual([(g.app, g.controller) for g in games], [(4, "partial"), (1, "full"), (2, "full"),
                                                                 (3, "partial")])

    def test_partial_from_store_category(self):
        import io
        import json
        from unittest import mock
        from playden_tester import library
        entry = {"10": {"success": True, "data": {"type": "game", "platforms": {"windows": True},
                                                 "categories": [{"id": 2, "description": "Single-player"},
                                                                {"id": 18, "description": "Partial Controller Support"}]}}}
        with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(entry).encode())):
            self.assertEqual(library.store_details(10)["controller"], "partial")

    def test_years(self):
        from playden_tester.lists import release_year, steam_year
        self.assertEqual([steam_year(d) for d in ("Jun 20, 2024", "14 Nov, 2011", "Coming soon", "")],
                         [2024, 2011, None, None])
        years = {"wikidata": {"1": 2008}, "steam": {"1": {"year": 2009}, "2": {"year": 2020}, "3": {"year": None}}}
        self.assertEqual([release_year(app, years) for app in (1, 2, 3)], [2008, 2020, None])

    def test_by_players(self):
        from playden_tester.lists import by_players_markdown
        rows = [{"app": 1, "title": "Quiet"}, {"app": 2, "title": "Popular | big"}, {"app": 3, "title": "Unknown"}]
        text = by_players_markdown(rows, {"1": {"avg": 12.4, "peak": 30}, "2": {"avg": 1500.0, "peak": 2500},
                                          "3": None}, {2: ["PlayStation 5"]}, "2026-11-02")
        table = [line for line in text.splitlines() if line[:3] in ("| 1", "| 2", "| 3")]
        self.assertEqual(table, ["| 1 | Popular \\| big | 1,500 | 2,500 | – | 2 | – | PlayStation 5 | 2 |",
                                 "| 2 | Quiet | 12 | 30 | – | 1 | – | – | 1 |",
                                 "| 3 | Unknown | – | – | – | 3 | – | – | 3 |"])
        self.assertIn("no numbers for 1 of the games", text)

    def test_steamcharts_page(self):
        from playden_tester.players import last_30_days
        html = ('<td class="month-cell left italic">Last 30 Days</td>\n<td class="right num-f italic">674.99</td>\n'
                '<td class="right num-p gainorloss italic">&#43;6.5</td>\n<td class="right gainorloss italic">&#43;0.98%'
                '</td>\n<td class="right num italic">1,486</td>')
        self.assertEqual(last_30_days(html), {"avg": 674.99, "peak": 1486})
        self.assertIsNone(last_30_days("<html>no data</html>"))


class CompatibilityTest(unittest.TestCase):
    def test_rows_with_a_store_link(self):
        from playden_tester.reported import compatibility_games
        text = ("| Game | Result | Kit |\n| --- | --- | --- |\n"
                "| [Celeste](https://store.steampowered.com/app/504230) | ✅ Works | 0.10 |\n"
                "| [LIMBO](https://store.steampowered.com/app/48000/LIMBO/) | ❌ Broken | 0.12 |\n"
                "| [Not ours](https://store.steampowered.com/app/1) | ✅ Works | 0.10 |\n")
        found = compatibility_games(text, [{"app": 504230, "title": "Celeste"}, {"app": 48000, "title": "LIMBO"},
                                           {"app": 70, "title": "Half-Life"}])
        self.assertEqual(sorted(found), [48000, 504230])
        self.assertEqual(found[48000][0]["state"], "❌ Broken")


class StoreFeaturesTest(unittest.TestCase):
    def test_page_flags(self):
        from playden_tester.storefeatures import page_flags
        html = ('<div>Uses Kernel Level Anti-Cheat</div><div class="anticheat_name">Easy Anti-Cheat'
                '<span class="anticheat_uninstalls"> - Requires manual removal after game uninstall</span></div>')
        self.assertEqual(page_flags(html), (["Easy Anti-Cheat"], False))
        self.assertEqual(page_flags('"loc_token":"#SteamDeckVerified_TestResult_UnsupportedAntiCheat_Other"'),
                         ([], True))
        self.assertEqual(page_flags("<a>Minion Masters - Vanguard</a>"), ([], False))

    def test_pads_and_multiplayer_anticheat(self):
        from playden_tester.storefeatures import DUALSENSE, DUALSHOCK, NO_PAD, multiplayer_anticheat, pad_rank
        self.assertEqual(pad_rank(["DualShock Controller Support", "DualSense Controller Support"]), DUALSENSE)
        self.assertEqual(pad_rank(["DualShock Controller Support"]), DUALSHOCK)
        self.assertEqual(pad_rank(None), NO_PAD)
        games = [{"app": 1, "title": "Notice"}, {"app": 2, "title": "Deck"}, {"app": 3, "title": "VAC solo"},
                 {"app": 4, "title": "Listed"}, {"app": 5, "title": "Clean"}]
        cache = {"1": {"categories": ["Online PvP"], "notice": ["Easy Anti-Cheat"], "deck_anticheat": False},
                 "2": {"categories": ["Multi-player"], "notice": [], "deck_anticheat": True},
                 "3": {"categories": ["Single-player", "Valve Anti-Cheat enabled"], "notice": [], "deck_anticheat": False},
                 "4": {"categories": ["Single-player", "Co-op"], "notice": [], "deck_anticheat": False},
                 "5": {"categories": ["Multi-player"], "notice": [], "deck_anticheat": False}}
        rows = {row["app"]: row for row in multiplayer_anticheat(games, cache, {4: ["BattlEye"]})}
        self.assertEqual(sorted(rows), [1, 2, 4])  # 3 has no multiplayer
        self.assertEqual(rows[1]["anticheats"], ["Easy Anti-Cheat"])
        self.assertEqual(rows[4]["anticheats"], ["BattlEye"])
        from playden_tester.storefeatures import anticheats
        self.assertEqual(anticheats({"notice": ["VAC (Valve Anti-Cheat)"], "categories": ["Valve Anti-Cheat enabled"]},
                                    ["Valve Anti-Cheat", "Easy Anti-Cheat"]), ["VAC", "Easy Anti-Cheat"])
        self.assertTrue(rows[4]["single_player"])

    def test_campaign_order_with_pads(self):
        import json
        import tempfile
        from pathlib import Path
        from playden_tester.campaign import load_list
        from playden_tester.storefeatures import DUALSENSE, DUALSHOCK
        rows = [{"app": 1, "title": "Neither"}, {"app": 2, "title": "DualShock"}, {"app": 3, "title": "DualSense"},
                {"app": 4, "title": "On PS5, DualSense"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "list.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            games = load_list(path, {4: 3}, {2: DUALSHOCK, 3: DUALSENSE, 4: DUALSENSE})
        self.assertEqual([g.app for g in games], [3, 2, 1, 4])
