import json
import tempfile
import unittest
from pathlib import Path

from playden_tester.dashboard import build_rows, compatibility_counts, read_draft, read_imported, read_rows, render

ISSUE = {"number": 7, "title": "[Test] B", "state": "open", "url": "https://github.com/leolobato/playden-ps5/issues/7"}
LIST = {"number": None, "title": "COMPATIBILITY.md: B", "state": "✅ Works",
        "url": "https://github.com/leolobato/playden-ps5/blob/main/COMPATIBILITY.md"}


DRAFT = """<!-- Draft from playden-auto-tester, 2026-11-04 12:37:28. Not posted. Title: [Test] Five -->
# [Test] Five

### Game

Five — https://store.steampowered.com/app/5

### Result

✅ Works: reaches the menu and plays

### Versions

| Field | Value |
| --- | --- |
| firmware | 12.20 |

This report is AI generated using Opus 5.5 Medium.

### Where the game is installed

Console storage

### Controls

- [x] DualSense, default (Xbox controller) (virtual DualSense from padd)

### Game settings you changed

None.

### What happened

1. Started from its PS5 title (Playden's relaunch helper), nothing pressed.
2. Reached the screen in the screenshot. Automated test: gameplay itself was not played; check before posting.

### Logs and screenshots

`logs.zip` (attach it), and `shot.jpg`, and `gone.jpg`.

From `logs/title-FAKE1.log`, near the end:

```
REC seq=1
```

### Checks

- [x] kstuff and ShadowMountPlus were loaded when I tested.
"""


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
    def compat(self, game, app=None, **fields):
        return {"game": game, "app": app, "url": "", "status": "✅ Works", "kit": "0.18", "engine": "", "notes": "Fine",
                **fields}

    def test_a_compatibility_row_shows_on_the_game_it_links(self):
        rows = build_rows([{"app": 5, "title": "Five"}], {}, {}, {}, {}, compatibility=[self.compat("Five!", 5)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["group"], "reported")
        self.assertEqual((rows[0]["compat"][0]["status"], rows[0]["compat"][0]["kit"]), ("✅ Works", "0.18"))
        self.assertEqual(rows[0]["compat"][0]["by"], "app")

    def test_a_row_without_a_known_app_matches_by_exact_name(self):
        rows = build_rows([{"app": 5, "title": "Escape Simulator"}], {}, {}, {}, {},
                          compatibility=[self.compat("Escape Simulator (imported)"),
                                         self.compat("Escape Simulator", 99)])
        self.assertEqual(len(rows), 1)
        self.assertEqual([entry["by"] for entry in rows[0]["compat"]], ["name", "name"])

    def test_a_longer_name_is_a_different_game(self):
        rows = build_rows([{"app": 5, "title": "Escape Simulator"}], {}, {}, {}, {},
                          compatibility=[self.compat("Escape Simulator 2", 99)])
        self.assertEqual({row["title"]: bool(row["compat"]) for row in rows},
                         {"Escape Simulator": False, "Escape Simulator 2": True})

    def test_games_only_on_the_compatibility_list_get_a_row(self):
        rows = build_rows([], {}, {9: [ISSUE]}, {}, {},
                          compatibility=[self.compat("Nine", 9), self.compat("Blur"), self.compat("Blur (imported)")])
        by_title = {row["title"]: row for row in rows}
        self.assertEqual(set(by_title), {"Nine", "Blur"})
        self.assertEqual((by_title["Nine"]["app"], by_title["Nine"]["key"]), (9, "9"))
        self.assertEqual([link["text"] for link in by_title["Nine"]["links"]], ["#7"])
        self.assertEqual((by_title["Blur"]["app"], by_title["Blur"]["key"]), (None, "name:blur"))
        self.assertEqual(len(by_title["Blur"]["compat"]), 2)
        self.assertEqual(by_title["Blur"]["group"], "reported")
        self.assertNotIn("__ROWS__", render(rows))

    def test_the_compatibility_column_replaces_the_link_to_the_list(self):
        rows = build_rows([{"app": 5, "title": "Five"}], {}, {5: [ISSUE, LIST]}, {}, {},
                          compatibility=[self.compat("Five", 5)])
        self.assertEqual([link["text"] for link in rows[0]["links"]], ["#7"])

    def test_games_on_the_compatibility_list_sort_with_the_reported_ones(self):
        rows = build_rows([{"app": 1, "title": "Listed"}, {"app": 2, "title": "Untested"}], {}, {}, {}, {},
                          compatibility=[self.compat("Listed", 1)])
        self.assertEqual([row["title"] for row in rows], ["Untested", "Listed"])

    def test_counts_say_how_rows_matched(self):
        rows = build_rows([{"app": 1, "title": "One"}, {"app": 2, "title": "Two"}], {}, {}, {}, {},
                          compatibility=[self.compat("One", 1), self.compat("Two"), self.compat("Three", 3),
                                         self.compat("Four"), self.compat("Five")])
        self.assertEqual(compatibility_counts(rows), {"app": 1, "name": 1, "steam": 1, "other": 2})

    def test_read_rows_takes_the_compatibility_list_from_its_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "compatibility.json"
            path.write_text(json.dumps([self.compat("Blur")]), encoding="utf-8")
            rows = read_rows([], "none", "none", "none", "none", "none", folder, compatibility_file=path)
            self.assertEqual([row["title"] for row in rows], ["Blur"])
            self.assertEqual(read_rows([], "none", "none", "none", "none", "none", folder,
                                       compatibility_file=Path(folder) / "gone.json"), [])

    def test_a_game_known_only_from_its_reports_gets_a_row(self):
        rows = build_rows([{"app": 1, "title": "One"}], {}, {1422450: [ISSUE]}, {}, {}, titles={1422450: "Deadlock"})
        row = next(row for row in rows if row["app"] == 1422450)
        self.assertEqual((row["title"], row["group"]), ("Deadlock", "reported"))
        self.assertEqual([link["text"] for link in row["links"]], ["#7"])

    def test_a_library_title_wins_and_a_game_without_reports_gets_no_row(self):
        rows = build_rows([{"app": 1, "title": "One"}], {}, {1: [ISSUE]}, {}, {}, titles={1: "[One", 2: "Two"})
        self.assertEqual([row["title"] for row in rows], ["One"])

    def test_a_compatibility_row_without_an_app_joins_the_reported_game_of_that_name(self):
        rows = build_rows([], {}, {9: [ISSUE]}, {}, {}, compatibility=[self.compat("Nine (imported)")],
                          titles={9: "Nine"})
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["app"], len(rows[0]["compat"]), len(rows[0]["links"])), (9, 1, 1))

    def test_read_rows_keeps_reported_games_outside_the_library(self):
        with tempfile.TemporaryDirectory() as folder:
            others = Path(folder) / "others.json"
            others.write_text(json.dumps([{"app": 9, "title": "Nine", "issues": [ISSUE]}]), encoding="utf-8")
            rows = read_rows([], "none", "none", others, "none", "none", folder)
        self.assertEqual([(row["app"], row["title"]) for row in rows], [(9, "Nine")])

    def test_notes_cannot_end_the_page_s_script(self):
        rows = build_rows([], {}, {}, {}, {}, compatibility=[self.compat("Blur", notes="</script><b>")])
        self.assertNotIn("</script><b>", render(rows))

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


    def test_screenshots_are_shown_from_their_files_not_copied_in(self):
        page = render([{"app": 5, "title": "Five", "group": "passed", "links": [],
                        "form": {"attach": ["data/reports/5-five/screenshot-30s.jpg"]}}])
        self.assertIn("shotField(form)", page)
        self.assertIn("data/reports/5-five/screenshot-30s.jpg", page)
        self.assertNotIn("data:image", page)


