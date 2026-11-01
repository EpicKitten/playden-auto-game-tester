"""What the tester can do on the PS5: see what runs, read logs, start a title.

Starting a title reuses the helper Playden ships for its self-update,
self-update-relaunch.elf. It reads a title ID from REQUEST, waits for that
title's sandbox to go, and starts it with sceLncUtilLaunchApp. It writes its
result to RESULT. It needs elfldr running on the console (port 9021).
"""
import re
import socket
import time

from .filemanager import FileManagerError
from .padd import PORT as PADD_PORT, Padd, PaddError

PLAYDEN = "FAKE77031"
HOMEBREW = "/data/homebrew"
LOGS = "/data/playden/logs"
SANDBOX = "/mnt/sandbox"
RELAUNCH_ELF = f"{HOMEBREW}/{PLAYDEN}/self-update-relaunch.elf"
REQUEST = "/data/playden/self-update/relaunch-title"
RESULT = "/data/playden/self-update/relaunch.log"
ELFLDR_PORT = 9021
PADD_ELF = "/data/playden-tester/padd.elf"

TITLE_ID = re.compile(r"^[A-Z]{4}\d{5}$")
RC = re.compile(r"(sceLncUtilLaunchApp|sceSystemServiceLaunchApp) rc=0x([0-9a-f]{8})")


class LaunchError(Exception):
    pass


def launch_outcome(text):
    """From the helper's log: True started, False failed, None not finished yet."""
    if "bad title id" in text or "no request" in text:
        return False
    wait = re.search(r"wait state=(-?\d+)", text)
    if wait and wait.group(1) != "0":
        return False  # the title never left, or /mnt/sandbox could not be read
    codes = [int(code, 16) for _, code in RC.findall(text)]
    if codes and not codes[-1] & 0x80000000:
        return True
    if len(codes) >= 2:  # the fallback failed too
        return False
    return None


class Console:
    def __init__(self, files, host, elfldr_port=ELFLDR_PORT, padd=None):
        self.files = files
        self.host = host
        self.elfldr_port = elfldr_port
        self.padd = padd or Padd(host)

    def has_padd(self):
        return self.port_open(PADD_PORT)

    def start_padd(self, elf, timeout=15.0):
        """Upload padd.elf and start it. The console then asks who uses the new controller: see assign."""
        if self.has_padd():
            return False
        if not self.port_open(self.elfldr_port):
            raise LaunchError(f"elfldr is not running on port {self.elfldr_port}; load it on the PS5 first")
        folder, _, name = PADD_ELF.rpartition("/")
        parent, _, leaf = folder.rpartition("/")
        self.files.mkdir(parent, leaf)
        self.files.upload(elf, folder, name)
        self.files.launch_elf(PADD_ELF)
        deadline = time.monotonic() + timeout
        while not self.has_padd():
            if time.monotonic() > deadline:
                raise LaunchError(f"padd did not start listening on port {PADD_PORT}")
            time.sleep(0.5)
        return True

    def close(self, title=None, timeout=20.0):
        """Close the running game through padd and wait until its sandbox is gone."""
        try:
            self.padd.close_app()
        except PaddError as error:
            raise LaunchError(str(error)) from None
        if title:
            deadline = time.monotonic() + timeout
            while self.is_running(title):
                if time.monotonic() > deadline:
                    raise LaunchError(f"{title} still runs {timeout:.0f} s after it was closed")
                time.sleep(1.0)

    def port_open(self, port, timeout=1.5):
        try:
            with socket.create_connection((self.host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def running_titles(self):
        """Title IDs that have a sandbox now, e.g. {'FAKE77031', 'NPXS40000'}."""
        titles = set()
        for entry in self.files.list(SANDBOX):
            title, _, _ = entry["name"].partition("_")
            if TITLE_ID.match(title):
                titles.add(title)
        return titles

    def is_running(self, title):
        return title in self.running_titles()

    def title_log(self, title):
        """The text of title-<title>.log, or '' when the title has none yet."""
        try:
            return self.files.download(f"{LOGS}/title-{title}.log").decode("utf-8", "replace")
        except FileManagerError:
            return ""

    def launch(self, title, timeout=20.0, grace=15.0):
        """Start a title. Raises LaunchError with the reason when it does not start.

        A failed return code does not settle it: with Playden in front, both launch calls
        answer 0x80940010 and the game starts anyway (Playden's own tests expect the same).
        So a failure only counts once the title's sandbox has not appeared within `grace`.

        Always through the relaunch helper, even with padd running: padd's launch (sceLncUtilLaunchApp
        without SkipLaunchCheck) answered 0x80940010/0x80940033 for Playden's game titles, with
        "Can't start the game or app" (CE-105773-3) on screen.
        """
        if not TITLE_ID.match(title):
            raise LaunchError(f"not a title ID: {title!r}")
        if not self.port_open(self.elfldr_port):
            raise LaunchError(f"elfldr is not running on port {self.elfldr_port}; load it on the PS5 first")
        self.files.write_text(REQUEST, title + "\n")
        self.files.write_text(RESULT, "")  # the helper rewrites it; an empty one means no answer yet
        try:
            self.files.launch_elf(RELAUNCH_ELF)
        except FileManagerError as error:
            raise LaunchError(f"could not send the launch helper: {error}") from None
        deadline = time.monotonic() + timeout
        text, outcome = "", None
        while outcome is None and time.monotonic() < deadline:
            time.sleep(1.0)
            text = self._result_text()
            if f"title={title}" in text:
                outcome = launch_outcome(text)
            if self.is_running(title):
                return
        if outcome is True:
            return
        if outcome is None:
            raise LaunchError(f"no answer from the launch helper after {timeout:.0f} s: {text.strip()}")
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if self.is_running(title):
                return
            time.sleep(1.0)
        raise LaunchError(f"launch failed: {text.strip()}")

    def _result_text(self):
        try:
            return self.files.read_text(RESULT)[0]
        except FileManagerError:
            return ""
