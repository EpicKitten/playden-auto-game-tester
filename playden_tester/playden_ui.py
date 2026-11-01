"""Drive Playden's own screens with padd (virtual DualSense) and check every step on the capture card (screen.py).

Playden has no remote API for downloads or uninstalls, and doing them behind its back would leave its records
wrong, so the tester uses its UI the way a player would. Every step reads the screen before pressing anything that
changes something: a wrong focus backs out instead of pressing on.
"""
import difflib
import time

from .screen import Screen, normalize

# The PS5 system keyboard Playden's search opens (ABC page). The focus starts on G.
KEYBOARD = ["1234567890@", "QWERTYUIOP#", 'ASDFGHJKL"/', "ZXCVBNM-_?!"]
KEYBOARD_START = (2, 4)
RIGHT_PANEL = (960, 0, 1920, 1080)
TABS = ["home", "library", "queue", "saves", "settings"]


class UIError(Exception):
    pass


def similar(a, b):
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def same_name(a, b):
    """The same game name, allowing only OCR slips (a letter read wrong, one dropped or added in the middle).
    A name that is the start of the other is a different game: "Half-Life" is not "Half-Life 2"."""
    x, y = normalize(a), normalize(b)
    if x == y:
        return True
    if not x or not y or x.startswith(y) or y.startswith(x):
        return False
    return abs(len(x) - len(y)) <= 1 and difflib.SequenceMatcher(None, x, y).ratio() >= 0.9


def dialog_names(lines, name):
    """Does the uninstall dialog ("<name>. Frees about 67 MB. ...") name this game and no longer one?"""
    text = normalize(" ".join(l.text for l in lines))
    return normalize(name) + "frees" in text


# Letters, digits and space only: the key shown as "-" typed a comma ("Half,life 2"), and the typed-text check
# cannot tell punctuation apart, so the search stops before the first other character and the result
# prediction finds the game among the matches.
TYPEABLE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")


def search_text(name, limit=28):
    """What to type for a game. Playden keeps a game when the search is part of its title as written (case
    folded), so this is the start of the title, up to the first character the ABC page has no key for."""
    text = ""
    for c in name.upper():
        if c not in TYPEABLE or len(text) >= limit:
            break
        text += c
    return text.rstrip()


def predict_results(library, typed):
    """The games Playden's Library (scope All) shows for a search, in its order: case-folded title contains the
    text, sorted by case-folded title, then by app ID (Playden src/homebrew/browse.cpp filtered_games)."""
    query = typed.casefold()
    found = [g for g in library if query in g.title.casefold()]
    return sorted(found, key=lambda g: (g.title.casefold(), g.app))


def key_moves(text, start=KEYBOARD_START):
    """D-pad presses (and triangle for space) that type text on the ABC page, from start."""
    where = {c: (r, k) for r, row in enumerate(KEYBOARD) for k, c in enumerate(row)}
    moves, (row, col) = [], start
    for c in text.upper():
        if c == " ":
            moves.append("triangle")
            continue
        if c not in where:
            raise UIError(f"cannot type {c!r}")
        r, k = where[c]
        moves += ["down" if r > row else "up"] * abs(r - row) + ["right" if k > col else "left"] * abs(k - col)
        moves.append("cross")
        row, col = r, k
    return moves


