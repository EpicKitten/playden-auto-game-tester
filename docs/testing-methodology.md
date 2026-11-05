# Testing methodology

How playden-auto-tester decides which Steam games to test, what it does with each one, and how a result is
reached. The aim is a quick, repeatable first check of whether a game starts and draws a picture under
[Playden](https://github.com/leolobato/playden-ps5) on a PS5. It does not replace someone playing the game.

## Test setup

| Part | Used for the reports in this repository |
| --- | --- |
| Console | Jailbroken PS5, firmware 12.20 |
| Playden | 0.10.0-beta.1, runtime kit 0.18 (each report's Versions section has the exact build) |
| Storage | Console storage |
| Input | padd's virtual DualSense; Playden's default controller mode (Xbox controller) |
| Video | HDMI capture card at 1080p60, read with ffmpeg on the PC; HDCP off on the PS5 |
| Payloads | kstuff and ShadowMountPlus (for Playden), ps5-web-file-manager, elfldr, padd |

Each game's own Playden settings are left at Playden's defaults, apart from the performance overlay (below).

## Which games are tested

1. **The library.** `library` reads the Steam library that Playden has cached on the console, then asks the Steam
   store about each game. A game is kept when it is a Windows game (not a demo, DLC or tool) with **full or partial
   controller support**. Steam only reports partial support as a store category, so that category is what counts.
2. **Already tested by others.** Games with a test report on
   [Playden's issue tracker](https://github.com/leolobato/playden-ps5/issues) (an issue linking the game's Steam page,
   or titled with its name) or a row in Playden's `COMPATIBILITY.md` are left out, so testing time goes to games
   nobody has reported on yet.
3. **Multiplayer games with anti-cheat** (Easy Anti-Cheat, BattlEye, VAC and similar) are left out: their online play
   cannot work under Playden.

## Test order

Quickest first, so the most games get tested in the least time:

1. Games already installed (no download to wait for).
2. The smallest install first: the disk space the game's Steam store page asks for (its minimum requirements).
   Games whose page doesn't state it come after the rest. Games of the same size follow the rest of this order.
3. Full controller support before partial (partial support often means menus that need a mouse).
4. [ProtonDB](https://www.protondb.com) rating: Platinum, Gold, Silver, Bronze, Borked, then games with too few or no
   reports. A game that runs well through Proton on Linux is more likely to run under Playden's Wine.
5. Games with no console version first, then games on Xbox or Nintendo only, then older PlayStations, and games with
   a PS4 or PS5 version last (those already play on the PS5 without Playden). Console versions come from Wikidata.
6. DualSense support, then DualShock, then neither, from the Steam store's categories.

## What happens to each game

1. **Download through Playden.** The game is found with Playden's Library search and its page is checked against the
   game (store description or title) before anything is pressed. Install is confirmed only on the "Install game"
   sheet for console storage. Queued downloads are waited for; interrupted ones are resumed from the Queue.
2. **Wait for the preparation to finish.** Playden creates the PS5 title when it starts preparing a game, and finishes
   a minute or two later. The game is started only after Playden's `runtime.log` says
   `prepare result app=<app> ready`. Started earlier, games quit at once or were refused, which says nothing about
   the game.
3. **Turn on the performance overlay.** In the game's settings: Performance overlay On, Overlay detail "Everything".
   This is DXVK's HUD: frame rate, a frame-time graph, memory and GPU load. It only appears in games drawn through
   DXVK (Direct3D 8 to 11); Direct3D 12 and OpenGL games show no overlay.
4. **Start the game** from its PS5 title, with Playden in front, through Playden's own relaunch helper. Nothing is
   pressed in the game.
5. **Watch it for 90 seconds.** The game counts as running while its sandbox exists on the console.
   - **30 seconds** after it starts running: the first screenshot (`screenshot-30s.jpg`).
   - **At 90 seconds**: 4 seconds of video are measured (brightness and motion, below) and the second screenshot is
     taken (`screenshot-90s.jpg`).
   - A game that quits before then gets one screenshot of whatever is on screen afterwards (`screenshot.jpg`).
6. **Close the game** with padd, start Playden again so it writes the game's session to its log, and save Playden's
   report zip from its web access.
7. **Uninstall the game** through Playden, keeping its saves, to make room for the next one.

## How a result is reached

| Status | Meaning |
| --- | --- |
| `survived` | Still running after 90 seconds |
| `exited_early` | Quit before 90 seconds, with nothing fatal in its log |
| `crashed` | Quit before 90 seconds, with a fatal line in its log |
| `did_not_start` | Started, but no sandbox appeared within 45 seconds |
| `launch_failed` | The console refused to start it (refused with 0x80940031, it is tried once more first) |
| `refused` | Playden would not prepare it |
| `skipped` | Not testable: Playden's download failed, or the game is not in Playden's Library |

Fatal lines are Playden's `Crash!!!`, unhandled exceptions, failed assertions, DLLs Wine could not load, and failed
load stages.

For a game that survived, the screen at 90 seconds decides how it reads:

| Screen | Measured over 4 seconds of video | Reading |
| --- | --- | --- |
| black | mean brightness under 10 of 255 | Not working, even though it runs (the log's Vulkan frame and audio counters are noted) |
| still | mean change per pixel under 0.6 | A menu, a title screen, or frozen: check the screenshots |
| moving | anything else | Running and drawing |

Each report's issue draft picks the result on Playden's test-report form from this:

- **✅ Works:** survived, with a still or moving screen. The draft says gameplay itself was not tested.
- **❌ Broken:** survived on a black screen while the log shows it drawing or playing sound.
- **❌ Does not start:** quit early, crashed, or survived on a black screen with no sign of drawing.
- **⛔ Refused:** Playden refused to prepare it.

A launch the tester could not make (`launch_failed`) gets no draft, since it says nothing about the game.

## What each report holds

Each tested game has a folder `data/reports/<Steam app>-<name>/`:

- `screenshot-30s.jpg`, `screenshot-90s.jpg`: the game 30 seconds in and at the end, with the overlay where supported.
- `playden-report.zip`: Playden's own report from its web access, with its logs and the game's title log. Playden
  redacts the Steam account name and SteamIDs.
- `issue.md`: a draft for Playden's test-report issue form (Game, Result, Versions, storage, Controls, settings, What
  happened with the session and the end of the log, files to attach, Checks). It states that the report is AI
  generated and names the model. Nothing is posted: a person reviews it first.
- `result.json`: status, detail, screen reading and when it was tested.

## What this does not check

- **Gameplay.** Nothing is pressed in the game. "Works" means it reached a screen and kept running for 90 seconds,
  usually a menu or title screen. Controls, saving, later levels and long sessions are not tested.
- **Sound.** Audio is only seen through the counters in Playden's log, not listened to.
- **Online play.**
- **Performance over time.** The overlay shows frame rate and frame times at two moments, not across a session.
- **Other storage.** Games are installed to console storage only, not to an M.2 SSD or USB drive.
- **Only the first start.** A game that needs a launcher, a first-run setup or a key press to get past a splash
  screen may read as "still" here and work fine for a person, or the other way round.

## Retests

A game is tested again when the tester itself went wrong (a Playden screen it could not read, a launch it could not
make while Playden was busy). Those runs are marked `error` with the reason and do not count as results. A campaign
stops on its own after three such errors in a row, or two failed launches, so a console in a bad state does not
produce a run of false results.
