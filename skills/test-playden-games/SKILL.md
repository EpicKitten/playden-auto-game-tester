---
name: test-playden-games
description: Use when testing Playden games on the PS5, checking the console, looking at its screen, pressing pad buttons, moving files, running payloads, power control, or starting and following a test campaign. Needs the ps5 tools from this plugin.
---

# Test Playden games

The `ps5` tools drive a jailbroken PS5 from this PC. AGENTS.md in this repo has the full rules and what Playden does.

## Start here

1. Call `status`. It shows which services answer and whether a campaign is running.
2. If `ps5-web-file-manager` or `padd` is down, call `start_services`. After padd starts, the PS5 asks "Who's using
   this controller?": check with `screenshot`, then `press` `cross`.
3. If nothing answers, the console is off, asleep or lost its jailbreak. Ask the user to load the payloads. No tool
   can fix that.

## Testing games

Use `campaign_start` for testing. It installs, tests, reports and uninstalls one game after another, and keeps going
after this session ends. Pick one game with `only: [<Steam app>]`, or a small batch with `limit`.

- A campaign starts padd itself and recovers from most failures. If it stops, read `campaign_status` and look at
  `results/campaign/recovery/`.
- `disk` gives real free space. Trust it over the number on Playden's Storage page.
- `campaign_status` shows counts and the log. Don't poll it: a game takes from minutes to many hours.
- `campaign_stop` stops before the next game. Leave the current game to finish, or its download stays paused.
- `order: "size"` suits a nearly full console. The default tests the most played games first, which are the largest.
- Input and capture tools refuse while a campaign runs, because it needs the pad and capture card.
- Run `update_lists` before a long campaign, so games others just reported are left out.

## Seeing the screen without a capture card

`screenshot` with `source: "remote"` works when the card is missing or busy. It opens a chiaki-ng window, brings it to
the front for each picture, and the console shows a notification. The first picture takes about 10 seconds. Call `remote_view_stop` when you're done. `status` reports
`remote_play`: `ready`, `standby` (rest mode), or null when the console is off or unreachable.

## Driving the console by hand

Look, then act, then look again: `screenshot` or `read_screen`, `press`, `screenshot`. Playden's UI needs a moment
after each press. Never guess at buttons from memory of an older screen.

## Rules

- **Never post to Playden's tracker.** Reports stay as local drafts until the user reviews them.
- **`session.v1` holds the Steam sign-in.** The tools refuse it. Don't look for a way around that.
- **Keep saves.** Never turn on "Delete saves too" in Playden's uninstall dialog.
- **Tested games are uninstalled afterwards,** even ones installed before the campaign. Untested games are never
  removed.
- **`file_delete` is permanent.** Keep its `dry_run` default, and pass `false` only when the user asked for that
  exact delete. Show them the dry run first.
- **`storage_clean` permanently removes data.** Use it only when the user asked. It stays away from Kept game data.
- **`power` is only for when the user asks.** Nothing here can wake the console, and a restart loses the jailbreak
  until the user loads it again. A running game loses unsaved progress.
- `process_kill` on kstuff or ShadowMountPlus stops games from launching until they're loaded again.
