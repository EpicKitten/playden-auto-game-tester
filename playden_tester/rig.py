"""One object for everything the tester can do to the console: status, screen, input, files, payloads, power and
campaigns. The MCP server (mcp.py) exposes these as tools.

The rules in AGENTS.md live here, so every caller gets them: session.v1 can't be reached, deletes are limited and
dry runs by default, and a running campaign keeps the pad and capture card to itself.
"""
import base64
import io
import json
import os
import posixpath
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .capture import Capture
from .catalog import games as console_games
from .console import ELFLDR_PORT, LOGS, PLAYDEN, Console
from .filemanager import FileManager
from .padd import PORT as PADD_PORT
from .payloadmgr import PORT as PAYLOAD_MANAGER_PORT
from .payloadmgr import PayloadManager, send_elf
from .remoteplay import RemotePlayError, RemoteView, discover
from .screen import Screen, ocr
from .webaccess import PORT as WEB_PORT
from .webaccess import WebAccess

SERVICES = {PAYLOAD_MANAGER_PORT: "Payload Manager", ELFLDR_PORT: "elfldr", 8888: "ps5-web-file-manager",
            PADD_PORT: "padd", WEB_PORT: "Playden web access", 2120: "zftpd"}
PRIVATE = ("/data/playden/user/session.v1",)  # the Steam sign-in
DELETE_ROOTS = ("/data/playden-tester",)
POWER_ACTIONS = ("restart", "standby", "off")
ROOT = Path(__file__).resolve().parent.parent


class RigError(Exception):
    pass


def clean_path(path):
    """An absolute console path with any . and .. resolved, so a path can't walk around the checks below."""
    if not path.startswith("/"):
        raise RigError(f"{path}: give an absolute console path")
    return posixpath.normpath(path).replace("//", "/")


def check_private(path, tree=False):
    """Refuse the Steam sign-in; with tree (folder downloads), refuse the folders that hold it too."""
    path = clean_path(path)
    lowered = path.casefold()
    for private in PRIVATE:
        if lowered == private or (tree and (lowered == "/" or private.startswith(lowered.rstrip("/") + "/"))):
            raise RigError(f"{path}: refused, this holds the Steam sign-in")
    return path


def delete_roots():
    extra = os.environ.get("PS5_DELETE_ROOTS", "")
    return (*DELETE_ROOTS, *(clean_path(p) for p in extra.split(",") if p))


def check_delete(path):
    path = check_private(path, tree=True)
    roots = delete_roots()
    if not any(path.startswith(root + "/") for root in roots):
        raise RigError(f"{path}: deletes are limited to what's inside {', '.join(roots)} (PS5_DELETE_ROOTS adds more)")
    return path


