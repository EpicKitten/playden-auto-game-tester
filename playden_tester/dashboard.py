"""dashboard.html: every game of the library on one page, with this tester's result and Playden's reports.

The page stands alone (no scripts or fonts from elsewhere) and holds only what the Markdown lists show: titles, sizes
and results. Playtime and family sharing stay out, and so does the text of a screen a tester error quoted.
"""
import html
import json
import time
from pathlib import Path

PASSED = {"survived", "not_closed"}
FAILED = {"crashed", "exited_early", "did_not_start", "refused"}
STATUS_LABELS = {
    "survived": "Survived", "not_closed": "Left running", "crashed": "Crashed", "exited_early": "Quit early",
    "did_not_start": "Did not start", "refused": "Refused by Playden", "error": "Tester error",
    "launch_failed": "Could not launch", "skipped": "Skipped", "stuck": "Stuck", "testing": "Testing now",
    "deferred": "Waiting",
}
# One group per game, in the order the page shows them. "bar" names the colour token.
GROUPS = {
    "to_test": {"label": "To test", "icon": "○", "bar": "empty"},
    "problem": {"label": "Needs a retest", "icon": "!", "bar": "warning"},
    "passed": {"label": "Survived here", "icon": "✓", "bar": "good"},
    "failed": {"label": "Failed here", "icon": "✕", "bar": "critical"},
    "left_out": {"label": "Left out by hand", "icon": "–", "bar": "muted"},
    "reported": {"label": "Reported on Playden", "icon": "●", "bar": "series"},
}


def _group(status, reported, reason):
    if status in PASSED:
        return "passed"
    if status in FAILED:
        return "failed"
    if reported:
        return "reported"
    if status:
        return "problem"
    return "left_out" if reason else "to_test"


def _detail(entry):
    """The campaign's note on a game, without the screen text a tester error can quote."""
    return (entry.get("detail") or "").split(" saw ")[0].split("\n")[0][:200]


def _links(issues):
    links = []
    for issue in issues:
        if issue.get("number"):
            links.append({"text": f"#{issue['number']}", "url": issue["url"], "state": issue.get("state") or ""})
        else:
            links.append({"text": "Compatibility list", "url": issue["url"], "state": issue.get("state") or ""})
    return links


def build_rows(library, state, reported, left_out, sizes, reports=None, anticheat=None):
    """One row per game. library: rows with app and title. state: campaign progress by app. reported: {app: issues}.
    left_out: {app: why}. sizes: {app: GB}. reports: {app: path of the local issue draft}. anticheat: {app: [names]},
    games that are tested but expected to fail."""
    reports, anticheat, games = reports or {}, anticheat or {}, {}
    for row in library:
        games.setdefault(int(row["app"]), row["title"])
    for app, entry in state.items():
        games.setdefault(int(app), entry.get("title") or str(app))
    rows = []
    for app, title in games.items():
        entry = state.get(str(app), {})
        status, issues = entry.get("status"), reported.get(app, [])
        group = _group(status, issues, left_out.get(app))
        rows.append({"app": app, "title": title, "gb": sizes.get(app), "group": group,
                     "result": STATUS_LABELS.get(status, status or ""), "detail": _detail(entry),
                     "tested": (entry.get("updated") or "")[:10], "links": _links(issues),
                     "why": left_out.get(app, ""), "draft": reports.get(app, ""),
                     "anticheat": ", ".join(anticheat.get(app, []))})
    # Never tested first: anything with an issue or a compatibility row goes last, whatever this tester found.
    return sorted(rows, key=lambda row: (bool(row["links"]), list(GROUPS).index(row["group"]), row["title"].lower()))


def read_rows(lists, anticheat_file, skip_by_hand, others, state_file, sizes_file, reports_folder):
    """The rows from the files the rest of the tester keeps. Files that are missing count as empty."""
    def load(path, default):
        path = Path(path)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    library = [row for path in lists for row in load(path, [])]
    reported = {int(row["app"]): row["issues"] for row in load(others, [])}
    left_out = {int(row["app"]): row.get("reason") or "By hand" for row in load(skip_by_hand, [])}
    anticheat = {int(row["app"]): row.get("anticheats") or [] for row in load(anticheat_file, [])}
    sizes = {int(app): gb for app, gb in load(sizes_file, {}).items() if gb}
    reports = {}
    folder = Path(reports_folder)
    if folder.is_dir():
        for path in folder.glob("*/issue.md"):
            app = path.parent.name.split("-", 1)[0]
            if app.isdigit():
                reports[int(app)] = path.as_posix()
    return build_rows(library, load(state_file, {}), reported, left_out, sizes, reports, anticheat)


