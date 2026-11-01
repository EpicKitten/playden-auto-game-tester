"""Write a run's results: results.json, summary.csv and one Markdown report per game."""
import csv
import json
from dataclasses import asdict
from pathlib import Path

SUMMARY_FIELDS = ["title", "name", "steam_app", "status", "screen", "detail", "seconds_running", "session_seconds",
                  "problems", "screenshot"]
RESULT_LABELS = {
    "survived": "✅ Runs (survived the watch time; playability not checked)",
    "crashed": "❌ Broken: crashed",
    "exited_early": "❌ Broken: quit early",
    "did_not_start": "❌ Broken: does not start",
    "launch_failed": "⚠️ Not tested: could not launch",
    "not_closed": "✅ Runs (left running)",
}


def alive_stats(log_tail):
    """The counters of the last "PW_WINE64 alive" line of a title log (vk_shown, audible, frames_put, ...)."""
    import re
    lines = [l for l in log_tail.splitlines() if " alive " in l]
    if not lines:
        return {}
    return {k: int(v) for k, v in re.findall(r"\b(\w+)=(\d+)\b", lines[-1])}


class RunWriter:
    def __init__(self, folder, meta, resume=False):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.meta = meta
        self.results = []
        saved = self.folder / "results.json"
        if resume and saved.exists():
            # A campaign that goes on keeps the results of its earlier runs.
            from .runner import Result
            known = set(Result.__dataclass_fields__)
            rows = json.loads(saved.read_text(encoding="utf-8")).get("results", [])
            self.results = [Result(**{k: v for k, v in row.items() if k in known}) for row in rows]

    def add(self, result):
        self.results.append(result)
        self._write_report(result)
        self.save()

    def rewrite(self, results):
        """Write the reports of results that changed after they were added."""
        for result in results:
            self._write_report(result)
        self.save()

    def save(self):
        data = {"meta": self.meta, "results": [asdict(r) for r in self.results]}
        (self.folder / "results.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        with open(self.folder / "summary.csv", "w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, SUMMARY_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for result in self.results:
                row = asdict(result)
                row["problems"] = " | ".join(result.problems)
                row["screen"] = result.screen.get("verdict", "")
                row["seconds_running"] = round(result.seconds_running)
                writer.writerow(row)

    @staticmethod
    def _label(r):
        verdict = r.screen.get("verdict")
        if r.status in ("survived", "not_closed") and verdict == "black":
            return "⚠️ Starts, but the screen stayed black"
        if r.status in ("survived", "not_closed") and verdict == "still":
            return "✅ Runs (picture did not move while watched: a menu, or frozen)"
        if r.status in ("survived", "not_closed") and verdict == "moving":
            return "✅ Runs (picture moving; playability not checked)"
        return RESULT_LABELS.get(r.status, r.status)

    def write_issue(self, r, versions, logs_zip):
        """A draft for Playden's test-report issue form (.github/ISSUE_TEMPLATE/test-report.yml), not posted."""
        verdict = r.screen.get("verdict")
        if r.status in ("survived", "not_closed") and verdict in ("moving", "still"):
            status = "✅ Works: reaches the menu and plays"
            note = "Reached the screen in the screenshot. Automated test: gameplay itself was not played; check before posting."
        elif r.status in ("survived", "not_closed"):
            alive = alive_stats(r.log_tail)
            if alive.get("vk_shown", 0) > 0 or alive.get("audible", 0) > 0:
                status = "❌ Broken: starts, but is not playable"
                note = (f"The screen stayed black for {r.seconds_running:.0f} s while the game ran: Vulkan presented "
                        f"{alive.get('vk_shown', 0)} frames and audio played ({alive.get('audible', 0)} audible).")
            else:
                status = "❌ Does not start: back to Home, or stays on the spinner"
                note = f"Still on a black screen or the loading spinner after {r.seconds_running:.0f} s."
        elif r.status in ("crashed", "exited_early", "did_not_start"):
            status = "❌ Does not start: back to Home, or stays on the spinner"
            note = f"Went back to Home: {r.detail}."
        else:
            return None  # a launch the tester could not make says nothing about the game
        store = f"https://store.steampowered.com/app/{r.steam_app}" if r.steam_app else "(imported)"
        tail = r.log_tail.strip().splitlines()[-15:]
        lines = [
            f"<!-- Draft from playden-auto-tester, {r.started_at}. Not posted. Title: [Test] {r.name} -->",
            f"# [Test] {r.name}", "",
            "### Game", "", f"{r.name} — {store}", "",
            "### Result", "", status, "",
            "### Versions", "", versions.strip(), "",
            "### Where the game is installed", "", "Console storage", "",
            "### Controls", "", "- [x] DualSense, default (Xbox controller) (virtual DualSense from padd)", "",
            "### Game settings you changed", "", "None.", "",
            "### What happened", "",
            "1. Started from its PS5 title (Playden's relaunch helper), nothing pressed.",
            f"2. {note}",
            f"3. Screen before closing: {verdict or 'not checked'}"
            + (f" (brightness {r.screen['brightness']}/255, motion {r.screen['motion']})" if r.screen else "") + ".",
            f"4. Session in the log: {r.session or 'none'} ({r.session_seconds} s).", "",
            "### Logs and screenshots", "",
            f"`{logs_zip}` (attach it){', and `' + r.screenshot + '`' if r.screenshot else ''}.", "",
        ]
        if r.problems:
            lines += ["Fatal lines found:", ""] + [f"- `{p}`" for p in r.problems] + [""]
        if tail:
            lines += [f"From `logs/title-{r.title}.log`, near the end:", "", "```", *tail, "```", ""]
        lines += ["### Checks", "", "- [x] kstuff and ShadowMountPlus were loaded when I tested.",
                  "- [x] I own this game (on Steam, or a copy I bought for an imported game).", ""]
        folder = self.folder / "issues"
        folder.mkdir(exist_ok=True)
        path = folder / f"{r.title}-{r.steam_app or 'local'}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _write_report(self, r):
        store = f"https://store.steampowered.com/app/{r.steam_app}" if r.steam_app else "(not a Steam game)"
        errors = ", ".join(f"{k} ×{v}" for k, v in sorted(r.wine_errors.items(), key=lambda kv: -kv[1])) or "none"
        lines = [
            f"**Title:** [Test] {r.name}", "",
            "### Game", "", f"{r.name} — {store}", "",
            "### Result", "", self._label(r), "",
            "### Versions", "",
            "| Field | Value |", "| --- | --- |",
            f"| tested | {r.started_at} |",
            f"| Playden | {self.meta.get('playden_version', '?')} |",
            f"| firmware | {self.meta.get('firmware', '?')} |",
            f"| game title | {r.title} |", "",
            "### What happened", "",
            f"Started by playden-auto-tester. Status `{r.status}`. {r.detail}".rstrip(),
            f"Seen running for {r.seconds_running:.0f} s; the session in the log lasted {r.session_seconds} s.", "",
            "### Log findings", "",
        ]
        lines += [f"- {p}" for p in r.problems] or ["- No fatal lines found."]
        lines += ["", f"Wine `err:` channels: {errors}", ""]
        if r.screen:
            lines += ["### Screen", "",
                      f"Before closing: **{r.screen['verdict']}** (brightness {r.screen['brightness']}/255, "
                      f"motion {r.screen['motion']} per pixel over {r.screen['frames']} frames).", ""]
        if r.screenshot:
            lines += [f"![{r.name}]({r.screenshot})", ""]
        if r.log_tail:
            lines += [f"From `logs/title-{r.title}.log` ({r.session}), near the end:", "", "```", r.log_tail, "```", ""]
        (self.folder / f"{r.title}.md").write_text("\n".join(lines), encoding="utf-8")
