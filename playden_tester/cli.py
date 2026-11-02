"""Command line: playden-tester doctor | list | launch | logs | run | padd | press | stick | close | home | library |
campaign | reported | ports | snapshot."""
import argparse
import os
import re
import sys
import time
from pathlib import Path

from . import catalog, titlelog
from .console import ELFLDR_PORT, LOGS, PLAYDEN, RELAUNCH_ELF, HOMEBREW, Console, LaunchError
from .capture import Capture, CaptureError, list_devices
from .filemanager import FileManager, FileManagerError
from .library import LibraryError, fill_store_details, read_library
from .padd import BUTTONS, PORT as PADD_PORT, PaddError
from .report import RunWriter
from .runner import LAUNCH_FAILED, Runner, Settings, STUCK

MAX_FAILED_LAUNCHES = 2
PADD_BUILD = Path(__file__).resolve().parent.parent / "build" / "padd" / "padd.elf"

PORTS = {8888: "ps5-web-file-manager (required)", ELFLDR_PORT: "elfldr (required to launch games)",
         PADD_PORT: "padd virtual controller (optional: input, unattended close)",
         2120: "zftpd FTP (optional)", 7031: "Playden web access, 0.9.0+ (optional)"}


def connect(args):
    files = FileManager(args.host, args.port)
    return files, Console(files, args.host)


def console_facts(files):
    facts = {}
    try:
        facts["playden_version"] = files.download(f"{HOMEBREW}/{PLAYDEN}/playden-version").decode().strip()
    except FileManagerError:
        pass
    try:
        match = re.search(r"console_firmware=(\S+)", files.download(f"{LOGS}/runtime.log").decode("utf-8", "replace"))
        if match:
            facts["firmware"] = match.group(1)
    except FileManagerError:
        pass
    return facts


def cmd_doctor(args):
    files, console = connect(args)
    ok = True
    for port, label in PORTS.items():
        is_open = console.port_open(port)
        ok &= is_open or "required" not in label
        print(f"  {'OPEN  ' if is_open else 'closed'} {port:5}  {label}")
    if not files.ping():
        print("The file manager does not answer; nothing else can be checked.")
        return 1
    facts = console_facts(files)
    print(f"  Playden {facts.get('playden_version', '?')}, firmware {facts.get('firmware', '?')}")
    has_helper = files.exists(f"{HOMEBREW}/{PLAYDEN}", "self-update-relaunch.elf")
    ok &= has_helper
    print(f"  launch helper {RELAUNCH_ELF}: {'found' if has_helper else 'MISSING'}")
    print(f"  running now: {', '.join(sorted(console.running_titles())) or 'nothing'}")
    if console.has_padd():
        try:
            info = console.padd.hello()
            print(f"  padd {info['version']}: pad {'ready' if info['pad_ready'] else 'NOT ready'}, "
                  f"user {info['user'] or info['user_id']}")
        except PaddError as error:
            print(f"  padd: {error}")
    if args.capture:
        try:
            check = Capture(args.capture).check(2)
            print(f"  capture {args.capture!r}: screen {check.verdict} (brightness {check.brightness:.0f})")
        except CaptureError as error:
            print(f"  capture: {error}")
    else:
        print("  capture: none (--capture or PS5_CAPTURE; 'snapshot --list' shows the devices)")
    print("Ready to test." if ok else "Not ready: fix the items above.")
    return 0 if ok else 1


def cmd_list(args):
    files, _ = connect(args)
    for game in catalog.games(files):
        app = f"steam {game.steam_app}" if game.steam_app else ""
        print(f"{game.title}  {app:14}  {game.name}")
    return 0


def cmd_launch(args):
    _, console = connect(args)
    try:
        console.launch(args.title)
    except LaunchError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{args.title} started.")
    return 0


def cmd_logs(args):
    _, console = connect(args)
    sessions = titlelog.parse(console.title_log(args.title))
    if not sessions:
        print("No sessions in the log.")
        return 1
    for session in sessions[: args.sessions]:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(session.start))
        print(f"== {session.name}  started {when}  lasted {session.duration} s  steam {session.steam_app}")
        for label, line in session.problems:
            print(f"  {label}: {line}")
        if session.wine_errors:
            print("  wine err: " + ", ".join(f"{k} x{v}" for k, v in session.wine_errors.items()))
        print(session.tail(args.tail))
    return 0


