import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from playden_tester import mcp, rig
from playden_tester.payloadmgr import PayloadManager, PayloadManagerError
from playden_tester.remoteplay import RemotePlayError, RemoteView, parse_discovery
from playden_tester.rig import Rig, RigError, check_delete, check_private, clean_path


class Files:
    def __init__(self):
        self.deleted, self.read = [], []

    def list(self, path):
        return [{"name": "old.log", "size": 12}]

    def write_text(self, path, text):
        raise AssertionError("must be refused first")

    def read_text(self, path):
        self.read.append(path)
        return "text", "1"

    def download(self, path):
        self.read.append(path)
        return b"data"

    def delete(self, path):
        self.deleted.append(path)


def offline_rig(root):
    made = Rig("192.0.2.1", root=root)
    made.files = made.console.files = Files()
    return made


class PathRulesTest(unittest.TestCase):
    def test_paths_are_resolved(self):
        self.assertEqual(clean_path("/data/a/../b/"), "/data/b")
        with self.assertRaises(RigError):
            clean_path("data/b")

    def test_session_is_refused_however_it_is_written(self):
        for path in ("/data/playden/user/session.v1", "/data/playden/user/x/../session.v1",
                     "//data/playden/user/session.v1", "/data/playden/USER/Session.V1"):
            with self.assertRaises(RigError, msg=path):
                check_private(path)

    def test_folders_holding_the_session_cannot_be_downloaded(self):
        for path in ("/data/playden/user", "/data/playden", "/data", "/"):
            check_private(path)  # listing and reading a folder's own path is not the sign-in
            with self.assertRaises(RigError, msg=path):
                check_private(path, tree=True)
        check_private("/data/playden/user/library-1.cache", tree=True)
        check_private("/data/playden/logs", tree=True)

    def test_deletes_stay_inside_the_allowed_folders(self):
        check_delete("/data/playden-tester/old.log")
        for path in ("/data/playden-tester", "/data/playden-tester/../playden/x", "/data/playden-games/1", "/system"):
            with self.assertRaises(RigError, msg=path):
                check_delete(path)
        with mock.patch.dict("os.environ", {"PS5_DELETE_ROOTS": "/data/scratch"}):
            check_delete("/data/scratch/a")


class RigTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.rig = offline_rig(self.root)

    def test_delete_is_a_dry_run_unless_told(self):
        self.assertFalse(self.rig.file_delete("/data/playden-tester/old.log")["deleted"])
        self.assertEqual(self.rig.files.deleted, [])
        self.assertTrue(self.rig.file_delete("/data/playden-tester/old.log", dry_run=False)["deleted"])
        self.assertEqual(self.rig.files.deleted, ["/data/playden-tester/old.log"])
        self.assertIn("old.log", (self.root / "results" / "rig-actions.log").read_text())

    def test_file_tools_never_reach_the_session(self):
        for call in (lambda: self.rig.file_read("/data/playden/user/session.v1"),
                     lambda: self.rig.file_download("/data/playden/user", str(self.root / "x")),
                     lambda: self.rig.file_write("/data/playden/user/session.v1", "x")):
            with self.assertRaises(RigError):
                call()
        self.assertEqual(self.rig.files.read, [])

    def test_a_running_campaign_keeps_the_pad(self):
        self.rig.console.padd = mock.Mock()
        with mock.patch.object(rig, "process_alive", return_value=True):
            self.rig.campaign_dir.mkdir(parents=True)
            (self.rig.campaign_dir / "run.pid").write_text("1234")
            with self.assertRaises(RigError):
                self.rig.press(["cross"])
            self.rig.campaign_stop()
            self.assertTrue(self.rig.campaign_status()["stopping"])
        self.rig.console.padd.press.assert_not_called()

    def test_power_needs_its_action_and_payload(self):
        with self.assertRaises(RigError):
            self.rig.power("explode")
        with self.assertRaisesRegex(RigError, "build-payloads"):
            self.rig.power("restart")


