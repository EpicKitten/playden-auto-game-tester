import json
import tempfile
import unittest
from pathlib import Path

from playden_tester.dashboard import build_rows, read_rows, render

ISSUE = {"number": 7, "title": "[Test] B", "state": "open", "url": "https://github.com/leolobato/playden-ps5/issues/7"}
LIST = {"number": None, "title": "COMPATIBILITY.md: B", "state": "✅ Works",
        "url": "https://github.com/leolobato/playden-ps5/blob/main/COMPATIBILITY.md"}


def row_for(rows, app):
    return next(row for row in rows if row["app"] == app)


class GroupTest(unittest.TestCase):
    def rows(self, state=None, reported=None, left_out=None):
        library = [{"app": n, "title": f"Game {n}", "playtime_minutes": 99, "family_shared": True} for n in (1, 2, 3)]
        return build_rows(library, state or {}, reported or {}, left_out or {}, {1: 2.5})

    def test_a_game_nobody_tested_is_to_test(self):
        self.assertEqual(row_for(self.rows(), 1)["group"], "to_test")

    def test_each_campaign_result_finds_its_group(self):
        for status, group in (("survived", "passed"), ("crashed", "failed"), ("refused", "failed"),
                              ("error", "problem"), ("launch_failed", "problem")):
            rows = self.rows({"1": {"status": status, "title": "Game 1"}})
            self.assertEqual(row_for(rows, 1)["group"], group, status)

    def test_a_tester_error_does_not_hide_a_report(self):
        rows = self.rows({"1": {"status": "error"}}, {1: [ISSUE]})
        self.assertEqual(row_for(rows, 1)["group"], "reported")

    def test_our_own_result_comes_first_and_keeps_the_issue(self):
        row = row_for(self.rows({"1": {"status": "survived"}}, {1: [ISSUE]}), 1)
        self.assertEqual(row["group"], "passed")
        self.assertEqual(row["links"][0]["url"], ISSUE["url"])

    def test_a_game_left_out_says_why(self):
        row = row_for(self.rows(left_out={2: "Removed by hand"}), 2)
        self.assertEqual((row["group"], row["why"]), ("left_out", "Removed by hand"))

    def test_an_anticheat_game_is_still_to_test_and_says_why_it_may_fail(self):
        rows = build_rows([{"app": 1, "title": "A"}], {}, {}, {}, {}, anticheat={1: ["BattlEye", "VAC"]})
        self.assertEqual((rows[0]["group"], rows[0]["anticheat"]), ("to_test", "BattlEye, VAC"))

    def test_a_game_only_the_campaign_knows_is_kept(self):
        self.assertEqual(row_for(self.rows({"9": {"status": "survived", "title": "Extra"}}), 9)["title"], "Extra")


class OrderTest(unittest.TestCase):
    def test_never_tested_games_come_first_and_reported_ones_last(self):
        library = [{"app": n, "title": name} for n, name in ((1, "A issue"), (2, "B tested"), (3, "C new"), (4, "D both"))]
        state = {"2": {"status": "survived"}, "4": {"status": "survived"}}
        rows = build_rows(library, state, {1: [ISSUE], 4: [LIST]}, {}, {})
        self.assertEqual([row["app"] for row in rows], [3, 2, 4, 1])


class LinkTest(unittest.TestCase):
    def test_issues_and_the_compatibility_list_are_both_linked(self):
        rows = build_rows([{"app": 1, "title": "B"}], {}, {1: [ISSUE, LIST]}, {}, {})
        self.assertEqual([link["text"] for link in rows[0]["links"]], ["#7", "Compatibility list"])
        self.assertEqual(rows[0]["links"][1]["state"], "✅ Works")


class PrivacyTest(unittest.TestCase):
    def test_playtime_family_sharing_and_screen_text_stay_out(self):
        library = [{"app": 1, "title": "Game", "playtime_minutes": 4242, "family_shared": True, "developer": "x"}]
        state = {"1": {"status": "error", "detail": "expected ('Library') on screen; saw ['realname', 'Debug:']"}}
        page = render(build_rows(library, state, {}, {}, {}))
        for private in ("4242", "family", "playtime", "realname"):
            self.assertNotIn(private, page)


class RenderTest(unittest.TestCase):
    def test_a_title_cannot_end_the_script(self):
        page = render(build_rows([{"app": 1, "title": "</script><b>x"}], {}, {}, {}, {}))
        self.assertNotIn("</script><b>", page)

    def test_it_stands_alone(self):
        page = render([])
        self.assertNotIn('src="http', page)
        self.assertNotIn('rel="stylesheet"', page)


class ReadTest(unittest.TestCase):
    def test_missing_files_count_as_empty_and_drafts_are_found(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "games.json").write_text(json.dumps([{"app": 5, "title": "Five"}]), encoding="utf-8")
            (root / "reports" / "5-five").mkdir(parents=True)
            (root / "reports" / "5-five" / "issue.md").write_text("draft", encoding="utf-8")
            rows = read_rows([root / "games.json"], root / "a", root / "b", root / "c", root / "d", root / "e",
                             root / "reports")
        self.assertEqual(rows[0]["group"], "to_test")
        self.assertTrue(rows[0]["draft"].endswith("5-five/issue.md"))


if __name__ == "__main__":
    unittest.main()
