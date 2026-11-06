import tempfile
import unittest
import zipfile
from pathlib import Path

from playden_tester.logs import save_run, session_stamp
from playden_tester.webaccess import WebAccessError

LOG = "== session-1.log\nPW_REPORT/1 build=a profile=b cycle=0 pid=1 time={}\nREC seq=1\n"


class FakeCollector:
    def __init__(self, stamp):
        self.stamp = stamp

    def collect(self, title, app, path, extra=None):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(f"logs/title-{title}.log", LOG.format(self.stamp))
        return "| Field | Value |\n"


class FakeWeb:
    def __init__(self, works=True):
        self.works = works

    def report_zip(self, title, path, tries=6, wait=10):
        if not self.works:
            raise WebAccessError("web access is off")
        path.write_bytes(b"PK")


class SaveRunTest(unittest.TestCase):
    def test_each_run_gets_its_own_numbered_folder(self):
        with tempfile.TemporaryDirectory() as root:
            first = save_run(FakeCollector(1), FakeWeb(), "FAKE1", root, "8x AA")
            second = save_run(FakeCollector(2), FakeWeb(), "FAKE1", root, "Direct3D 9!")
            self.assertEqual(first["folder"].name, "01-8x-aa")
            self.assertEqual(second["folder"].name, "02-direct3d-9")
            self.assertTrue((first["folder"] / "logs.zip").exists())
            self.assertTrue((second["folder"] / "playden-report.zip").exists())
            self.assertEqual(second["stale"], [])

    def test_the_same_session_twice_is_reported_as_stale(self):
        with tempfile.TemporaryDirectory() as root:
            save_run(FakeCollector(5), FakeWeb(), "FAKE1", root, "one")
            again = save_run(FakeCollector(5), FakeWeb(), "FAKE1", root, "two")
            self.assertEqual(again["stale"], ["01-one"])

    def test_a_run_is_kept_when_web_access_is_off(self):
        with tempfile.TemporaryDirectory() as root:
            saved = save_run(FakeCollector(1), FakeWeb(False), "FAKE1", root, "one")
            self.assertFalse(saved["report"])
            self.assertTrue((saved["folder"] / "logs.zip").exists())

    def test_notes_say_what_the_run_was(self):
        with tempfile.TemporaryDirectory() as root:
            saved = save_run(FakeCollector(1), None, "FAKE1", root, "one", notes="score 1500")
            self.assertIn("score 1500", (saved["folder"] / "notes.md").read_text(encoding="utf-8"))

    def test_session_stamp_is_the_newest_session(self):
        self.assertEqual(session_stamp(LOG.format(9) + LOG.format(3)), "9")
        self.assertEqual(session_stamp("no sessions"), "")


if __name__ == "__main__":
    unittest.main()
