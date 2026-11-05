import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from playden_tester import payloadmgr
from playden_tester.console import Console, LaunchError
from playden_tester.padd import PaddError
from playden_tester.capture import check_frames
from playden_tester.playden_ui import PlaydenUI, UIError
from playden_tester.recovery import Healer, assign_pad, dialog_action
from playden_tester.runner import Result, Runner, Settings
from playden_tester.screen import Line


def line(text, x=100, y=100):
    return Line(text, x, y, 300, 30)


class FakeScreen:
    def __init__(self, *reads):
        self.reads = list(reads)

    def read(self, settle=0.8, region=None):
        lines = self.reads.pop(0) if len(self.reads) > 1 else self.reads[0]
        return lines, None, "frame.png"


class PadDialogTest(unittest.TestCase):
    def test_cross_goes_only_to_the_dialog(self):
        padd = mock.Mock()
        screen = FakeScreen([line("Home")], [line("Who's using this controller?")], [line("Home")])
        self.assertTrue(assign_pad(padd, screen, sleep=lambda _: None))
        padd.press.assert_called_once_with("cross")

    def test_nothing_is_pressed_without_the_dialog(self):
        padd = mock.Mock()
        ticks = iter(range(0, 100, 5))
        self.assertFalse(assign_pad(padd, FakeScreen([line("Home")]), clock=lambda: next(ticks), sleep=lambda _: None))
        padd.press.assert_not_called()


class DialogTest(unittest.TestCase):
    def test_buttons(self):
        self.assertEqual(dialog_action([line("Can't start the game or app."), line("CE-105773-3")]), "cross")
        self.assertIsNone(dialog_action([line("Library"), line("Settings")]))
        self.assertIsNone(dialog_action([line("Since 1998, a place100 race")]))  # no error code here

    def test_anything_that_can_remove_is_left_with_circle(self):
        self.assertEqual(dialog_action([line("Uninstall 1 game?"), line("An error has occurred")]), "circle")
        self.assertEqual(dialog_action([line("Clean up")]), "circle")


class HealerTest(unittest.TestCase):
    def healer(self, **console):
        fake = mock.Mock(host="192.0.2.1", **console)
        ui = mock.Mock()
        ui.read.return_value = ([line("Library")], None, "x")
        return Healer(fake, ui, mock.Mock(), say=lambda _: None, sleep=lambda _: None), fake, ui

    def test_a_stopped_file_manager_is_restarted(self):
        healer, console, _ = self.healer()
        console.port_open.side_effect = [False, True, True]
        console.has_padd.return_value = True
        healer.payloads.find.return_value = "/data/pldmgr/ps5-web-file-manager.elf"
        self.assertTrue(healer.services())
        healer.payloads.load.assert_called_once_with("/data/pldmgr/ps5-web-file-manager.elf")

    def test_healing_closes_a_left_game(self):
        healer, console, _ = self.healer()
        console.port_open.return_value = True
        console.running_titles.return_value = {"FAKE78001", "FAKE77031", "NPXS40000"}
        self.assertTrue(healer.heal("test"))
        console.close.assert_called_once_with("FAKE78001")

    def test_a_dead_service_ends_it(self):
        healer, console, _ = self.healer()
        console.port_open.return_value = False
        console.has_padd.return_value = False
        healer.payloads.find.return_value = None
        self.assertFalse(healer.heal("test"))
        console.close.assert_not_called()


