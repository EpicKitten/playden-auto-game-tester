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


class RunWriter:
    def __init__(self, folder, meta):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.meta = meta
        self.results = []

    def add(self, result):
        self.results.append(result)
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