def cmd_run(args):
    files, console = connect(args)
    if not console.port_open(ELFLDR_PORT):
        print(f"elfldr is not running on port {ELFLDR_PORT}. Load it on the PS5, then run again.", file=sys.stderr)
        return 1
    games = catalog.games(files)
    if args.only:
        wanted = {t.upper() for t in args.only}
        games = [g for g in games if g.title in wanted]
    def busy():
        return sorted(t for t in console.running_titles() if t.startswith("FAKE78"))

    if busy():
        print(f"A game is already running ({', '.join(busy())}). Close it on the PS5 "
              f"(Home: Options on its tile, Close Game); waiting up to {args.close_timeout:.0f} s")
        deadline = time.monotonic() + args.close_timeout
        while busy() and time.monotonic() < deadline:
            time.sleep(2)
        if busy():
            print("It is still running; nothing tested.", file=sys.stderr)
            return 1
    folder = Path(args.out) / time.strftime("run-%Y%m%d-%H%M%S")
    writer = RunWriter(folder, {"host": args.host, "watch_seconds": args.watch, **console_facts(files)})
    auto_close = console.has_padd()
    print("padd is running: games are closed for you." if auto_close else
          "padd is not running: close each game on the PS5 when asked (or start padd: 'padd start').")
    capture = Capture(args.capture) if args.capture else None
    print(f"Screen checks through {args.capture!r}." if capture else "No capture card: no screen checks or screenshots.")
    runner = Runner(console, Settings(watch=args.watch, close_timeout=args.close_timeout, auto_close=auto_close),
                    capture=capture, shots=folder)
    print(f"Testing {len(games)} games; results in {folder}")
    failed_launches = 0
    for number, game in enumerate(games, 1):
        print(f"--- {number}/{len(games)}")
        result = runner.run(game)
        writer.add(result)
        print(f"[{game.title}] {result.status} {result.detail}".rstrip())
        if result.status == STUCK:
            print("Stopping: the game was not closed.", file=sys.stderr)
            writer.rewrite(runner.fill_pending())
            return 2
        failed_launches = failed_launches + 1 if result.status == LAUNCH_FAILED else 0
        if failed_launches >= MAX_FAILED_LAUNCHES:
            # A console that refuses one launch after another is stuck (it showed "Can't start the game or app"
            # for every title, Playden included, until it was restarted); more launches only add error dialogs.
            print(f"Stopping: {failed_launches} launches in a row failed. Check the PS5 (a restart may be needed).",
                  file=sys.stderr)
            return 3
    writer.rewrite(runner.fill_pending())
    for result, _ in runner.pending:
        print(f"[{result.title}] its session never reached the log")
    passed = sum(r.passed for r in writer.results)
    print(f"Done: {passed}/{len(writer.results)} survived {args.watch:.0f} s. See {folder / 'summary.csv'}")
    return 0


def cmd_padd(args):
    files, console = connect(args)
    if args.action == "start":
        elf = Path(args.elf) if args.elf else PADD_BUILD
        if not elf.is_file():
            print(f"{elf} not found. Build it first: wsl -d Ubuntu -- bash scripts/build-padd.sh", file=sys.stderr)
            return 1
        try:
            started = console.start_padd(elf.read_bytes())
        except LaunchError as error:
            print(error, file=sys.stderr)
            return 1
        if not started:
            print("padd is already running.")
            return 0
        print("padd started. The PS5 now asks \"Who's using this controller?\". Once you see that dialog,\n"
              "run 'padd assign' to answer it with the virtual pad (this turns your DualSense off; press its PS\n"
              "button and pick your user to bring it back).")
        return 0
    if not console.has_padd():
        print(f"padd is not running on port {PADD_PORT}.", file=sys.stderr)
        return 1
    if args.action == "status":
        info = console.padd.hello()
        print(f"padd {info['version']}, pad {'ready' if info['pad_ready'] else 'not ready'}, "
              f"user {info['user'] or info['user_id']}")
    elif args.action == "assign":
        console.padd.press("cross")
        print("Pressed Cross on the virtual pad.")
    elif args.action == "stop":
        console.padd.shutdown()
        print("padd stopped and its controller removed.")
    return 0