class RoomTest(unittest.TestCase):
    def test_a_stuck_uninstall_is_tried_again_after_the_rest(self):
        from playden_tester.campaign import Campaign
        from playden_tester.runner import Settings as Plain
        console = mock.Mock()
        console.files.list.return_value = [{"name": "FAKE78001_x"}, {"name": "FAKE78002_x"}]
        with tempfile.TemporaryDirectory() as folder:
            campaign = Campaign(console, None, None, Plain(), folder, {})
            campaign.state = {
                "1": {"app": 1, "title": "Stuck", "ps5_title": "FAKE78001", "status": "survived", "uninstall_error": "x"},
                "2": {"app": 2, "title": "Normal", "ps5_title": "FAKE78002", "status": "survived"},
            }
            with mock.patch.object(campaign, "titles", return_value={"FAKE78001", "FAKE78002"}):
                self.assertEqual([e["title"] for e in campaign.evictable()], ["Normal"])
                self.assertEqual([e["title"] for e in campaign.stuck()], ["Stuck"])


class DiskTest(unittest.TestCase):
    def test_real_drives_only(self):
        report = {"/data": {"bytes": 2 ** 40, "free": 2 ** 39, "available": 2 ** 38, "device": "/user/data"},
                  "/mnt/usb0": {"bytes": 2 ** 21, "free": 2 ** 20, "available": 2 ** 20, "device": "tmpfs"}}
        with mock.patch.object(payloadmgr, "run_elf", return_value=json.dumps(report)):
            drives = payloadmgr.disk_free("192.0.2.1", b"elf", 9021)
        self.assertEqual(drives, {"/data": {"total_gb": 1024.0, "free_gb": 512.0, "available_gb": 256.0}})


class CleanUpTest(unittest.TestCase):
    def ui(self, *focused):
        ui = PlaydenUI(mock.Mock(), mock.Mock(), say=lambda _: None)
        ui._storage_page = mock.Mock()
        ui._storage_row = mock.Mock(return_value="Unused game settings data 44")
        ui.press = mock.Mock()
        reads = [([line(text)], (0, 0, 2000, 2000), "x") for text in focused]
        ui.read = mock.Mock(side_effect=reads)
        return ui

    def test_presses_only_clean_up(self):
        ui = self.ui("Clean up", "Storage")
        self.assertIn("44", ui.clean_unused())
        self.assertEqual(ui.press.call_args_list[-1].args, ("cross",))

    def test_backs_out_of_anything_else(self):
        for text in ("Kept game data", "Delete saves too"):
            ui = self.ui(text)
            with self.assertRaises(UIError):
                ui.clean_unused()
            self.assertEqual(ui.press.call_args_list[-1].args, ("circle",))


class FramesCapture:
    def __init__(self, motion, before, after):
        self.motion, self.frames = motion, [before, after]

    def check(self, seconds):
        return check_frames([bytes(100), bytes([self.motion]) * 100])

    def frame(self):
        return self.frames.pop(0)


class ProbeTest(unittest.TestCase):
    def probe(self, motion, before, after):
        console = mock.Mock()
        runner = Runner(console, Settings(probe=True), say=lambda _: None, sleep=lambda _: None,
                        capture=FramesCapture(motion, before, after))
        result = Result("FAKE78001", "Game")
        runner._probe(result)
        return result.input_response, console

    def test_a_game_that_reacts(self):
        verdict, console = self.probe(0, bytes(100), bytes([200]) * 100)
        self.assertEqual(verdict, "responded")
        self.assertEqual(console.padd.press.call_count, 3)

    def test_a_game_that_does_not(self):
        self.assertEqual(self.probe(0, bytes(100), bytes(100))[0], "no_change")

    def test_a_busy_picture_cannot_be_told_apart(self):
        self.assertEqual(self.probe(50, bytes(100), bytes([60]) * 100)[0], "unknown")


