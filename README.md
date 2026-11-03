# playden-auto-tester
An app to automatically test playden game compatibility on the PS5 remotely via PC

It starts each [Playden](https://github.com/leolobato/playden-ps5) game on a jailbroken PS5, watches whether it keeps
running, reads the game's log, and writes a result and a test report for each game.

## Quick start

The short version for testing your own Steam games. The sections after this one explain each part in detail.

**You need**

- A jailbroken PS5 with Playden 0.10 or later, signed in to your Steam account, and with
  [ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) and
  [elfldr](https://github.com/ps5-payload-dev/elfldr) loaded (plus kstuff and ShadowMountPlus, as Playden needs).
- A Windows PC on the same network, with [Python 3.10 or later](https://www.python.org/downloads/) and ffmpeg
  (`winget install Gyan.FFmpeg`).
- An HDMI capture card between the PS5 and your TV, plugged into the PC. On the PS5, turn off Settings › System ›
  HDMI › Enable HDCP.

**1. Install the tester** (in a terminal, in this folder)

```sh
pip install -e .
```

**2. Tell it where your PS5 and capture card are**

```sh
playden-tester snapshot --list            # shows your capture card's name
set PS5_HOST=192.168.1.50                 # your PS5's address (PowerShell: $env:PS5_HOST = "192.168.1.50")
set PS5_CAPTURE=USB Capture HDMI          # the name from the list (PowerShell: $env:PS5_CAPTURE = "...")
playden-tester doctor                     # should end with "Ready to test."
```

**3. Build your list of games** (the lists in `data/` in this repository are the maintainer's, not yours)

```sh
playden-tester library --controller full      # your Steam games with full controller support
playden-tester library --controller partial   # and partial support
playden-tester update                         # skips games others already tested; sorts the rest
```

Your list is now in `data/games-to-test.md`.

**4. Connect the virtual controller** (once after each PS5 restart; padd has to be built first, see
[Direct control: padd](#direct-control-padd))

```sh
playden-tester padd start     # the PS5 then asks "Who's using this controller?"
playden-tester padd assign    # answers it
```

**5. Start testing**

```sh
playden-tester campaign
```

Leave it running; nobody needs to be at the console. For each game it downloads it through Playden, starts it,
watches it for 90 seconds, takes screenshots, saves the logs and uninstalls it again (your saves are kept). Press
Ctrl+C to stop, and run the same command again to carry on where it stopped.

**6. Read the results**

Each tested game gets a folder in `data/reports/`, for example `data/reports/1435790-escape-simulator/`:

- `screenshot-30s.jpg` and `screenshot-90s.jpg`: the game 30 seconds in and just before it was closed, with
  Playden's performance overlay (frame rate, frame times, memory, GPU load) where the game supports it;
- `playden-report.zip`: Playden's logs for the game, with your Steam name and SteamIDs hidden;
- `issue.md`: a ready-to-paste draft for a test report on
  [Playden's issue tracker](https://github.com/leolobato/playden-ps5/issues/new?template=test-report.yml). Nothing is
  posted for you: read it, check the screenshots, and post it yourself if you want to share the result;
- `result.json`: the result in short.

A game "survived" when it was still running after 90 seconds. A black screen counts as not working. How games are
chosen, tested and judged, and what the tests do not cover, is in
[docs/testing-methodology.md](docs/testing-methodology.md).

## What the console needs

| Service | Port | Why |
| --- | --- | --- |
| [ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) | 8888 | Lists titles, reads logs, writes the launch request, sends the launch payload |
| [elfldr](https://github.com/ps5-payload-dev/elfldr) | 9021 | Runs the payload that starts a game |
| Playden 0.8.0 or later | | Ships `self-update-relaunch.elf`, which the tester uses to start titles |

Plus the payloads Playden itself needs (kstuff, ShadowMountPlus).

## How it works

- **Starting a game.** Playden's self-update helper, `/data/homebrew/FAKE77031/self-update-relaunch.elf`, starts the
  title named in `/data/playden/self-update/relaunch-title` with `sceLncUtilLaunchApp`. The tester writes the game's
  title ID there, sends the helper to elfldr, and reads the helper's result from `relaunch.log`.
- **Is it running?** A running title has a folder `/mnt/sandbox/<title>_000`.
- **What happened?** After the game ends, Playden writes the session to `/data/playden/logs/title-<title>.log`. The
  tester finds the new session by its `PW_REPORT` start time and looks for fatal lines (`Crash!!!`, unhandled
  exceptions, failed loads).

Each game ends up with one status:

| Status | Meaning |
| --- | --- |
| `survived` | Still running after the watch time (120 s by default). It did not crash; it may still be a black screen. |
| `crashed` | Quit before the watch time, with a fatal line in its log |
| `exited_early` | Quit before the watch time, nothing fatal in its log |
| `did_not_start` | Launched, but no sandbox appeared |
| `launch_failed` | The launch helper could not start it |
| `not_closed` | Survived, but was not closed in time, so the run stopped |

Without padd (below), close a game that survived on the PS5 yourself: on Home, Options on its tile, Close Game.
Going Home alone leaves it running. The run then goes on to the next game.

## Seeing the screen: capture card

With an HDMI capture card on the PC and ffmpeg installed (`winget install Gyan.FFmpeg`), the tester looks at a game
that survived before closing it: a screenshot goes into its report, and a few seconds of video say whether the
picture is **black**, **still** (a menu, or frozen) or **moving**. A black screen fails the game.

On the PS5, turn off Settings › System › HDMI › **Enable HDCP**, or the card gets no picture. A card that only takes
1080p60 also needs Settings › Screen and Video › Video Output at 1080p, with 120 Hz, VRR and HDR off. Only one program
can use the card: close the Camera app and OBS first.

```sh
playden-tester snapshot --list                     # capture device names
set PS5_CAPTURE=USB Capture HDMI                   # PowerShell: $env:PS5_CAPTURE = "USB Capture HDMI"
playden-tester snapshot home.png --check 3         # one frame, plus black/still/moving
playden-tester run                                 # screen checks and screenshots are now part of each test
```

## Direct control: padd

[padd](https://github.com/leolobato/ps5-mcp) (MIT, from ps5-mcp by Playden's author) is a payload that adds a
virtual DualSense to the console and takes commands on TCP 9305: buttons and sticks, launch a title, close the
running game, go Home. With padd running, the tester closes each game after the watch time, so a run needs nobody
at the console. Games are still launched through Playden's relaunch helper: padd's own launch call is refused for
Playden's game titles (0x80940033, "Can't start the game or app", CE-105773-3).

A run stops after two launches in a row fail. A console that got stuck refusing every title, Playden included, came
back after a restart.

Build it once, on WSL or Linux (pinned ps5-mcp commit and PS5 Payload SDK v0.43, checked by SHA-256):

```sh
wsl -d Ubuntu -- sudo apt install -y clang-18 lld-18 unzip
wsl -d Ubuntu -- bash scripts/build-padd.sh      # writes build/padd/padd.elf
```

Then, after each console boot:

```sh
playden-tester padd start     # uploads build/padd/padd.elf to /data/playden-tester/ and runs it through elfldr
# the PS5 shows "Who's using this controller?"; with that dialog on screen:
playden-tester padd assign    # Cross from the virtual pad picks the focused user
playden-tester padd status
```

Assigning the virtual pad turns the DualSense off: press its PS button and pick your user to use both. The virtual
pad works on system screens (it dismisses error dialogs); whether a game started by the relaunch helper takes its
input is not tested yet. Stop padd with `playden-tester padd stop`; killing it another way can leave a phantom controller
until the console restarts.

```sh
playden-tester press cross                 # buttons: cross circle square triangle up down left right l1 r1 l2 r2 l3 r3 options touchpad
playden-tester press down --repeat 3
playden-tester stick left 0 -1 --seconds 1 # x y from -1 to 1, up and left negative
playden-tester close                       # close the running game
playden-tester home                        # suspend it and show Home
```

The PS button itself can't be sent from a virtual pad; `home` and `close` cover what it is used for.

## Use

Python 3.10 or later; no other packages.

```sh
pip install -e .
set PS5_HOST=172.16.20.5        # PowerShell: $env:PS5_HOST = "172.16.20.5"
playden-tester doctor           # checks ports, Playden version, firmware, launch helper
playden-tester list             # the Playden games on the console
playden-tester logs FAKE78009   # the newest session of a game, from its log
playden-tester launch FAKE78009 # start one game
playden-tester run              # test every game
playden-tester run --only FAKE78009 FAKE78019 --watch 180
```

`python -m playden_tester ...` works without installing.

A run writes `results/run-<time>/`: `results.json`, `summary.csv`, and `<title>.md` for each game, in the shape of
Playden's [test report](https://github.com/leolobato/playden-ps5/blob/main/docs/sample-test-report.md).

## Campaigns: download, test, collect logs, uninstall

With padd and a capture card, the tester can drive Playden's own screens: it reads them with Windows' built-in OCR
and checks each step before it presses anything that changes something.

```sh
playden-tester library --controller full          # your Steam games with full controller support (asks the Steam store)
playden-tester library --controller partial       # and those with partial support
playden-tester reported                           # games of that list others already reported on Playden's tracker
playden-tester ports                              # which of them also came out on consoles (Wikidata)
playden-tester features                           # pads, multiplayer and anti-cheat of each (Steam store)
playden-tester protondb                           # how well each runs on Linux through Proton (ProtonDB)
playden-tester campaign --max-gb 20 --limit 10    # the next 10 games of both lists
```

The other commands read both lists, `data/games-controller-full.json` and `data/games-controller-partial.json`;
`--list FILE ...` names others. Games with full controller support are tested before games with partial support,
whose menus or some parts may need a mouse or keyboard. Steam's `controller_support` field only ever says "full", so
`library` finds partial support by the store's "Partial Controller Support" category.

`update` runs `reported`, `ports`, `features` and `protondb` in one go and then rebuilds the lists of games still to
test, so keeping them current takes one command. Only `library` and `campaign` need the console.

```sh
playden-tester update             # check Playden's tracker for new reports and rebuild the lists (a few minutes)
playden-tester update --players   # also read Steam player numbers again (about half an hour more)
```

The lists are [`data/games-to-test.md`](data/games-to-test.md), in the order `campaign` tests them, and
[`data/games-by-players.md`](data/games-by-players.md), the same games by average Steam players in the last 30 days
(from [SteamCharts](https://steamcharts.com)). `lists` rebuilds them from what the other commands wrote, and `players`
reads the player numbers into `data/steam-players.json`. Release years come from Wikidata and the Steam store and are
kept in `data/release-years.json`, so only new games are looked up. A game whose campaign run went wrong in the
tester itself (status `error`) stays on the list, marked for a retest, and the next campaign tests it again.

`reported` reads every issue on [leolobato/playden-ps5](https://github.com/leolobato/playden-ps5/issues) and its
`COMPATIBILITY.md`, and writes the games with a test report (one that links the game's Steam or SteamDB page, or is
titled with its name) or a row in the compatibility list to
`data/tested-by-others.json`; `campaign` then skips them. Run it again for newer reports.

`campaign` also skips the games in `data/multiplayer-anticheat.json`: multiplayer games with anti-cheat (Easy
Anti-Cheat, BattlEye, VAC and the like), which cannot be played online under Playden. `features` writes it: for each
game it reads Steam's feature categories and store page, and counts a multiplayer game as having anti-cheat when its
page shows Steam's anti-cheat notice, its Steam Deck or SteamOS result says "unsupported anti-cheat", it has the
"Valve Anti-Cheat enabled" category, or [AreWeAntiCheatYet](https://areweanticheatyet.com) lists it. Rows added to the
file by hand stay. The store features go to `data/store-features.json`, and a second run only looks up new games. `--skip FILE ...` names
other lists, `--skip` alone skips none, and `--only` always tests the games it names.

`ports` looks up each game's platforms on Wikidata (by its Steam app ID) and writes `data/console-ports.json`.
`campaign` then tests the games with no console version first, then games on other consoles only (Xbox, Nintendo),
then games released on a PlayStation, with games that came out on PS4 or PS5, which play on the PS5 without Playden,
last. Installed games still come first, and games missing
from Wikidata count as having no console version. `--ports ''` keeps the list's order. Within each of those groups,
games with Steam's "DualSense Controller Support" go first, then "DualShock Controller Support", from
`data/store-features.json` (`--features ''` leaves that out). Unauthenticated, GitHub allows 60 requests an
hour; set `GITHUB_TOKEN` for more.

`protondb` reads each game's [ProtonDB](https://www.protondb.com) rating and writes `data/protondb.json`. `campaign`
then sorts by rating, after the controller support and before the console and pad order above: Platinum first, then
Gold, Silver, Bronze and Borked, with games rated Pending (too few reports) or missing from ProtonDB last. Installed
games still come first. `--protondb ''` leaves the rating out.

For each game, `campaign`:

1. downloads it through Playden if it is not installed (Library > All > Search; the game is confirmed by its page),
   and waits until its page offers Play;
2. tests it: launch, watch, screen check, screenshot, close;
3. starts Playden, which writes the game's session to its title log;
4. writes a redacted logs zip, the way Playden's `tools/collect_logs.py` does (Steam account names and SteamIDs
   replaced; `/data/playden/user` is never read except the library cache), and a draft for Playden's test-report
   issue form in `results/campaign/issues/`. Nothing is posted;
5. uninstalls it through Settings > Storage > Installed games, keeping its saves (`--keep` skips this).

Each game also gets a folder in `data/reports/<app>-<name>/` (`--reports FOLDER`, `''` for none):

- `screenshot.jpg`: the screen while the game ran, or, when it had already quit, the screen before the next game;
- `playden-report.zip`: the report zip of Playden's web access (Playden 0.9.0 or later, port 7031), the one its Logs
  page offers, with the game's title log. Playden redacts the Steam account name and SteamIDs. When web access does
  not answer, the folder gets the tester's own redacted `logs.zip` instead;
- `issue.md`: a draft for Playden's test-report issue form, naming the zip and screenshot beside it to attach;
- `result.json`: status, detail and screen check.

On Playden 0.10 the campaign waits for Playden to finish preparing a game (`prepare result app=<app> ready` in its
`runtime.log`) before starting it: the PS5 title exists from the start of the preparation, and a game started before
the end quits at once or is refused (0x80940031). Playden stays behind after a game, so the campaign opens it again
from its tile on the PS5's Home.

Progress is in `results/campaign/campaign.json`: run the same command again to go on. A campaign stops after three
games in a row go wrong, or two failed launches.

`library` reads only Playden's library cache (`library-<SteamID>.cache`), never `session.v1` beside it, which holds
the Steam sign-in. The lists and the store cache go to `data/`, which is not committed, except
[`data/games-to-test.md`](data/games-to-test.md), the games still to test in campaign order, and
[`data/games-by-players.md`](data/games-by-players.md), the same games by Steam players in the last 30 days.

## Tests

```sh
python -m unittest discover -s tests
```