def cmd_press(args):
    _, console = connect(args)
    for _ in range(args.repeat):
        console.padd.press(*args.buttons, seconds=args.hold)
        time.sleep(args.gap)
    return 0


def cmd_stick(args):
    _, console = connect(args)
    console.padd.stick(args.side, args.x, args.y, args.seconds)
    return 0


def cmd_close(args):
    _, console = connect(args)
    running = [t for t in console.running_titles() if t.startswith("FAKE") or t.startswith("PPSA")]
    try:
        console.close(running[0] if len(running) == 1 else None)
    except LaunchError as error:
        print(error, file=sys.stderr)
        return 1
    print("Closed the running game.")
    return 0


def cmd_home(args):
    _, console = connect(args)
    console.padd.home()
    return 0


def cmd_snapshot(args):
    if args.list:
        for name in list_devices():
            print(name)
        return 0
    if not args.capture:
        print("give --capture or set PS5_CAPTURE ('snapshot --list' shows the devices)", file=sys.stderr)
        return 1
    capture = Capture(args.capture)
    path = capture.snapshot(args.file or time.strftime("snapshot-%Y%m%d-%H%M%S.png"))
    print(path)
    if args.check:
        print(capture.check(args.check).as_dict())
    return 0


def cmd_library(args):
    """Your Steam library with controller support from the store; writes a JSON and a CSV list."""
    import csv
    import json
    files, _ = connect(args)
    games = read_library(files)
    cache_path = Path(args.data) / "store-cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    print(f"{len(games)} Steam games in the library; {sum(str(g.app) not in cache for g in games)} to look up")
    try:
        fill_store_details(games, cache)
    finally:
        cache_path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    installed = {g.steam_app for g in catalog.games(files, read_logs=True) if g.steam_app}
    rows = [dict(g.as_dict(), installed=g.app in installed) for g in games
            if (args.controller == "any" or g.controller == args.controller) and g.store_type in ("game", "")
            and "windows" in g.platforms and not g.demo]
    rows.sort(key=lambda row: row["title"].lower())
    out = Path(args.data) / f"games-controller-{args.controller}"
    out.with_suffix(".json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, ["app", "title", "controller", "installed", "playtime_minutes", "family_shared",
                                         "developer", "platforms", "store_type", "demo"])
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for g in games:
        counts[g.controller or "unknown"] = counts.get(g.controller or "unknown", 0) + 1
    print("controller support: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"{len(rows)} Windows games with controller support '{args.controller}' "
          f"({sum(r['installed'] for r in rows)} installed): {out.with_suffix('.csv')}")
    return 0


def cmd_reported(args):
    """The games of a list that already have a test report on Playden's issue tracker."""
    import json
    from .reported import ReportedError, fetch_issues, reported_games
    games = json.loads(Path(args.list).read_text(encoding="utf-8"))
    try:
        issues = fetch_issues(args.repo, token=os.environ.get("GITHUB_TOKEN"))
    except ReportedError as error:
        print(error, file=sys.stderr)
        return 1
    found = reported_games(issues, games)
    names = {g["app"]: g["title"].strip() for g in games}
    rows = [{"app": app, "title": names[app], "issues": found[app]}
            for app in sorted(found, key=lambda app: names[app].lower())]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    for row in rows:
        print(f"{row['app']:>8}  {row['title']}  " + " ".join(f"#{i['number']}" for i in row["issues"]))
    print(f"{len(rows)} of {len(games)} games already have a test report on {args.repo} "
          f"({len(issues)} issues read): {out}")
    return 0


def cmd_ports(args):
    """Which games of a list also came out on consoles (Wikidata): campaigns test those last."""
    import json
    from .ports import NO_PORT, PLAYSTATION_PORT, PortsError, console_ports, fetch_platforms
    games = json.loads(Path(args.list).read_text(encoding="utf-8"))
    try:
        platforms = fetch_platforms([g["app"] for g in games])
    except PortsError as error:
        print(error, file=sys.stderr)
        return 1
    rows = []
    for g in games:
        rank, ports = console_ports(platforms.get(g["app"], set()))
        rows.append({"app": g["app"], "title": g["title"].strip(), "rank": rank, "ports": ports,
                     "on_wikidata": g["app"] in platforms})
    rows.sort(key=lambda row: (row["rank"], row["title"].lower()))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    counts = [sum(row["rank"] == rank for row in rows) for rank in range(NO_PORT, PLAYSTATION_PORT + 1)]
    print(f"{len(rows)} games: {counts[0]} with no console version, {counts[1]} on other consoles, "
          f"{counts[2]} on PS4 or PS5 ({sum(not row['on_wikidata'] for row in rows)} not on Wikidata): {out}")
    return 0