def process_alive(pid):
    if sys.platform == "win32":  # os.kill(pid, 0) would send Ctrl+C here
        done = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in done.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class Rig:
    def __init__(self, host, capture=None, port=8888, root=ROOT):
        if not host:
            raise RigError("no console address: set PS5_HOST")
        self.host, self.root = host, Path(root)
        self.files = FileManager(host, port)
        self.console = Console(self.files, host)
        self.payloads = PayloadManager(host)
        self.capture = Capture(capture) if capture else None
        self.screen = Screen(self.capture) if capture else None
        self.campaign_dir = self.root / "results" / "campaign"
        self.view = RemoteView(host, os.environ.get("PS5_REMOTE_NAME") or "PS5")

    # Status

    def status(self):
        ports = {name: self.console.port_open(port) for port, name in SERVICES.items()}
        facts = {"host": self.host, "remote_play": discover(self.host), "services": ports,
                 "campaign": self.campaign_status()}
        if ports["ps5-web-file-manager"]:
            facts["running_titles"] = sorted(self.console.running_titles())
        if ports["padd"]:
            facts["pad"] = self.console.padd.hello()
        if ports["Playden web access"]:
            facts["playden"] = WebAccess(self.host, timeout=10).status()
        return facts

    def processes(self):
        return self.payloads.processes()

    # Screen

    def _quiet(self):
        """Refuse input and capture during a campaign, which needs both for itself."""
        if self.campaign_status()["running"]:
            raise RigError("a campaign is running and needs the pad and capture card; stop it first")

    def _capture(self):
        if not self.capture:
            raise RigError("no capture card: set PS5_CAPTURE")
        self._quiet()

    def screenshot(self, path=None, width=1280, source="card"):
        """(JPEG bytes small enough to look at, path of the full frame), from the capture card or from Remote Play."""
        target = Path(path) if path else Path(tempfile.gettempdir()) / "playden-rig-screenshot.png"
        if source == "remote":
            self._quiet()
            self.view.nickname = self._remote_name()
            self.view.snapshot(target)
        else:
            self._capture()
            self.capture.snapshot(target)
        from PIL import Image
        image = Image.open(target).convert("RGB")
        image.thumbnail((width, width))
        out = io.BytesIO()
        image.save(out, "JPEG", quality=80)
        return out.getvalue(), str(target)

    def _remote_name(self):
        """chiaki-ng finds its pairing by the console's name, which the console says itself."""
        found = discover(self.host)
        if not found:
            raise RemotePlayError("the console doesn't answer Remote Play: it may be off")
        return os.environ.get("PS5_REMOTE_NAME") or found["name"]

    def remote_view_stop(self):
        """Close the Remote Play window, which ends the session."""
        self.view.stop()

    def wake(self, timeout=60.0):
        """Wake the console from rest mode by starting a chiaki-ng stream, which uses its own pairing."""
        found = discover(self.host)
        if not found:
            raise RemotePlayError("the console doesn't answer: a console that's fully off can't be woken")
        if found["state"] == "ready":
            return found
        self.view.nickname = os.environ.get("PS5_REMOTE_NAME") or found["name"]
        self.view.start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            found = discover(self.host)
            if found and found["state"] == "ready":
                return found
            time.sleep(2.0)
        raise RemotePlayError(f"the console is still in rest mode {timeout:.0f} s after chiaki-ng started")

    def read_screen(self):
        """The text on screen with its positions, and the box around the focused item."""
        self._capture()
        lines, focus, path = self.screen.read(0.2)
        return {"lines": [vars(l) for l in lines], "focus": focus, "focused_text": [l.text for l in Screen.inside(lines, focus)],
                "image": str(path)}

    def screen_check(self, seconds=3.0):
        """Whether the picture is black, still or moving."""
        self._capture()
        return self.capture.check(seconds).as_dict()

    # Input

    def press(self, buttons, repeat=1, hold=0.12, gap=0.4):
        self._quiet()
        for number in range(repeat):
            self.console.padd.press(*buttons, seconds=hold)
            if number + 1 < repeat:
                time.sleep(gap)

    def stick(self, side, x, y, seconds=0.3):
        self._quiet()
        self.console.padd.stick(side, x, y, seconds)

    def home(self):
        self._quiet()
        self.console.padd.home()

    # Games

    def games(self):
        return [g.as_dict() for g in console_games(self.files, read_logs=False)]

    def launch(self, title):
        self._quiet()
        return self.console.launch(title)

    def close_app(self):
        self._quiet()
        running = [t for t in self.console.running_titles() if t.startswith(("FAKE", "PPSA")) and t != PLAYDEN]
        self.console.close(running[0] if len(running) == 1 else None)
        return running

    def title_log(self, title, tail=20000):
        return self.console.title_log(title)[-tail:]

    def runtime_log(self, tail=20000):
        return self.files.download(f"{LOGS}/runtime.log").decode("utf-8", "replace")[-tail:]

    # Files

    def file_list(self, path):
        return self.files.list(clean_path(path))

    def file_read(self, path):
        return self.files.read_text(check_private(path))[0]

    def file_write(self, path, text):
        self.files.write_text(check_private(path), text)

    def file_upload(self, local, path):
        path = check_private(path)
        folder, _, name = path.rpartition("/")
        self.files.upload(Path(local).read_bytes(), folder, name)

    def file_download(self, path, local):
        data = self.files.download(check_private(path, tree=True))
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        Path(local).write_bytes(data)
        return len(data)

    def file_delete(self, path, dry_run=True):
        """Delete inside the allowed folders. A dry run says what would go, and is the default."""
        path = check_delete(path)
        folder, _, name = path.rpartition("/")
        entry = next((e for e in self.files.list(folder) if e["name"] == name), None)
        if entry is None:
            raise RigError(f"{path}: not found")
        if not dry_run:
            self.files.delete(path)
            self._log(f"deleted {path}")
        return {"path": path, "deleted": not dry_run, "entry": entry}

    # Payloads

    def payload_list(self):
        return self.payloads.payloads()

    def payload_start(self, path):
        if path not in self.payloads.payloads():
            raise RigError(f"{path} isn't in Payload Manager's library")
        self.payloads.load(path)

    def payload_send(self, local):
        """Run a local ELF through elfldr. Nothing is written to the console's disk."""
        send_elf(self.host, Path(local).read_bytes(), ELFLDR_PORT)

    def process_kill(self, pid):
        name = self.payloads.kill(pid)
        self._log(f"killed process {pid} ({name})")
        return name

    def start_services(self, timeout=20.0):
        """Bring up the file manager and padd if they aren't running; what each one did."""
        done = {}
        if self.console.port_open(8888):
            done["ps5-web-file-manager"] = "already running"
        else:
            payload = self.payloads.find("web-file-manager", "webfilemanager", "file_manager", "file-manager")
            if not payload:
                done["ps5-web-file-manager"] = "not in Payload Manager's library"
            else:
                self.payloads.load(payload)
                done["ps5-web-file-manager"] = "started" if self._wait_port(8888, timeout) else "did not open port 8888"
        if self.console.has_padd():
            done["padd"] = "already running"
        else:
            elf = self.root / "build" / "padd" / "padd.elf"
            if not elf.is_file():
                done["padd"] = f"{elf} not built: scripts/build-padd.sh"
            else:
                send_elf(self.host, elf.read_bytes(), ELFLDR_PORT)
                done["padd"] = ("started; press cross once the PS5 asks who uses the controller"
                                if self._wait_port(PADD_PORT, timeout) else f"did not open port {PADD_PORT}")
        return done

    def _wait_port(self, port, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.console.port_open(port):
                return True
            time.sleep(0.5)
        return False

    # Power

    def power(self, action, wait=45.0):
        """Restart, enter rest mode or turn off through build/power/ps5power-<action>.elf. Whether the console went
        away is the only answer there is: payloads stop with it, and a restart loses the jailbreak."""
        if action not in POWER_ACTIONS:
            raise RigError(f"power action is one of {', '.join(POWER_ACTIONS)}")
        self._quiet()
        elf = self.root / "build" / "power" / f"ps5power-{action}.elf"
        if not elf.is_file():
            raise RigError(f"{elf} not built: scripts/build-power.sh")
        send_elf(self.host, elf.read_bytes(), ELFLDR_PORT)
        self._log(f"power {action}")
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            if not self.console.port_open(PAYLOAD_MANAGER_PORT):
                return {"action": action, "console_went_away": True}
            time.sleep(1.0)
        return {"action": action, "console_went_away": False}

    # Campaigns

    def _pid_file(self):
        return self.campaign_dir / "run.pid"

    def campaign_status(self):
        pid_file, state_file = self._pid_file(), self.campaign_dir / "campaign.json"
        pid = int(pid_file.read_text()) if pid_file.exists() else None
        counts = {}
        if state_file.exists():
            for entry in json.loads(state_file.read_text(encoding="utf-8")).values():
                counts[entry.get("status")] = counts.get(entry.get("status"), 0) + 1
        return {"running": bool(pid) and process_alive(pid), "pid": pid, "stopping": (self.campaign_dir / "stop").exists(),
                "results": counts}

    def campaign_log(self, lines=40):
        log = self.root / "results" / "campaign-run.log"
        return "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]) if log.exists() else ""

    def campaign_start(self, only=None, limit=None, order="players", watch=None):
        """Start a campaign that outlives this server; its output goes to results/campaign-run.log."""
        if self.campaign_status()["running"]:
            raise RigError("a campaign is already running")
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        (self.campaign_dir / "stop").unlink(missing_ok=True)
        command = [sys.executable, "-u", "-m", "playden_tester", "campaign"]
        if order == "size":
            command += ["--players", ""]
        elif order != "players":
            raise RigError("order is players or size")
        command += ["--only", *map(str, only)] if only else []
        command += ["--limit", str(limit)] if limit else []
        command += ["--watch", str(watch)] if watch else []
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
        with open(self.root / "results" / "campaign-run.log", "a", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=self.root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       creationflags=flags, start_new_session=sys.platform != "win32")
        self._pid_file().write_text(str(process.pid))
        return process.pid

    def campaign_stop(self):
        """Ask the campaign to stop before its next game, so no download is left paused."""
        if not self.campaign_status()["running"]:
            raise RigError("no campaign is running")
        (self.campaign_dir / "stop").write_text("")

    def update_lists(self):
        done = subprocess.run([sys.executable, "-m", "playden_tester", "update"], cwd=self.root, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        return done.stdout[-1500:] + done.stderr[-500:]

    def _log(self, text):
        log = self.root / "results" / "rig-actions.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as out:
            out.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}\n")


def jpeg_text(data):
    return base64.b64encode(data).decode()
