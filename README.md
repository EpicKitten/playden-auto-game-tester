# playden-auto-tester
An app to automatically test playden game compatibility on the PS5 remotely via PC

It starts each [Playden](https://github.com/leolobato/playden-ps5) game on a jailbroken PS5, watches whether it keeps
running, reads the game's log, and writes a result and a test report for each game.

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
playden-tester reported                           # games of that list others already reported on Playden's tracker
playden-tester ports                              # which of them also came out on consoles (Wikidata)
playden-tester features                           # pads, multiplayer and anti-cheat of each (Steam store)
playden-tester campaign --max-gb 20 --limit 10    # the next 10 games of data/games-controller-full.json
```

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

For each game, `campaign`:

1. downloads it through Playden if it is not installed (Library > All > Search; the game is confirmed by its page),
   and waits until its page offers Play;
2. tests it: launch, watch, screen check, screenshot, close;
3. starts Playden, which writes the game's session to its title log;
4. writes a redacted logs zip, the way Playden's `tools/collect_logs.py` does (Steam account names and SteamIDs
   replaced; `/data/playden/user` is never read except the library cache), and a draft for Playden's test-report
   issue form in `results/campaign/issues/`. Nothing is posted;
5. uninstalls it through Settings > Storage > Installed games, keeping its saves (`--keep` skips this).

Progress is in `results/campaign/campaign.json`: run the same command again to go on. A campaign stops after three
games in a row go wrong, or two failed launches.

`library` reads only Playden's library cache (`library-<SteamID>.cache`), never `session.v1` beside it, which holds
the Steam sign-in. The lists and the store cache go to `data/`, which is not committed.

## Tests

```sh
python -m unittest discover -s tests
```