class RemotePlayTest(unittest.TestCase):
    def test_discovery_reply(self):
        reply = b"HTTP/1.1 200 Ok\nhost-id:B40AD81D8B9B\nhost-type:PS5\nhost-name:PS5-065\nsystem-version:12200005\n"
        self.assertEqual(parse_discovery(reply), {"state": "ready", "name": "PS5-065", "type": "PS5",
                                                  "firmware": "12200005", "running_app": None})
        self.assertEqual(parse_discovery(b"HTTP/1.1 620 Server Standby\nhost-type:PS5\n")["state"], "standby")

    def test_wake_leaves_an_awake_console_alone(self):
        made = offline_rig(Path(tempfile.gettempdir()))
        made.view = mock.Mock()
        with mock.patch.object(rig, "discover", return_value={"state": "ready", "name": "PS5-065"}):
            self.assertEqual(made.wake()["state"], "ready")
        made.view.start.assert_not_called()

    def test_wake_refuses_a_console_that_is_off(self):
        made = offline_rig(Path(tempfile.gettempdir()))
        with mock.patch.object(rig, "discover", return_value=None), self.assertRaises(RemotePlayError):
            made.wake()

    def test_only_the_streams_own_window_is_grabbed(self):
        view = RemoteView("192.0.2.1", "PS5-065")
        view.process = mock.Mock(pid=4242)
        with mock.patch("playden_tester.remoteplay.window_of", return_value=None) as window, \
                mock.patch("subprocess.run") as run:
            self.assertFalse(view._grab("x.png"))
        window.assert_called_once_with(4242)
        run.assert_not_called()

    def test_a_closed_view_is_reported(self):
        view = RemoteView("192.0.2.1", "PS5-065")
        with mock.patch.object(view, "start"), self.assertRaisesRegex(RemotePlayError, "closed"):
            view.snapshot("x.png")


class PayloadManagerTest(unittest.TestCase):
    def test_kill_refuses_what_cannot_come_back(self):
        manager = PayloadManager("192.0.2.1")
        rows = [{"pid": 1, "name": "elfldr.elf"}, {"pid": 2, "name": "padd.elf"}]
        with mock.patch.object(manager, "processes", return_value=rows), mock.patch.object(manager, "_get") as get:
            with self.assertRaises(PayloadManagerError):
                manager.kill(1)
            with self.assertRaises(PayloadManagerError):
                manager.kill(3)
            self.assertEqual(manager.kill(2), "padd.elf")
        get.assert_called_once_with("/process_kill?pid=2")


class ProtocolTest(unittest.TestCase):
    def exchange(self, *messages):
        out = io.StringIO()
        stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
        with mock.patch("sys.stdout", io.StringIO()):
            mcp.serve(mock.Mock(), stdin, out)
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def test_handshake_and_list(self):
        replies = self.exchange({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                 "params": {"protocolVersion": "2025-03-26"}},
                                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                                {"jsonrpc": "2.0", "id": 3, "method": "nope"})
        self.assertEqual([r["id"] for r in replies], [1, 2, 3])  # the notification gets no reply
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-03-26")
        names = {tool["name"] for tool in replies[1]["result"]["tools"]}
        self.assertLessEqual({"status", "screenshot", "press", "file_delete", "power", "campaign_start"}, names)
        self.assertEqual(replies[2]["error"]["code"], -32601)

    def test_a_failure_is_a_result_the_agent_can_read(self):
        fake = mock.Mock()
        fake.status.side_effect = OSError("no route")
        result = mcp.call_tool(fake, "status", {})
        self.assertTrue(result["isError"])
        self.assertIn("no route", result["content"][0]["text"])

    def test_screenshot_comes_back_as_an_image(self):
        fake = mock.Mock()
        fake.screenshot.return_value = (b"jpeg", "C:/frame.png")
        result = mcp.call_tool(fake, "screenshot", {})
        self.assertEqual(result["content"][0]["type"], "image")
        self.assertEqual(result["content"][0]["data"], "anBlZw==")

    def test_rows_with_a_type_are_an_answer_not_content(self):
        fake = mock.Mock()
        fake.file_list.return_value = [{"name": "a", "type": "file"}]
        result = mcp.call_tool(fake, "file_list", {"path": "/data"})
        self.assertEqual(json.loads(result["content"][0]["text"]), [{"name": "a", "type": "file"}])

    def test_delete_defaults_to_a_dry_run_and_power_needs_confirm(self):
        fake = mock.Mock()
        fake.file_delete.return_value = {"deleted": False}
        mcp.call_tool(fake, "file_delete", {"path": "/data/playden-tester/a"})
        fake.file_delete.assert_called_once_with("/data/playden-tester/a", True)
        self.assertTrue(mcp.call_tool(fake, "power", {"action": "restart"})["isError"])
        fake.power.assert_not_called()


if __name__ == "__main__":
    unittest.main()
