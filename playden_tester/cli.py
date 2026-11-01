"""Command line: playden-tester doctor | list | launch | logs | run."""
import argparse
import os
import re
import sys
import time
from pathlib import Path

from . import catalog, titlelog
from .console import ELFLDR_PORT, LOGS, PLAYDEN, RELAUNCH_ELF, HOMEBREW, Console, LaunchError
from .filemanager import FileManager, FileManagerError
from .report import RunWriter
from .runner import Runner, Settings, STUCK

PORTS = {8888: "ps5-web-file-manager (required)", ELFLDR_PORT: "elfldr (required to launch games)",
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
    busy = {t for t in console.running_titles() if t.startswith("FAKE78")}
    if busy:
        print(f"A game is already running ({', '.join(sorted(busy))}). Close it first.", file=sys.stderr)
        return 1
    folder = Path(args.out) / time.strftime("run-%Y%m%d-%H%M%S")
    writer = RunWriter(folder, {"host": args.host, "watch_seconds": args.watch, **console_facts(files)})
    runner = Runner(console, Settings(watch=args.watch, close_timeout=args.close_timeout))
    print(f"Testing {len(games)} games; results in {folder}")
    for number, game in enumerate(games, 1):
        print(f"--- {number}/{len(games)}")
        result = runner.run(game)
        writer.add(result)
        print(f"[{game.title}] {result.status} {result.detail}".rstrip())
        if result.status == STUCK:
            print("Stopping: the game was not closed.", file=sys.stderr)
            return 2
    passed = sum(r.passed for r in writer.results)
    print(f"Done: {passed}/{len(writer.results)} survived {args.watch:.0f} s. See {folder / 'summary.csv'}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="playden-tester", description="Test Playden games on a jailbroken PS5 remotely.")
    parser.add_argument("--host", default=os.environ.get("PS5_HOST"), help="PS5 address (or set PS5_HOST)")
    parser.add_argument("--port", type=int, default=8888, help="ps5-web-file-manager port")
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
    args = parser.parse_args(argv)
    if not args.host:
        parser.error("give --host or set PS5_HOST")
    try:
        return args.func(args)
    except FileManagerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