def render(rows, stamp=None):
    """The page. Row data goes in as JSON, with "<" escaped so a title can't end the script."""
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    groups = json.dumps(GROUPS, ensure_ascii=False, separators=(",", ":"))
    stamp = stamp or time.strftime("%Y-%m-%d %H:%M")
    return PAGE.replace("__STAMP__", html.escape(stamp)).replace("__GROUPS__", groups).replace("__ROWS__", data)


def write(rows, out):
    Path(out).write_text(render(rows), encoding="utf-8", newline="\n")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Playden Game Tests</title>
<style>
:root {
  color-scheme: light;
  --surface: #fcfcfb; --raised: #f4f3ef; --line: #e1e0d9; --axis: #c3c2b7;
  --text: #0b0b0b; --text-2: #52514e; --text-3: #6f6e69; --link: #1f62b5;
  --good: #0ca30c; --critical: #d03b3b; --warning: #fab219; --series: #2a78d6;
  --muted: #9b9a92; --empty: #e1e0d9;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface: #1a1a19; --raised: #232321; --line: #2c2c2a; --axis: #383835;
    --text: #f0efec; --text-2: #c3c2b7; --text-3: #9b9a92; --link: #7cb2f2;
    --series: #3987e5; --muted: #6f6e69; --empty: #383835;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface: #1a1a19; --raised: #232321; --line: #2c2c2a; --axis: #383835;
  --text: #f0efec; --text-2: #c3c2b7; --text-3: #9b9a92; --link: #7cb2f2;
  --series: #3987e5; --muted: #6f6e69; --empty: #383835;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); color: var(--text);
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 32px 24px 64px; }
header { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 24px; align-items: baseline; }
h1 { font-size: 26px; line-height: 1.2; margin: 0; letter-spacing: -0.01em; }
.stamp { color: var(--text-3); font-size: 13px; }
.lead { color: var(--text-2); margin: 6px 0 24px; max-width: 70ch; }
.tiles { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin-bottom: 20px; }
.tile { background: var(--raised); border: 0; border-radius: 8px; padding: 10px 12px; text-align: left; color: inherit;
  font: inherit; cursor: pointer; min-width: 0; outline: 2px solid transparent; outline-offset: -2px; }
.tile:hover { outline-color: var(--axis); }
.tile[aria-pressed="true"] { outline-color: var(--text); }
.tile:focus-visible, button:focus-visible, input:focus-visible, a:focus-visible, th:focus-visible {
  outline: 2px solid var(--link); outline-offset: 1px; }
.tile b { display: block; font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.2; }
.tile span { display: flex; gap: 6px; align-items: center; color: var(--text-2); font-size: 13px; }
.swatch { width: 10px; height: 10px; border-radius: 3px; flex: none; }
.bar { position: relative; display: flex; gap: 2px; height: 14px; margin-bottom: 28px; }
.bar i { display: block; min-width: 2px; }
.bar i:first-child { border-radius: 4px 0 0 4px; }
.bar i:last-child { border-radius: 0 4px 4px 0; }
.tip { position: fixed; z-index: 5; pointer-events: none; background: var(--text); color: var(--surface); font-size: 13px;
  padding: 4px 8px; border-radius: 6px; white-space: nowrap; display: none; }
.tools { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 12px; }
#search { flex: 1 1 240px; max-width: 360px; font: inherit; color: inherit; background: var(--surface);
  border: 1px solid var(--axis); border-radius: 8px; padding: 7px 10px; }
