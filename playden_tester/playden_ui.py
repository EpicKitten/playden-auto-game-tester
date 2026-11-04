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


class DownloadFailed(UIError):
    """Playden's download of the game failed ("No Windows content to install", "Steam didn't grant access")."""


class NotInLibrary(UIError):
    """Playden's Library search does not find the game (no longer shared with the family, say)."""


def similar(a, b):
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def playden_tile(image_path):
    """True when the focused tile on the PS5's Home (the big one at the left of the row) is Playden's: its icon is
    an orange play mark on black, about 9% orange and 77% near-black pixels. Game art with orange in it
    (Guacamelee!'s gold logo) is far less dark: under 10% on the tiles seen."""
    from PIL import Image
    pixels = list(Image.open(image_path).convert("RGB").crop((170, 120, 345, 300)).getdata())
    orange = sum(1 for r, g, b in pixels if r > 200 and 90 < g < 170 and b < 80) / len(pixels)
    dark = sum(1 for p in pixels if max(p) < 40) / len(pixels)
    return orange > 0.05 and dark > 0.5


def queued(button):
    """True when a game page's focused button says its download is queued or running ("Download Queued")."""
    text = normalize(button)
    return "queued" in text or text.startswith("downloading")


def same_name(a, b):
    """The same game name, allowing only OCR slips (a letter read wrong, one dropped or added in the middle).
    A name that is the start of the other is a different game: "Half-Life" is not "Half-Life 2"."""
    # OCR reads Playden's Q as O ("Oueue", "Ouiplash"), and ™, ® and © as letters ("BatmanTM", "LEGOO").
    x = normalize(a).replace("q", "o")
    if any(x == normalize(v).replace("q", "o") for v in symbol_readings(b)) or             any(normalize(v).replace("q", "o") == normalize(b).replace("q", "o") for v in symbol_readings(a)):
        return True
    y = normalize(b).replace("q", "o")
    if not x or not y or x.startswith(y) or y.startswith(x):
        return False
    if [c for c in x if c.isdigit()] != [c for c in y if c.isdigit()]:
        return False  # "Sniper Elite 3" is not "Sniper Elite 4", however close the letters
    return abs(len(x) - len(y)) <= 1 and difflib.SequenceMatcher(None, x, y).ratio() >= 0.9


def symbol_readings(name):
    """The name with each ™, ® and © as OCR may read it: dropped, or as a letter or two."""
    names = {name}
    for symbol in "®™©":
        names = {n.replace(symbol, reading) for n in names for reading in ("", "o", "r", "c", "tm")}
    return names


def dialog_names(lines, name):
    """Does the uninstall dialog ("<name>. Frees about 67 MB. ...") name this game and no longer one? OCR slips
    are allowed: "LEGO® Builder's Journey" reads as "LEGOO Builder's Journey"."""
    text = normalize(" ".join(l.text for l in lines))
    # Exact, apart from the symbols OCR reads as a letter or drops: anything looser would let "Escape Simulator"
    # match "Escape Simulator 2" and uninstall the wrong game.
    return any(normalize(n) + "frees" in text for n in symbol_readings(name))


# Letters, digits and space only: the key shown as "-" typed a comma ("Half,life 2"), and the typed-text check
# cannot tell punctuation apart, so the search stops before the first other character and the result
# prediction finds the game among the matches.
TYPEABLE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")


NOT_DESCRIPTION = ("installs to", "saves from", "read more", "select", "cloud saves")


def description_text(lines):
    """The description on a game's page: the text under the buttons, left of the facts column. It sits lower
    on a page that offers Install (y 860) than on one that offers Play (y 775)."""
    return " ".join(l.text for l in lines if 740 < l.y < 970 and l.x < 1250
                    and not l.text.lower().startswith(NOT_DESCRIPTION) and "read more" not in l.text.lower())


