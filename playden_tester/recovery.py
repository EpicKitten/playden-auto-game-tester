"""Getting the console back to a working state with nobody at it: restarting services, answering the controller
dialog, clearing error dialogs and closing a stuck game, so one bad game doesn't end a campaign.
"""
import re
import time
from pathlib import Path

from .capture import CaptureError
from .console import ELFLDR_PORT, LaunchError
from .filemanager import FileManagerError
from .padd import PORT as PADD_PORT
from .padd import PaddError
from .payloadmgr import PayloadManagerError, disk_free, send_elf
from .screen import Screen, ScreenError, normalize

FILE_MANAGER = ("web-file-manager", "webfilemanager", "file_manager", "file-manager")
PAD_DIALOG = "using this controller"
# What the PS5's own error dialogs say, with letters and digits only. Their one button is OK, so Cross clears them.
ERROR_WORDS = ("cantstart", "errorhasoccurred", "somethingwentwrong")
ERROR_CODE = re.compile(r"(?:ce|np|ws|su)\d{6}")  # "CE-105773-3"
# A dialog that can remove something is left with Circle, whatever else it says.
DANGER_WORDS = ("uninstall", "delete", "cleanup")


def assign_pad(padd, screen, timeout=20.0, clock=time.monotonic, sleep=time.sleep):
    """Answer "Who's using this controller?" with Cross, once the screen really shows it. True once it's gone."""
    deadline = clock() + timeout
    while clock() < deadline:
        lines = screen.read(0.5)[0]
        if Screen.has(lines, PAD_DIALOG):
            padd.press("cross")
            sleep(2.0)
            return not Screen.has(screen.read(0.5)[0], PAD_DIALOG)
        sleep(1.0)
    return False


def dialog_action(lines):
    """Which button clears what's on screen: circle for anything that could remove something, cross for a PS5 error
    dialog, None when it's neither."""
    text = "".join(normalize(line.text) for line in lines)
    if any(word in text for word in DANGER_WORDS):
        return "circle"
    return "cross" if any(word in text for word in ERROR_WORDS) or ERROR_CODE.search(text) else None


class Healer:
    def __init__(self, console, ui, payloads, say=print, folder=None, capture=None, df_elf=None, padd_elf=None,
                 sleep=time.sleep):
        self.console, self.ui, self.payloads, self.say = console, ui, payloads, say
        self.folder, self.capture, self.sleep = Path(folder) if folder else None, capture, sleep
        self.df_elf, self.padd_elf = Path(df_elf) if df_elf else None, Path(padd_elf) if padd_elf else None

    def free_gb(self):
        """GB really available for games, or None when the payload can't say."""
        if not self.df_elf or not self.df_elf.is_file():
            return None
        try:
            return disk_free(self.console.host, self.df_elf.read_bytes(), ELFLDR_PORT)["/data"]["available_gb"]
        except (OSError, ValueError, KeyError):
            return None

    def services(self):
        """Start the file manager and padd if they stopped. True when both answer."""
        if not self.console.port_open(8888):
            try:
                found = self.payloads.find(*FILE_MANAGER)
                if found:
                    self.say(f"The file manager stopped; starting {found.rsplit('/', 1)[-1]}")
                    self.payloads.load(found)
                    self.sleep(5.0)
            except PayloadManagerError as error:
                self.say(f"Could not restart the file manager: {error}")
        if not self.console.has_padd() and self.padd_elf and self.padd_elf.is_file():
            self.say("padd stopped; starting it")
            try:
                send_elf(self.console.host, self.padd_elf.read_bytes(), ELFLDR_PORT)
            except OSError as error:
                self.say(f"Could not restart padd: {error}")
            self.sleep(4.0)
            if self.console.has_padd():
                assign_pad(self.console.padd, self.ui.screen)
        return self.console.port_open(8888) and self.console.port_open(PADD_PORT)

    def clear_dialogs(self):
        """Press through up to three dialogs. What each one said goes in the log."""
        for _ in range(3):
            lines = self.ui.read(0.5)[0]
            button = dialog_action(lines)
            if not button:
                return
            self.say(f"Dialog on screen, pressing {button}: {' '.join(l.text for l in lines)[:120]}")
            self.ui.press(button, gap=2.0)

    def close_games(self):
        for title in sorted(t for t in self.console.running_titles() if t.startswith("FAKE78")):
            self.say(f"Closing {title}, left running")
            self.console.close(title)

    def picture(self, reason):
        """What the screen showed when things went wrong, for working out why later."""
        if not self.folder or not self.capture:
            return
        name = time.strftime("%Y%m%d-%H%M%S") + ".jpg"
        try:
            self.capture.snapshot(self.folder / name)
            self.say(f"Saved the screen as {self.folder / name}: {reason}")
        except CaptureError:
            pass

    def heal(self, reason):
        """Try to bring everything back after something went wrong; True when the campaign can go on."""
        self.say(f"Trying to recover: {reason}")
        self.picture(reason)
        try:
            if not self.services():
                self.say("Could not recover: the file manager or padd is down")
                return False
            self.clear_dialogs()
            self.close_games()
            self.clear_dialogs()
            return True
        except (LaunchError, FileManagerError, PaddError, CaptureError, ScreenError, OSError) as error:
            self.say(f"Could not recover: {error}")
            return False