#count { color: var(--text-3); font-size: 13px; font-variant-numeric: tabular-nums; }
#clear { font: inherit; font-size: 13px; color: var(--link); background: none; border: 0; padding: 0; cursor: pointer; }
.scroll { overflow-x: auto; border-top: 1px solid var(--axis); }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 12px; font-weight: 600; color: var(--text-2); padding: 8px 12px 8px 0; white-space: nowrap;
  border-bottom: 1px solid var(--axis); cursor: pointer; user-select: none; position: sticky; top: 0; background: var(--surface); }
th[aria-sort="ascending"]::after { content: " ▲"; }
th[aria-sort="descending"]::after { content: " ▼"; }
td { padding: 7px 12px 7px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; padding-right: 20px; }
td.game { min-width: 200px; }
td.tested { white-space: nowrap; color: var(--text-2); font-variant-numeric: tabular-nums; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.state { display: inline-flex; gap: 6px; align-items: baseline; white-space: nowrap; }
.state .dot { font-size: 12px; width: 12px; text-align: center; font-weight: 700; }
.note { color: var(--text-3); font-size: 13px; margin-top: 1px; max-width: 42ch; }
.links { display: flex; flex-wrap: wrap; gap: 2px 10px; }
.tag { color: var(--text-3); font-size: 12px; }
.none { color: var(--text-3); }
footer { color: var(--text-3); font-size: 13px; margin-top: 16px; max-width: 80ch; }
code { font-size: 12px; }
@media (max-width: 760px) {
  main { padding: 20px 16px 48px; }
  .tiles { grid-template-columns: repeat(2, 1fr); }
  td.tested, th.tested { display: none; }
}
@media (forced-colors: active) {
  .bar i, .swatch { forced-color-adjust: none; border: 1px solid CanvasText; }
}
</style>
</head>
<body>
<main>
<header><h1>Playden Game Tests</h1><div class="stamp">Generated __STAMP__</div></header>
<p class="lead" id="lead"></p>
<div class="tiles" id="tiles"></div>
<div class="bar" id="bar" role="img"></div>
<div class="tools">
  <input id="search" type="search" placeholder="Search games" aria-label="Search games">
  <span id="count" aria-live="polite"></span>
  <button id="clear" type="button" hidden>Clear filters</button>
</div>
<div class="scroll"><table>
<thead><tr>
  <th data-key="title" tabindex="0">Game</th>
  <th data-key="gb" class="num" tabindex="0">Size</th>
  <th data-key="group" tabindex="0" aria-sort="ascending">This tester</th>
  <th data-key="links" tabindex="0">Playden reports</th>
  <th data-key="tested" class="tested" tabindex="0">Tested</th>
</tr></thead>
<tbody id="rows"></tbody>
</table></div>
<footer>Never-tested games come first; games with a Playden issue or a compatibility row come last. "Survived" means the game ran through the watch time with a moving picture; it doesn't prove it is playable.
Reports count whoever filed them. Rebuild this page with <code>python -m playden_tester dashboard</code>.</footer>
</main>
<div class="tip" id="tip"></div>
<script>
const GROUPS = __GROUPS__;
const ROWS = __ROWS__;
const order = Object.keys(GROUPS);
const $ = id => document.getElementById(id);
let filter = null, query = "", sortKey = "group", sortDir = 1;

function esc(text) {
  const box = document.createElement("span");
  box.textContent = text == null ? "" : text;
  return box.innerHTML;
}
const size = gb => gb == null ? "–" : gb < 1 ? Math.round(gb * 1024) + " MB" : (gb < 10 ? gb.toFixed(1) : Math.round(gb)) + " GB";
const count = key => ROWS.filter(row => row.group === key).length;

function summary() {
  const tested = count("passed") + count("failed");
  $("lead").textContent = `${ROWS.length} games: ${tested} tested here, ${count("reported")} more reported on Playden, ` +
    `${count("to_test") + count("problem")} still to test.`;
  $("tiles").innerHTML = order.map(key => `<button class="tile" type="button" data-group="${key}" aria-pressed="false">` +
    `<b>${count(key)}</b><span><i class="swatch" style="background:var(--${GROUPS[key].bar})"></i>${esc(GROUPS[key].label)}</span></button>`).join("");
  $("bar").setAttribute("aria-label", order.map(key => `${GROUPS[key].label}: ${count(key)}`).join(", "));
  $("bar").innerHTML = order.filter(count).map(key => `<i data-group="${key}" style="flex:${count(key)} 0 0;background:var(--${GROUPS[key].bar})"></i>`).join("");
}

function compare(a, b) {
  const pick = {
    group: row => (row.links.length ? 100 : 0) + order.indexOf(row.group),
    title: row => row.title.toLowerCase(),
    gb: row => row.gb == null ? Infinity : row.gb,
    links: row => row.links.length ? -row.links.length : 1,
    tested: row => row.tested || "~",
  }[sortKey];
  const x = pick(a), y = pick(b);
  return (x < y ? -1 : x > y ? 1 : a.title.localeCompare(b.title)) * sortDir;
}

function stateCell(row) {
  const group = GROUPS[row.group];
  const label = row.result || (row.group === "reported" ? "Not tested here" : row.group === "left_out" ? row.why : group.label);
  const cheat = row.anticheat ? `<div class="note">Anti-cheat, expected to fail: ${esc(row.anticheat)}</div>` : "";
  const note = cheat + (row.result && row.detail ? `<div class="note">${esc(row.detail)}</div>` : "");
  const draft = row.draft ? ` <a href="${esc(row.draft)}" class="tag">draft</a>` : "";
  return `<span class="state"><span class="dot" style="color:var(--${group.bar === "empty" ? "muted" : group.bar})">${group.icon}</span>${esc(label)}${draft}</span>${note}`;
}

function linksCell(row) {
  if (!row.links.length) return '<span class="none">–</span>';
  return `<div class="links">` + row.links.map(link =>
    `<span><a href="${esc(link.url)}">${esc(link.text)}</a> <span class="tag">${esc(link.state)}</span></span>`).join("") + "</div>";
}

function draw() {
  const words = query.toLowerCase().split(/\\s+/).filter(Boolean);
  const shown = ROWS.filter(row => (!filter || row.group === filter) &&
    words.every(word => (row.title + " " + row.app).toLowerCase().includes(word))).sort(compare);
  $("rows").innerHTML = shown.map(row => `<tr><td class="game"><a href="https://store.steampowered.com/app/${row.app}">${esc(row.title)}</a></td>` +
    `<td class="num">${size(row.gb)}</td><td>${stateCell(row)}</td><td>${linksCell(row)}</td>` +
    `<td class="tested">${esc(row.tested) || '<span class="none">–</span>'}</td></tr>`).join("");
  $("count").textContent = `${shown.length} of ${ROWS.length} games`;
  $("clear").hidden = !filter && !query;
  document.querySelectorAll(".tile").forEach(tile => tile.setAttribute("aria-pressed", tile.dataset.group === filter));
}

function sortBy(th) {
  const key = th.dataset.key;
  sortDir = sortKey === key ? -sortDir : 1;
  sortKey = key;
  document.querySelectorAll("th").forEach(other => other.removeAttribute("aria-sort"));
  th.setAttribute("aria-sort", sortDir > 0 ? "ascending" : "descending");
  draw();
}

summary();
draw();
$("tiles").addEventListener("click", event => {
  const tile = event.target.closest(".tile");
  if (tile) { filter = filter === tile.dataset.group ? null : tile.dataset.group; draw(); }
});
$("search").addEventListener("input", event => { query = event.target.value; draw(); });
$("clear").addEventListener("click", () => { filter = null; query = ""; $("search").value = ""; draw(); });
document.querySelectorAll("th").forEach(th => {
  th.addEventListener("click", () => sortBy(th));
  th.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); sortBy(th); } });
});
$("bar").addEventListener("mousemove", event => {
  const part = event.target.closest("i"), tip = $("tip");
  if (!part) { tip.style.display = "none"; return; }
  const key = part.dataset.group;
  tip.textContent = `${GROUPS[key].label}: ${count(key)} (${Math.round(count(key) / ROWS.length * 100)}%)`;
  tip.style.display = "block";
  tip.style.left = Math.min(event.clientX + 12, innerWidth - tip.offsetWidth - 8) + "px";
  tip.style.top = event.clientY + 16 + "px";
});
$("bar").addEventListener("mouseleave", () => { $("tip").style.display = "none"; });
</script>
</body>
</html>
"""