class PlaydenUI:
    def __init__(self, padd, screen, say=print):
        self.pad = padd
        self.screen = screen
        self.say = say

    def press(self, *names, times=1, gap=0.35):
        for _ in range(times):
            self.pad.press(*names)
            time.sleep(gap)

    def read(self, settle=0.8, region=None):
        return self.screen.read(settle, region)

    def expect(self, *texts, settle=0.8, tries=3):
        """The screen lines once all texts are on screen; UIError when they never are."""
        lines = []
        for _ in range(tries):
            lines, _, _ = self.read(settle)
            if Screen.has(lines, *texts):
                return lines
        raise UIError(f"expected {texts} on screen; saw {[l.text for l in lines][:12]}")

    def active_tab(self):
        """The selected tab's name (home, library, queue, saves, settings): the one inside the grey outline."""
        from PIL import Image
        from .screen import ocr
        path = self.screen.grab(0.8)
        pixels = Image.open(path).convert("RGB").load()
        edge = [x for x in range(80, 1100) if all(70 <= c <= 110 for c in pixels[x, 57])]
        if not edge:
            return None
        x0, x1 = min(edge), max(edge)
        for line in ocr(path):
            if line.y < 120 and x0 <= line.center[0] <= x1:
                for name in TABS:
                    if name in normalize(line.text) or (name == "queue" and "ueue" in normalize(line.text)):
                        return name
        return None

    def tab(self, name):
        """Select a tab by name. R1 goes right and wraps from Settings to Home."""
        if isinstance(name, int):
            name = TABS[name]
        for _ in range(len(TABS) + 1):
            if self.active_tab() == name:
                return
            self.press("r1", gap=0.6)
        raise UIError(f"could not select the {name} tab")

    def type_search(self, text):
        """Type into the open system keyboard and check the field before Done (R2)."""
        for move in key_moves(text):
            self.pad.press(move)
            time.sleep(0.12)
        lines, _, _ = self.read(0.6)
        # The field line only (the suggestions row below it repeats the word); the caret can read as an extra "l".
        typed = " ".join(l.text for l in lines if 315 < l.y < 375 and 530 < l.x < 1400)
        if similar(typed, text) < 0.8:
            raise UIError(f"typed {typed!r} instead of {text!r}")
        self.pad.press("r2")

    # --- Library: find a game and open its page ---------------------------------------------------------------

    def home_visible(self, lines):
        return Screen.has(lines, "Library", "Saves", "Settings")  # "Queue" often reads as "Oueue"

    @staticmethod
    def overlay_open(lines):
        """A sheet (Installed games), a dialog, the system keyboard or a game's page over the tabs."""
        markers = [("Select games to uninstall",), ("Uninstall 1 game",), ("Search", "Done", "Backspace"),
                   ("Delete saves too",), ("PLAYTIME", "LOCATION")]
        return any(Screen.has(lines, *marker) for marker in markers)

    def side_focus(self):
        lines, box, _ = self.read(0.7, (80, 130, 420, 600))
        return [l.text for l in Screen.inside(lines, box)]

    def library_all(self):
        """Library tab, scope All, no search."""
        self.tab(1)
        lines = self.expect("Library", "All", settle=1.0)
        if Screen.has(lines, "Clear search"):
            self.press("circle")
        # One Left per column from the focused tile, then one more into the side menu (6 columns).
        for _ in range(8):
            if self.side_focus():
                break
            self.press("left", gap=0.6)
        else:
            raise UIError("could not reach the Library side menu")
        for _ in range(8):
            focused = self.side_focus()
            if focused and normalize(focused[0]) == "all":
                self.press("cross", gap=0.8)
                return
            self.press("up" if focused and normalize(focused[0]) in ("favorites", "hidden", "newcollection") else "down")
        raise UIError("could not select All in the Library")

    def details_match(self, lines, game):
        """Is this details page the game? Its description against the library cache's, or the title text."""
        text = " ".join(l.text for l in lines if l.y > 840 and l.x < 1250)
        if game.description and text and similar(text[:160], game.description[:160]) > 0.6:
            return True
        title = " ".join(l.text for l in lines if 380 < l.y < 640)
        return same_name(title, game.title)

    def focused_tile(self):
        """(row, column) of the focused Library tile on screen, from the orange outline, or None. Tiles start at
        x 445 and y 150, 234 px apart across and 339 px down."""
        _, box, _ = self.read(0.6, (420, 120, 1900, 1000))
        if not box:
            return None
        return round((box[1] - 130) / 339), round((box[0] - 430) / 234)

    def goto_tile(self, index, tries=8):
        """Move the focus to result `index` (6 to a row) and check it there before anything opens it. Presses
        sent while the results were still drawing were dropped on the console, so each move is checked."""
        time.sleep(1.0)
        row, col = index // 6, index % 6
        self.press("down", times=row, gap=0.6)
        for _ in range(tries):
            here = self.focused_tile()
            if here is None:
                raise UIError("no focused tile in the Library grid")
            # Rows past the second scroll the grid, so only the first two can be checked on screen.
            row_ok = row > 1 or here[0] == row
            if here[1] == col and row_ok:
                return
            if not row_ok:
                self.press("down" if here[0] < row else "up", gap=0.6)
            else:
                self.press("right" if here[1] < col else "left", gap=0.6)
        raise UIError(f"could not move to result {index + 1}")

    def result_count(self, lines):
        """The "N games" count under the Library's side menu, or None when it cannot be read."""
        for line in lines:
            words = line.text.split()
            if line.x < 420 and len(words) >= 2 and words[1].startswith("game"):
                number = words[0].replace("O", "0").replace("o", "0")  # "0 games" reads as "O games"
                if number.isdigit():
                    return int(number)
        return None

    def open_game(self, game, library=None, max_results=24):
        """From anywhere in Playden to the game's details page (Install or Play button focused).

        With the library (OwnedGame list), the results are predicted: when Playden's count matches, the game's
        tile is the predicted one. Otherwise each result's page is checked against the game."""
        typed = search_text(game.title)
        if len(typed) < 2:
            raise UIError(f"{game.title}: no typeable start to search for")
        self.library_all()
        self.press("right", gap=0.6)  # back into the grid, so touchpad opens search
        self.press("touchpad", gap=1.0)
        self.expect("Search", "Done", settle=0.8)
        self.type_search(typed)
        lines = self.expect("game", settle=1.5)
        count = self.result_count(lines)
        if count is None:
            raise UIError(f"{game.title}: could not read how many games the search for {typed!r} found")
        if count == 0:
            raise UIError(f"{game.title}: the search for {typed!r} found nothing")
        # Playden's Library can be sorted another way than by name (it is here), so the predicted place is only
        # where to look first; every result is opened and its page compared with the game before it counts.
        predicted = [g.app for g in predict_results(library, typed)] if library else []
        order = list(range(min(count, max_results)))
        if len(predicted) == count and game.app in predicted and predicted.index(game.app) in order:
            first = predicted.index(game.app)
            order.remove(first)
            order.insert(0, first)
        whole_name = count == 1 and normalize(typed) == normalize(game.title)
        for index in order:
            self.goto_tile(index)
            self.press("cross", gap=1.8)
            lines, _, _ = self.read(0.5)
            # One result for the game's whole name is the game, even when its page shows a logo and no text.
            if self.details_match(lines, game) or whole_name:
                return lines
            self.press("circle", gap=1.2)
        raise UIError(f"{game.title}: none of the {min(count, max_results)} search results is this game")

    # --- Install and uninstall ----------------------------------------------------------------------------------

    def install(self, game, files, timeout=120):
        """Press Install on the game's details page; True once Playden has started on it (its download folder)."""
        lines, box, _ = self.read(0.6, (60, 620, 1240, 740))
        focused = " ".join(l.text for l in Screen.inside(lines, box))
        if "install" not in focused.lower():
            if "play" in focused.lower():
                return False  # already installed
            raise UIError(f"{game.title}: the focused button is {focused!r}, not Install")
        self.press("cross", gap=1.5)
        lines, _, _ = self.read(0.5)
        if Screen.has(lines, "Cancel") and not Screen.has(lines, "Delete saves"):
            raise UIError(f"{game.title}: Install opened a dialog: {[l.text for l in lines][:10]}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(e["name"] == str(game.app) for e in files.list("/data/playden-games")):
                return True
            time.sleep(3)
        raise UIError(f"{game.title}: no download folder {game.app} within {timeout} s of Install")

    def uninstall(self, name, files, app, title=None, timeout=180):
        """Settings > Storage > Installed games: tick the game by name and uninstall it, keeping its saves.
        Checks the dialog names the game and the button is Uninstall, then that its files are gone."""
        self.tab(4)
        self.expect("Storage", "Downloads", "Updates", settle=1.0)
        for _ in range(3):
            if self.side_focus():
                break
            self.press("left", gap=0.6)
        for _ in range(9):
            focused = self.side_focus()
            if focused and normalize(focused[0]) == "storage":
                break
            order = ["account", "library", "storage", "downloads", "display", "updates", "about", "quitplayden"]
            here = order.index(normalize(focused[0])) if focused and normalize(focused[0]) in order else 9
            if normalize(focused[0] if focused else "") == "quitplayden" or here > 2:
                self.press("up")
            else:
                self.press("down")
        else:
            raise UIError("could not reach Storage")
        self.press("right", gap=0.6)
        for _ in range(6):
            lines, box, _ = self.read(0.6, (430, 190, 1840, 960))
            if any("installedgames" in normalize(l.text) for l in Screen.inside(lines, box)):
                break
            self.press("down")
        else:
            raise UIError("could not focus Installed games")
        self.press("cross", gap=1.5)
        self.expect("Select games to uninstall", settle=0.5)
        row = None
        for _ in range(60):
            lines, box, _ = self.read(0.5, RIGHT_PANEL)
            focused = Screen.inside(lines, box)
            if focused and same_name(focused[0].text, name):
                row = focused[0].text
                break
            if focused and normalize(focused[0].text).startswith("uninstallselected"):
                break
            self.press("down", gap=0.2)
        if not row:
            self.press("circle")
            raise UIError(f"{name} is not in Installed games")
        self.press("cross", gap=0.8)
        self.expect("selected", settle=0.3)  # "1 selected" reads as "I selected"
        self.press("triangle", gap=1.2)
        lines = self.expect("Uninstall 1 game", settle=0.3)
        if not dialog_names(lines, name):
            self.press("circle")
            raise UIError(f"the uninstall dialog does not name {name}: "
                          f"{' '.join(l.text for l in lines if 380 < l.y < 500)[:120]!r}")
        self.press("right", times=2, gap=0.4)
        lines, box, _ = self.read(0.6, (480, 600, 1440, 740))
        if [normalize(l.text) for l in Screen.inside(lines, box)] != ["uninstall"]:
            self.press("circle")
            raise UIError("the focus is not on the dialog's Uninstall button")
        self.press("cross")
        # Playden removes the PS5 title first, then deletes the files: an 18.8 GB game took over 3 minutes. The
        # title gone means the uninstall is under way; files still there after that are left to finish.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(3)
            games = {e["name"] for e in files.list("/data/playden-games")}
            titles = {e["name"] for e in files.list("/data/homebrew")}
            title_gone = not title or title not in titles
            if title_gone and (str(app) not in games or not title):
                self.press("circle")  # close the list
                return "done"
            if title_gone and time.monotonic() > deadline - timeout / 2:
                self.press("circle")
                return "files still being deleted"
        raise UIError(f"{name}: still on the console {timeout} s after Uninstall")