class NudgeTest(unittest.TestCase):
    def test_it_comes_before_the_first_screenshot_and_is_reported(self):
        order = []
        console = mock.Mock()
        console.is_running.return_value = True
        console.title_log.return_value = ""
        console.padd.stick.side_effect = lambda *a: order.append("stick")
        console.padd.press.side_effect = lambda *a: order.append("press")
        capture = mock.Mock()
        capture.snapshot.side_effect = lambda path: order.append("shot") or Path(path)
        capture.check.return_value = check_frames([bytes(100), bytes(100)])
        rng = mock.Mock()
        rng.uniform.return_value = 0.0
        rng.choice.return_value = "left"
        now = [0.0]

        def sleep(seconds):
            now[0] += seconds

        runner = Runner(console, Settings(nudge=True, first_shot=30, watch=40, auto_close=True, poll=5, close_timeout=5),
                        say=lambda _: None, clock=lambda: now[0], sleep=sleep, capture=capture, shots="shots", rng=rng)
        console.is_running.side_effect = [True] * 12 + [False] * 5
        game = mock.Mock(title="FAKE78001", steam_app=1)
        game.name = "Game"
        result = runner.run(game)
        self.assertEqual(order[:3], ["stick", "press", "shot"])
        console.padd.stick.assert_called_once_with("left", 1.0, 0.0, 0.5)
        console.padd.press.assert_called_once_with("left")
        self.assertIn("d-pad left", result.detail)

    def test_every_direction_can_come_up(self):
        from playden_tester.runner import DPAD
        self.assertEqual(sorted(DPAD), ["down", "left", "right", "up"])

    def test_off_by_default(self):
        self.assertFalse(Settings().nudge)


class CloseTest(unittest.TestCase):
    def console(self, processes, refusal=None):
        padd = mock.Mock()
        padd.close_app.side_effect = refusal
        console = Console(mock.Mock(), "192.0.2.1", padd=padd)
        console.is_running = mock.Mock(return_value=True)
        console.game_processes = mock.Mock(side_effect=processes)
        return console

    def test_a_folder_left_by_a_closed_game_does_not_count(self):
        self.console([{1}, set()]).close("FAKE78010", timeout=0)

    def test_nothing_left_to_close_is_not_an_error(self):
        self.console([set()], PaddError("close refused: SCE error 0xffffffff")).close("FAKE78010", timeout=0)

    def test_a_game_that_really_stays_is_an_error(self):
        with self.assertRaises(LaunchError):
            self.console([{1}, {1}]).close("FAKE78010", timeout=0)

    def test_an_unknown_process_count_is_an_error(self):
        with self.assertRaises(LaunchError):
            self.console([None, None]).close("FAKE78010", timeout=0)

    def test_another_refusal_is_still_an_error(self):
        with self.assertRaises(LaunchError):
            self.console([{1}], PaddError("close refused: SCE error 0x80940033")).close("FAKE78010")


class LeftoverFolderTest(unittest.TestCase):
    def console(self, counts):
        console = Console(mock.Mock(), "192.0.2.1", padd=mock.Mock())
        console.game_processes = mock.Mock(side_effect=counts)
        console.running_titles = mock.Mock(return_value={"FAKE78010"})
        console.left_behind["FAKE78010"] = None
        return console

    def test_a_closed_title_is_not_running_whatever_its_folder_says(self):
        self.assertFalse(self.console([set()]).is_running("FAKE78010"))

    def test_it_starts_from_the_tile_and_never_the_helper(self):
        console = self.console([{1}, {1, 2}, {1, 2}])
        console.tile_launch = mock.Mock()
        console.launch("FAKE78010")
        console.tile_launch.assert_called_once_with("FAKE78010")
        console.files.launch_elf.assert_not_called()
        self.assertTrue(console.is_running("FAKE78010"))

    def test_the_game_quitting_is_seen_by_its_process(self):
        console = self.console([{1}, {1, 2}, {1}])
        console.tile_launch = mock.Mock()
        console.launch("FAKE78010")
        self.assertFalse(console.is_running("FAKE78010"))

    def test_a_game_that_replaced_playden_counts_as_started(self):
        console = self.console([{1}, {2}, {2}])
        console.tile_launch = mock.Mock()
        console.launch("FAKE78010")
        self.assertTrue(console.is_running("FAKE78010"))

    def test_without_a_way_to_press_the_tile_it_says_so(self):
        with self.assertRaisesRegex(LaunchError, "leftover folder"):
            self.console([{1}]).launch("FAKE78010")

    def test_a_folder_that_went_means_the_normal_launch(self):
        console = self.console([])
        console.running_titles.return_value = set()
        console.port_open = mock.Mock(return_value=False)
        with self.assertRaisesRegex(LaunchError, "elfldr"):
            console.launch("FAKE78010")
        self.assertEqual(console.left_behind, {})

    def test_a_refused_close_remembers_the_title(self):
        console = Console(mock.Mock(), "192.0.2.1", padd=mock.Mock())
        console.padd.close_app.side_effect = PaddError("close refused: SCE error 0xffffffff")
        console.game_processes = mock.Mock(return_value=set())
        console.close("FAKE78010")
        self.assertIn("FAKE78010", console.left_behind)

    def test_playden_is_never_taken_for_one(self):
        console = Console(mock.Mock(), "192.0.2.1", padd=mock.Mock())
        console.padd.close_app.side_effect = PaddError("close refused: SCE error 0xffffffff")
        console.game_processes = mock.Mock(return_value=set())
        console.close("FAKE77031")
        self.assertEqual(console.left_behind, {})