def cmd_campaign(args):
    from .campaign import Campaign, load_list
    from .playden_ui import PlaydenUI
    from .screen import Screen
    files, console = connect(args)
    if not args.capture:
        print("a campaign needs the capture card: give --capture or set PS5_CAPTURE", file=sys.stderr)
        return 1
    if not console.has_padd():
        print("a campaign needs padd: 'padd start', then 'padd assign'", file=sys.stderr)
        return 1
    if not console.port_open(ELFLDR_PORT):
        print(f"elfldr is not running on port {ELFLDR_PORT}", file=sys.stderr)
        return 1
    ranks = {}
    if args.ports and Path(args.ports).exists():
        from .ports import load_ranks
        ranks = load_ranks(Path(args.ports))
        print(f"games with a console version go last ({args.ports})")
    games = load_list(args.list, ranks)
    if args.only:
        wanted = {int(a) for a in args.only}
        games = [g for g in games if g.app in wanted]
    else:
        from .reported import load_apps
        for skip in filter(None, args.skip):
            if Path(skip).exists():
                apps = load_apps(Path(skip))
                print(f"skipping {sum(g.app in apps for g in games)} games listed in {skip}")
                games = [g for g in games if g.app not in apps]
    capture = Capture(args.capture)
    ui = PlaydenUI(console.padd, Screen(capture))
    out = Path(args.out)
    campaign = Campaign(console, ui, capture,
                        Settings(watch=args.watch, close_timeout=120, auto_close=True), out,
                        {"host": args.host, "watch_seconds": args.watch, **console_facts(files)},
                        keep=args.keep, max_gb=args.max_gb, reserve_gb=args.reserve_gb)
    from .library import read_library
    campaign.library = read_library(files)
    code = campaign.run(games, limit=args.limit)
    statuses = {}
    for entry in campaign.state.values():
        statuses[entry.get("status")] = statuses.get(entry.get("status"), 0) + 1
    print("campaign so far: " + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items(), key=str)))
    print(f"issue drafts in {out / 'issues'}, logs in {out / 'logs'}")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(prog="playden-tester", description="Test Playden games on a jailbroken PS5 remotely.")
    parser.add_argument("--host", default=os.environ.get("PS5_HOST"), help="PS5 address (or set PS5_HOST)")
    parser.add_argument("--port", type=int, default=8888, help="ps5-web-file-manager port")
    parser.add_argument("--capture", default=os.environ.get("PS5_CAPTURE"),
                        help="capture card device, e.g. \"USB Capture HDMI\" (or set PS5_CAPTURE)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check the console is ready for testing").set_defaults(func=cmd_doctor)
    sub.add_parser("list", help="list the Playden games on the console").set_defaults(func=cmd_list)
    p = sub.add_parser("launch", help="start one title")
    p.add_argument("title")
    p.set_defaults(func=cmd_launch)
    p = sub.add_parser("logs", help="show a title's newest sessions from its log")
    p.add_argument("title")
    p.add_argument("--sessions", type=int, default=1)
    p.add_argument("--tail", type=int, default=20)
    p.set_defaults(func=cmd_logs)
    p = sub.add_parser("run", help="test the games one after another")
    p.add_argument("--only", nargs="+", metavar="TITLE", help="test only these title IDs")
    p.add_argument("--watch", type=float, default=120.0, help="seconds a game must run to pass")
    p.add_argument("--close-timeout", type=float, default=600.0, help="seconds to wait for you to close a game")
    p.add_argument("--out", default="results", help="folder for the run results")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("padd", help="the virtual controller payload: start, status, assign, stop")
    p.add_argument("action", choices=["start", "status", "assign", "stop"])
    p.add_argument("--elf", help=f"padd.elf to upload (default {PADD_BUILD})")
    p.set_defaults(func=cmd_padd)
    p = sub.add_parser("press", help=f"press buttons on the virtual pad: {', '.join(BUTTONS)}")
    p.add_argument("buttons", nargs="+")
    p.add_argument("--hold", type=float, default=0.12, help="seconds to hold")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--gap", type=float, default=0.25, help="seconds between repeats")
    p.set_defaults(func=cmd_press)
    p = sub.add_parser("stick", help="move a stick: x and y from -1 to 1 (up and left negative)")
    p.add_argument("side", choices=["left", "right"])
    p.add_argument("x", type=float)
    p.add_argument("y", type=float)
    p.add_argument("--seconds", type=float, default=0.5)
    p.set_defaults(func=cmd_stick)
    sub.add_parser("close", help="close the running game (padd)").set_defaults(func=cmd_close)
    sub.add_parser("home", help="suspend the running game and show Home (padd)").set_defaults(func=cmd_home)
    p = sub.add_parser("library", help="list your Steam games by controller support (asks the Steam store)")
    p.add_argument("--controller", default="full", choices=["full", "partial", "none", "any"])
    p.add_argument("--data", default="data", help="folder for the lists and the store cache")
    p.set_defaults(func=cmd_library)
    p = sub.add_parser("campaign", help="download (through Playden), test, collect logs and uninstall each game of a list")
    p.add_argument("--list", default="data/games-controller-full.json", help="a list written by 'library'")
    p.add_argument("--out", default="results/campaign", help="folder for results, logs, issue drafts and progress")
    p.add_argument("--watch", type=float, default=90.0)
    p.add_argument("--max-gb", type=float, help="skip games bigger than this (default: none; storage is managed)")
    p.add_argument("--reserve-gb", type=float, default=15.0,
                   help="free space always left on the console; tested games are uninstalled to make room")
    p.add_argument("--limit", type=int, help="test at most this many games this time")
    p.add_argument("--only", nargs="+", metavar="APP", help="only these Steam app IDs")
    p.add_argument("--keep", action="store_true", help="do not uninstall games after testing")
    p.add_argument("--skip", nargs="*", metavar="FILE",
                   default=["data/tested-by-others.json", "data/multiplayer-anticheat.json"],
                   help="skip the games in these lists (JSON rows with an app; missing files are ignored): by default "
                        "the ones others already reported on and multiplayer games with anti-cheat; --skip alone "
                        "skips none")
    p.add_argument("--ports", default="data/console-ports.json", metavar="FILE",
                   help="test games with a console version last, PS4 and PS5 ones at the very end, from this list "
                        "written by 'ports' (if it exists); '' keeps the list's order")
    p.set_defaults(func=cmd_campaign)
    p = sub.add_parser("ports", help="find which games of a list also came out on consoles (Wikidata)")
    p.add_argument("--list", default="data/games-controller-full.json", help="a list written by 'library'")
    p.add_argument("--out", default="data/console-ports.json")
    p.set_defaults(func=cmd_ports)
    p = sub.add_parser("reported", help="find the games of a list that already have a test report on Playden's tracker")
    p.add_argument("--list", default="data/games-controller-full.json", help="a list written by 'library'")
    p.add_argument("--repo", default="leolobato/playden-ps5", help="GitHub repository (GITHUB_TOKEN raises the rate limit)")
    p.add_argument("--out", default="data/tested-by-others.json")
    p.set_defaults(func=cmd_reported)
    p = sub.add_parser("snapshot", help="save a frame from the capture card")
    p.add_argument("file", nargs="?", help="PNG or JPEG path (default snapshot-<time>.png)")
    p.add_argument("--list", action="store_true", help="list capture devices")
    p.add_argument("--check", type=float, metavar="SECONDS", help="also watch the screen: black, still or moving")
    p.set_defaults(func=cmd_snapshot)
    args = parser.parse_args(argv)
    if args.func is cmd_snapshot:
        try:
            return cmd_snapshot(args)
        except CaptureError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    if not args.host and args.func not in (cmd_reported, cmd_ports):  # these only read GitHub or Wikidata
        parser.error("give --host or set PS5_HOST")
    try:
        return args.func(args)
    except (FileManagerError, PaddError, CaptureError, LibraryError, ValueError, LaunchError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
