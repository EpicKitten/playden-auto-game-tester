"""The PS5's own Remote Play: its power state over the network, and pictures of its screen with no capture card.

Pictures come from a chiaki-ng window, so that window has to be open, and it's brought to the front for each one.
chiaki-ng must be paired with the console once, by hand. It keeps its own pairing key, and this module never reads it.
"""
import ctypes
import ctypes.wintypes
import glob
import os
import socket
import subprocess
import time
from pathlib import Path

from .capture import find_ffmpeg

DISCOVERY_PORT = 9302
PROTOCOL = "00030010"
BLACK_BELOW = 3.0  # mean brightness of a stream's window before its first picture
CONNECT_SECONDS = 10.0  # a new window shows chiaki-ng's own screens before the console's picture


class RemotePlayError(Exception):
    pass


def parse_discovery(reply):
    """The console's answer as a dict: its first line gives the state, the rest are header lines."""
    lines = reply.decode("utf-8", "replace").splitlines()
    code = lines[0].split(" ", 2)[1:] if lines else []
    state = {"200": "ready", "620": "standby"}.get(code[0] if code else "", "unknown")
    fields = dict(line.split(":", 1) for line in lines[1:] if ":" in line)
    return {"state": state, "name": fields.get("host-name"), "type": fields.get("host-type"),
            "firmware": fields.get("system-version"), "running_app": fields.get("running-app-titleid")}


def discover(host, timeout=3.0):
    """Ask the console for its power state. An answer means it's on or in rest mode; None means off or unreachable."""
    message = f"SRCH * HTTP/1.1\ndevice-discovery-protocol-version:{PROTOCOL}\n".encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as link:
        link.settimeout(timeout)
        link.sendto(message, (host, DISCOVERY_PORT))
        try:
            return parse_discovery(link.recv(2048))
        except OSError:
            return None


def find_chiaki():
    names = [os.environ.get("CHIAKI_EXE", ""), r"C:\Program Files\chiaki-ng\chiaki.exe",
             *glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Programs\chiaki-ng\chiaki.exe"))]
    found = next((name for name in names if name and Path(name).is_file()), None)
    if not found:
        raise RemotePlayError("chiaki-ng not found: install it (winget install --id StreetPea.chiaki-ng -e), or set "
                              "CHIAKI_EXE")
    return found


def window_of(pid):
    """(handle, left, top, width, height) of the inside of a process's largest visible window, or None: its outer
    frame includes pixels of whatever is behind it. It's found by process because the user may have chiaki-ng open
    too, with the same title."""
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()  # the same pixels as ffmpeg's
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def look(window, _):
        owner, box, corner = ctypes.wintypes.DWORD(), ctypes.wintypes.RECT(), ctypes.wintypes.POINT()
        user32.GetWindowThreadProcessId(window, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(window) and user32.GetClientRect(window, ctypes.byref(box)) \
                and user32.ClientToScreen(window, ctypes.byref(corner)):
            found.append((window, corner.x, corner.y, box.right, box.bottom))
        return True

    user32.EnumWindows(look, 0)
    return max(found, key=lambda w: w[3] * w[4], default=None)


def brightness(path):
    from PIL import Image, ImageStat
    return ImageStat.Stat(Image.open(path).convert("L")).mean[0]


class RemoteView:
    """A chiaki-ng stream window, kept open between pictures once started."""

    def __init__(self, host, nickname, grab_seconds=25.0):
        self.host, self.nickname, self.grab_seconds = host, nickname, grab_seconds
        self.process, self.started = None, 0.0

    def open(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        if not self.open():
            self.process = subprocess.Popen([find_chiaki(), "--exit-app-on-stream-exit", "stream", self.nickname,
                                             self.host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.started = time.monotonic()

    def stop(self):
        if self.open():
            self.process.terminate()
            try:
                self.process.wait(10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def _grab(self, path):
        """Save what this stream's own window shows. ffmpeg copies that part of the desktop, so the window goes to
        the front first, or whatever covers it would be saved instead."""
        window = window_of(self.process.pid)
        if not window or window[3] < 200 or window[4] < 200:
            return False
        handle, left, top, width, height = window
        ctypes.windll.user32.SetForegroundWindow(handle)
        time.sleep(0.4)
        done = subprocess.run([find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab",
                               "-offset_x", str(left), "-offset_y", str(top), "-video_size", f"{width}x{height}",
                               "-i", "desktop", "-frames:v", "1", "-update", "1", str(path)],
                              capture_output=True, text=True, timeout=30)
        return done.returncode == 0

    def snapshot(self, path):
        """Save the stream's picture, waiting for its first frame when the window has just opened."""
        self.start()
        deadline = self.started + self.grab_seconds
        if time.monotonic() >= deadline:
            deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if not self.open():
                raise RemotePlayError("chiaki-ng closed: is the console on, and paired with chiaki-ng?")
            if time.monotonic() < self.started + CONNECT_SECONDS:
                time.sleep(0.5)
            elif self._grab(path) and brightness(path) >= BLACK_BELOW:
                return path
            else:
                time.sleep(1.0)
        raise RemotePlayError(f"no picture from chiaki-ng after {self.grab_seconds:.0f} s; its window may be "
                              "minimised, or this screen may be blocked from Remote Play")