def search_text(name, limit=28):
    """What to type for a game. Playden keeps a game when the search is part of its title as written (case
    folded), so this is the start of the title, up to the first character the ABC page has no key for. A title
    that starts with characters the page has none for ("东方夜雀食堂 - Touhou Mystia's Izakaya") uses its first
    typeable run of at least 4 letters instead ("TOUHOU MYSTIA")."""
    runs, text = [], ""
    for c in name.upper() + "|":
        if c in TYPEABLE and len(text) < limit:
            text += c
            continue
        if text.strip():
            runs.append(text.strip())
        if c not in TYPEABLE:
            text = ""
        else:
            break
    if runs and name.upper().startswith(runs[0]):
        return runs[0]
    return next((run for run in runs if len(run.replace(" ", "")) >= 4), "")


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


SIDE_MENUS = [["Installed", "All", "Favorites", "Hidden", "New collection"],
              ["Account", "Library", "Storage", "Downloads", "Display", "Updates", "Web access", "About",
               "Quit Playden"]]
SIDE_STEP = 66  # px between side-menu items


def side_item(lines, y):
    """The side-menu item at height y, from the items OCR did read and the menus' fixed order and spacing."""
    for menu in SIDE_MENUS:
        for index, label in enumerate(menu):
            seen = [l for l in lines if l.x < 420 and same_name(l.text, label)]
            if seen:
                slot = index + round((y - seen[0].center[1]) / SIDE_STEP)
                if 0 <= slot < len(menu):
                    return menu[slot]
    return None


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
        # Grey outline; orange (Playden's focus colour) while the tab bar itself has the focus.
        edge = [x for x in range(80, 1100) if all(70 <= c <= 110 for c in pixels[x, 57])]
        if not edge:
            edge = [x for y in (50, 52, 54) for x in range(80, 1100)
                    if pixels[x, y][0] > 200 and 90 < pixels[x, y][1] < 170 and pixels[x, y][2] < 90]
        if not edge:
            return None
        x0, x1 = min(edge), max(edge)
        for line in ocr(path):
            if line.y >= 120 or line.x > x1 or line.x + line.w < x0:
                continue
            # OCR can read two tabs as one line ("Saves 20 Settings"): place each tab name along the line by where
            # it starts in the text and take the one inside the outline.
            text = line.text.lower()
            for name in TABS:
                at = text.find(name if name != "queue" else "ueue")
                if at >= 0 and x0 - 20 <= line.x + line.w * (at + len(name) / 2) / max(len(text), 1) <= x1 + 20:
                    return name
        return None

    def open_from_ps_home(self, steps=12):
        """On the PS5's Home: move along the row of tiles to Playden's (the focused tile's name shows below it)
        and open it. Playden 0.10 stays suspended after a game closes, and launching it again does not bring it
        back; its tile does. True once its tile was pressed."""
        # Playden's tile sits right of the PS5's own (Welcome, PlayStation Store and Plus) among the recent games.
        # OCR garbles its name ("Play e", ";aoes") and cuts the PlayStation ones short ("PlayStatio"), so its
        # orange icon counts too.
        for direction in ("right", "left"):
            for _ in range(steps if direction == "right" else steps * 2):
                lines, _, path = self.read(0.8)
                label = normalize(" ".join(l.text for l in lines if 220 < l.y < 320 and l.x < 1300))
                if (label.startswith("play") and not label.startswith("playst")) or playden_tile(path):
                    self.press("cross", gap=3.0)
                    for _ in range(10):  # it takes about 10 s to show its tabs
                        if self.home_visible(self.read(1.0)[0]):
                            break
                        time.sleep(2)
                    return True
                self.press(direction, gap=1.2)
        return False

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
        # Playden 0.10 keeps the last search in the field ("Lego" + "myst"): delete it with Square (backspace) first.
        # Not Triangle: Playden's hint says "Clear", but the system keyboard takes it as space.
        lines, _, _ = self.read(0.4)
        old = " ".join(l.text for l in lines if 315 < l.y < 375 and 530 < l.x < 1400).strip()
        for _ in range(len(old) + 3 if old else 0):
            self.pad.press("square")
            time.sleep(0.08)
        for move in key_moves(text):
            self.pad.press(move)
            time.sleep(0.12)
        lines, _, _ = self.read(0.6)
        # The field line only (the suggestions row below it repeats the word); the caret can read as an extra "l".
        typed = " ".join(l.text for l in lines if 315 < l.y < 375 and 530 < l.x < 1400)
        if similar(typed, text) < 0.8:
            self.pad.press("circle")  # close the keyboard, so the next game starts from the Library
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
        """The text of the focused side-menu item; [] when the focus is not in the side menu."""
        lines, box, _ = self.read(0.7, (80, 130, 420, 700))
        inside = [l.text for l in Screen.inside(lines, box)]
        if inside or not box:
            return inside
        # OCR does not read some highlighted items ("All"); tell them by their place among the ones it reads.
        guess = side_item(lines, (box[1] + box[3]) / 2)
        return [guess] if guess else []

    def library_all(self):
        """Library tab, scope All, no search."""
        self.tab(1)
        lines = self.expect("Library", "Installed", settle=1.0)  # OCR misses a highlighted "All"
        if Screen.has(lines, "Clear search"):
            self.press("circle")
        # One Left per column from the focused tile, then one more into the side menu (6 columns); presses made
        # while the grid redraws can be dropped, so allow twice that.
        for _ in range(12):
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
            # An item OCR does not read is one below All (Favorites, on 0.10): only Installed is above it, and that
            # one reads.
            self.press("down" if focused and normalize(focused[0]) == "installed" else "up")
        raise UIError("could not select All in the Library")

    def details_match(self, lines, game):
        """Is this details page the game? Its description against the library cache's, or the title text."""
        text = description_text(lines)
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
            raise NotInLibrary(f"{game.title}: the search for {typed!r} found nothing")
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

    def set_overlay(self, game):
        """On the game's page: Actions > Game settings > Performance overlay On, Overlay detail Everything (DXVK's
        HUD with frame rate, a frame-time graph, memory, GPU load and the DXVK version), so screenshots show how the
        game runs. Leaves the page as it was. Only games drawn through DXVK show it."""
        def focus():
            lines, box, _ = self.read(0.5, RIGHT_PANEL)
            return normalize(" ".join(l.text for l in Screen.inside(lines, box)))

        def pick(option):
            self.press("cross", gap=1.2)
            for _ in range(4):
                if focus().startswith(option):
                    self.press("cross", gap=1.2)
                    return
                self.press("down", gap=0.5)
            self.press("circle")
            raise UIError(f"{game.title}: no {option!r} among the choices")

        self.press("options", gap=1.5)
        for _ in range(5):
            if focus().startswith("gamesettings"):
                break
            self.press("down", gap=0.5)
        else:
            self.press("circle")
            raise UIError(f"{game.title}: no Game settings in its actions")
        self.press("cross", gap=2.0)
        try:
            for _ in range(30):
                here = focus()
                if here.startswith("performanceoverlay"):
                    break
                self.press("down", gap=0.4)
            else:
                raise UIError(f"{game.title}: no Performance overlay in its game settings")
            if not here.endswith("on"):
                pick("on")
            self.press("down", gap=0.6)
            here = focus()
            if not here.startswith("overlaydetail"):
                raise UIError(f"{game.title}: no Overlay detail below Performance overlay ({here[:40]!r})")
            if not here.endswith("everything"):
                pick("everything")
        finally:
            self.press("circle", gap=1.5)  # close the settings
            self.press("circle", gap=1.0)  # and the actions menu

    def install(self, game, files, timeout=120):
        """Press Install on the game's details page; True once Playden has started on it (its download folder)."""
        lines, box, _ = self.read(0.6, (60, 620, 1240, 740))
        focused = " ".join(l.text for l in Screen.inside(lines, box))
        if queued(focused):
            return True  # Playden 0.10 queues downloads behind the one running: "Download Queued"
        if "failed" in focused.lower():
            raise DownloadFailed(f"{game.title}: Playden's download failed ({focused!r}); its Queue row says why")
        if "paused" in focused.lower():
            # A download cut short ("Interrupted. Resume to continue."). Pressing it opens the Queue tab with its
            # row focused, where Actions > Resume download resumes it.
            self.press("cross", gap=2.0)
            lines, box, _ = self.read(0.6)
            row = " ".join(l.text for l in Screen.inside(lines, box))
            if not same_name(Screen.inside(lines, box)[0].text if Screen.inside(lines, box) else "", game.title):
                raise UIError(f"{game.title}: Download Paused did not open its Queue row ({row[:80]!r})")
            self.press("options", gap=1.5)
            for _ in range(4):
                lines, box, _ = self.read(0.5, RIGHT_PANEL)
                item = normalize(" ".join(l.text for l in Screen.inside(lines, box)))
                if item.startswith("resumedownload"):
                    self.press("cross", gap=3.0)
                    return True
                self.press("down", gap=0.6)
            self.press("circle")
            raise UIError(f"{game.title}: no Resume download in its Queue row's actions")
        if "install" not in focused.lower():
            if "play" in focused.lower():
                return False  # already installed
            raise UIError(f"{game.title}: the focused button is {focused!r}, not Install")
        self.press("cross", gap=1.5)
        lines, _, _ = self.read(0.5)
        if Screen.has(lines, "Install game"):
            # Playden 0.10: a sheet that says where the game goes, with Install ("Starts the download") focused.
            # Only console storage is confirmed; a game headed anywhere else is left alone.
            sheet, box, _ = self.read(0.3, (980, 230, 1900, 900))  # taller with a Language row
            focused = normalize(" ".join(l.text for l in Screen.inside(sheet, box)))
            if not any("toconsolestorage" in normalize(l.text) for l in lines) \
                    or "install" not in focused.replace("startsthedownload", "") or "startsthedownload" not in focused:
                self.press("circle")
                raise UIError(f"{game.title}: the install sheet is not Install to Console storage: "
                              f"{[l.text for l in lines][:12]}")
            self.press("cross", gap=1.5)
            lines, _, _ = self.read(0.5)
        if Screen.has(lines, "Cancel") and not Screen.has(lines, "Delete saves"):
            raise UIError(f"{game.title}: Install opened a dialog: {[l.text for l in lines][:10]}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(e["name"] == str(game.app) for e in files.list("/data/playden-games")):
                return True
            lines, box, _ = self.read(0.3, (60, 620, 1240, 740))
            if queued(" ".join(l.text for l in Screen.inside(lines, box))):
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
            order = ["account", "library", "storage", "downloads", "display", "updates", "webaccess", "about",
                     "quitplayden"]
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
        row, last, repeats = None, None, 0
        # Playden 0.10 shows the list full screen ("Uninstall games"), with the name at the left of the focused
        # row; 0.8 showed it in the right half.
        wide = Screen.has(self.read(0.2)[0], "Uninstall games")
        for _ in range(60):
            lines, box, _ = self.read(0.5, (60, 330, 1860, 960) if wide else RIGHT_PANEL)
            if wide and box and box[3] - box[1] < 40 and box[1] < 860:
                # The last row on screen touches the list's bottom edge, and only the outline's top is found.
                box = (box[0], box[1], box[2], box[1] + 90)
            focused = Screen.inside(lines, box)
            if wide:
                focused = sorted((l for l in focused if l.x < 1200), key=lambda l: l.y)
            if focused and same_name(focused[0].text, name):
                row = focused[0].text
                break
            if focused and normalize(focused[0].text).startswith("uninstallselected"):
                break
            here = focused[0].text if focused else None
            repeats = repeats + 1 if here == last else 0
            if repeats >= 2:
                break  # the end of the list
            last = here
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