class HomeTileTest(unittest.TestCase):
    def ui(self, *reads):
        ui = PlaydenUI(mock.Mock(), mock.Mock(), say=lambda _: None)
        ui.press = mock.Mock()
        ui.read = mock.Mock(side_effect=[(lines, None, "x") for lines in reads])
        return ui

    def page(self, name):
        return [line(name, 442, 263), line(name, 177, 707), line("Play Game", 266, 870)]

    def test_it_presses_the_exact_game_only(self):
        ui = self.ui(*[self.page("Escape Simulator 2")] * 3, self.page("Escape Simulator"))
        with mock.patch("time.sleep"):
            self.assertTrue(ui.start_from_ps_home("Escape Simulator"))
        self.assertEqual([c.args[0] for c in ui.press.call_args_list], ["right", "cross"])

    def test_a_page_still_sliding_is_read_again(self):
        sliding = [line("Play Game", 241, 818)]
        ui = self.ui(sliding, [line("Iconoclasts", 465, 216), line("Play Game", 242, 820)])
        with mock.patch("time.sleep"):
            self.assertTrue(ui.start_from_ps_home("Iconoclasts"))
        self.assertEqual([c.args[0] for c in ui.press.call_args_list], ["cross"])

    def test_nothing_running_is_fine(self):
        ui = self.ui(self.page("Iconoclasts"))
        ui.pad.home.side_effect = PaddError("home refused: SCE error 0xffffffff")
        with mock.patch("time.sleep"):
            self.assertTrue(ui.start_from_ps_home("Iconoclasts"))

    def test_cross_never_goes_to_an_open_menu(self):
        menu = self.page("Iconoclasts") + [line("Delete", 395, 366)]
        ui = self.ui(*[menu] * 126)
        with mock.patch("time.sleep"):
            self.assertFalse(ui.start_from_ps_home("Iconoclasts"))
        self.assertNotIn("cross", [c.args[0] for c in ui.press.call_args_list])


class ClipTest(unittest.TestCase):
    def test_a_passing_game_keeps_no_video(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "a.mp4").write_bytes(b"x")
            runner = Runner(mock.Mock(), Settings(), shots=folder)
            good = Result("t", "n", status="survived", clip="a.mp4")
            runner._keep_clip(good)
            self.assertEqual(good.clip, "")
            self.assertFalse((Path(folder) / "a.mp4").exists())

    def test_a_failed_game_keeps_it(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "a.mp4").write_bytes(b"x")
            bad = Result("t", "n", status="crashed", clip="a.mp4")
            Runner(mock.Mock(), Settings(), shots=folder)._keep_clip(bad)
            self.assertTrue((Path(folder) / "a.mp4").exists())


if __name__ == "__main__":
    unittest.main()
