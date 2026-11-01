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

## Direct control: padd

[padd](https://github.com/leolobato/ps5-mcp) (MIT, from ps5-mcp by Playden's author) is a payload that adds a
virtual DualSense to the console and takes commands on TCP 9305: buttons and sticks, launch a title, close the
running game, go Home. With padd running, the tester launches games through it and closes each one after the watch
time, so a run needs nobody at the console.

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

Assigning the virtual pad turns the DualSense off: press its PS button and pick your user to use both. A game
takes input only from the controller that launched it, so games the tester launches through padd answer the
virtual pad only. Stop padd with `playden-tester padd stop`; killing it another way can leave a phantom controller
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

## Tests

```sh
python -m unittest discover -s tests
```
