# AGENTS.md

Notes for coding agents (and people) working on playden-auto-tester. The README covers what the tool does and how to
run it; this file covers how to change it safely.

## What it is

A Python CLI (`playden-tester`, package `playden_tester/`) that tests [Playden](https://github.com/leolobato/playden-ps5)
games on a jailbroken PS5 from a Windows PC: it downloads each game through Playden's UI, launches it, watches it
with an HDMI capture card, collects logs, writes a report folder and an issue draft, and uninstalls it.

- Python 3.10+, standard library only (`dependencies = []`). Pillow is used for screen reading when present; don't
  add other packages without a good reason.
- Windows is the main platform: OCR is Windows' built-in engine (`playden_tester/ocr.ps1`), video comes from ffmpeg
  (DirectShow). The console side is reached over HTTP (ps5-web-file-manager, port 8888), elfldr (9021), padd (9305)
  and Playden's web access (7031).

## Layout

| Module | Role |
| --- | --- |
| `cli.py` | Commands and their options; the entry point |
| `campaign.py` | Download, prepare, test, report folder, uninstall, one game after another; progress in `results/campaign/campaign.json` |
| `runner.py` | One test: launch, watch, screenshots, screen check, close |
| `playden_ui.py` | Driving Playden's screens with padd and OCR (tabs, Library search, install, uninstall, game settings) |
| `screen.py`, `capture.py` | Capture card frames, OCR lines, the orange focus outline |
| `console.py`, `filemanager.py`, `padd.py`, `webaccess.py` | The console's services |
| `rig.py`, `mcp.py`, `payloadmgr.py`, `remoteplay.py` | Everything above as one object, with the safety rules built in; the MCP server the plugin starts; Payload Manager (8084); Remote Play through chiaki-ng |
| `.claude-plugin/`, `skills/`, `payloads/` | The Claude Code plugin, its skill, and the `ps5power` payload |
| `report.py` | Results, Markdown reports and issue drafts for Playden's test-report form |
| `library.py`, `reported.py`, `ports.py`, `storefeatures.py`, `protondb.py`, `players.py`, `lists.py` | Building the lists of games still to test (`update` runs them) |
| `tests/test_tester.py` | Unit tests with fake consoles, clocks and captures |

## Commands

```sh
python -m unittest discover -s tests      # run before every commit; all must pass
python -m playden_tester update           # rebuild the lists of games to test (no console needed)
python -m playden_tester doctor           # check the console (PS5_HOST)
python -m playden_tester campaign         # the long run; needs padd, the capture card (PS5_CAPTURE) and elfldr
```

A campaign takes days. Run it in the background, append its output to `results/campaign-run.log`, and stop it only
between games when you can: a stop in the middle of a download leaves it paused in Playden's Queue.

## Rules that protect the user

- **Never read `/data/playden/user/session.v1`.** It holds the Steam sign-in. Only `library-<SteamID>.cache` in that
  folder may be read.
- **Logs and zips are redacted** (Steam account names and SteamIDs) before they are saved. Playden's own report zip is
  already redacted by Playden.
- **Nothing is posted to Playden's tracker.** Issue drafts are written locally for the user to review.
- **Uninstalls keep saves.** Check that "Delete saves too" stays Off; never press it.
- **Don't uninstall the user's own games.** The campaign only evicts games it tested itself.
- **New tools go through `rig.py`,** so they get its checks: `session.v1` is refused on every route, deletes stay
  inside `PS5_DELETE_ROOTS` and are dry runs by default, and input waits for a campaign to end.
- **chiaki-ng's pairing key stays in chiaki-ng.** Don't read it from the registry: start chiaki-ng instead.
- **Exact names before destructive actions.** The uninstall dialog check must stay exact apart from known OCR slips
  (®/™/©): "Escape Simulator" must never match "Escape Simulator 2".
- Ask before pushing, opening or editing a PR.

## Playden 0.10 behaviour the code depends on

Learned on the test console (Playden 0.10.0-beta.1, firmware 12.20); check again after a Playden update.

- The PS5 title is reserved when Playden **starts** preparing a game; it is ready only at
  `prepare result app=<app> ready` in `runtime.log`. A game launched earlier quits in about 2 s or is refused
  (0x80940031), and its preparation is left unfinished. `Campaign.wait_prepared` handles this.
- After a game closes, Playden stays suspended and keeps its sandbox folder, so `is_running(PLAYDEN)` is not
  reliable and launching it again does nothing. It is brought back from its tile on the PS5's Home
  (`PlaydenUI.open_from_ps_home`, told apart by its orange-on-black icon).
- Install opens a sheet ("To Console storage"); downloads queue ("Download Queued") and can pause ("Download
  Paused": resume it from the Queue row's Actions, not the page button, which only opens the Queue).
- The Library search keeps its last text: clear it with Square (backspace). Triangle types a space on the system
  keyboard even though Playden's hint says "Clear".
- Per-game settings (performance overlay, detail "Everything") are set through Actions > Game settings; their files
  under `/data/playden/games/` are not readable over the file manager.
- OCR slips seen often: Q read as O ("Oueue"), ® as O ("LEGOO"), neighbouring tabs merged ("Saves 20 Settings"),
  highlighted items missed ("All"). Prefer positions, colours and nearby text that reads reliably.

When a screen changes, take a screenshot through the capture card (`playden-tester snapshot FILE`) and look before
changing the navigation code. Don't guess at buttons.

## Data

- `data/` is gitignored except `data/games-to-test.md`, `data/games-by-players.md` and `data/games-by-size.md`, the
  maintainer's lists. Other
  users regenerate them with `library --controller full`, `library --controller partial` and `update`.
- `data/reports/<app>-<name>/` holds each tested game's screenshots (`screenshot-30s.jpg`, `screenshot-90s.jpg`),
  `playden-report.zip`, `issue.md` and `result.json`. Not committed.
- `games-to-test.json` is not committed: it holds playtime and family-sharing details.
- Markdown lists are written with LF line endings (`newline="\n"`), so a run on Windows doesn't rewrite every line.

## Style

- Match the code around you: short docstrings that say what and why, comments only where the reason is not obvious,
  lines up to about 120 characters.
- Error messages and log lines are plain sentences that name the game: `"[app] Title: what happened"`.
- New behaviour gets a unit test with the existing fakes (`FakeConsole`, `FakeCapture`, `FakeClock`).
- Issue drafts end their Versions section with "This report is AI generated using <model>" (`report.AI_MODEL`).

## Git and PRs

- Commit messages: a short summary line, then what changed and why. End agent-written commits with a
  `Co-Authored-By:` line for the model.
- `gh` may not be installed; PRs can be opened through the GitHub API with a token from `git credential fill`. Never
  print the token.