class DraftTest(unittest.TestCase):
    def form(self, name="5-five/issue.md", files=("5-five/logs.zip", "5-five/shot.jpg")):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / name
            path.parent.mkdir(parents=True)
            path.write_text(DRAFT, encoding="utf-8")
            for file in files:
                (root / file).parent.mkdir(parents=True, exist_ok=True)
                (root / file).write_bytes(b"x")
            form = read_draft(path)
            form["attach"] = [Path(file).relative_to(root).as_posix() for file in form["attach"]]
            return form

    def test_each_form_field_is_found(self):
        form = self.form()
        self.assertEqual(form["title"], "[Test] Five")
        self.assertEqual(form["game"], "Five — https://store.steampowered.com/app/5")
        self.assertEqual(form["status"], "✅ Works: reaches the menu and plays")
        self.assertEqual(form["storage"], "Console storage")
        self.assertEqual(form["settings"], "None.")
        self.assertIn("| firmware | 12.20 |", form["versions"])
        self.assertTrue(form["versions"].endswith("Opus 5.5 Medium."))

    def test_the_note_to_the_reviewer_is_not_for_the_form(self):
        self.assertNotIn("check before posting", self.form()["happened"])

    def test_files_are_kept_apart_from_the_log_text(self):
        form = self.form()
        self.assertEqual(form["attach"], ["5-five/logs.zip", "5-five/shot.jpg"])  # gone.jpg does not exist
        self.assertTrue(form["logs"].startswith("From `logs/title-FAKE1.log`"))
        self.assertNotIn("attach it", form["logs"])

    def test_a_draft_in_issues_finds_the_zip_in_logs(self):
        form = self.form("issues/FAKE1-5.md", ("logs/logs.zip", "shot.jpg"))
        self.assertEqual(form["attach"], ["logs/logs.zip", "shot.jpg"])

    def test_the_form_reaches_the_page_without_ending_the_script(self):
        rows = build_rows([{"app": 1, "title": "A"}], {}, {}, {}, {}, forms={1: {"happened": "</script><b>x"}})
        self.assertNotIn("</script><b>", render(rows))


class ReadTest(unittest.TestCase):
    def test_a_games_report_folder_wins_over_its_draft_in_issues(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "games.json").write_text(json.dumps([{"app": 5, "title": "Five"}, {"app": 6, "title": "Six"}]),
                                             encoding="utf-8")
            (root / "reports" / "5-five").mkdir(parents=True)
            (root / "issues").mkdir()
            (root / "reports" / "5-five" / "issue.md").write_text("# [Test] From reports", encoding="utf-8")
            (root / "issues" / "FAKE1-5.md").write_text("# [Test] From issues", encoding="utf-8")
            (root / "issues" / "refused-6.md").write_text("# [Test] Refused", encoding="utf-8")
            rows = read_rows([root / "games.json"], root / "a", root / "b", root / "c", root / "d", root / "e",
                             root / "reports", root / "issues")
        self.assertEqual(row_for(rows, 5)["form"]["title"], "[Test] From reports")
        self.assertEqual(row_for(rows, 6)["form"]["title"], "[Test] Refused")

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


class ImportedTest(unittest.TestCase):
    def folder(self, root, name="imported-furmark", status="survived"):
        folder = Path(root) / name
        folder.mkdir()
        (folder / "result.json").write_text(json.dumps(
            {"app": None, "game": "FurMark", "status": status, "detail": "3598 points", "tested": "2026-11-05 13:00:00",
             "gb": 0.06}), encoding="utf-8")
        (folder / "shot.jpg").write_bytes(b"x")
        (folder / "issue.md").write_text(
            "# [Test] FurMark\n\n### Game\n\nFurMark - https://example.com/furmark/\n\n### Result\n\nWorks\n\n"
            "### Controls\n\n- [x] DualSense, Mouse preset\n\n### Logs and screenshots\n\n`shot.jpg`\n\nScore: 3598\n",
            encoding="utf-8")

    def test_an_imported_folder_is_a_row_with_no_app(self):
        with tempfile.TemporaryDirectory() as root:
            self.folder(root)
            row = read_imported(root)[0]
        self.assertEqual((row["key"], row["app"], row["title"]), ("imported-furmark", None, "FurMark"))
        self.assertEqual((row["group"], row["result"], row["tested"]), ("passed", "Survived", "2026-11-05"))
        self.assertEqual(row["form"]["controls"], ["DualSense, Mouse preset"])
        self.assertTrue(row["form"]["attach"][0].endswith("imported-furmark/shot.jpg"))

    def test_a_failed_import_is_in_the_failed_group(self):
        with tempfile.TemporaryDirectory() as root:
            self.folder(root, status="crashed")
            self.assertEqual(read_imported(root)[0]["group"], "failed")

    def test_only_imported_folders_count(self):
        with tempfile.TemporaryDirectory() as root:
            self.folder(root, "123-a-steam-game")
            self.assertEqual(read_imported(root), [])

    def test_read_rows_adds_them_and_the_page_renders(self):
        with tempfile.TemporaryDirectory() as root:
            self.folder(root)
            rows = read_rows([], "none", "none", "none", "none", "none", root)
            self.assertEqual([row["title"] for row in rows], ["FurMark"])
            self.assertIn("imported-furmark", render(rows))


if __name__ == "__main__":
    unittest.main()
