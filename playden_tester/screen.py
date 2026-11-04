"""Read what is on the PS5's screen: text (Windows' built-in OCR) and the orange box around the focused item in
Playden's UI. Needs a capture card (capture.py) and Pillow; the OCR needs Windows 10 or 11.
"""
import json
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

OCR_SCRIPT = Path(__file__).with_name("ocr.ps1")


class ScreenError(Exception):
    pass


@dataclass
class Line:
    text: str
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2


def normalize(text):
    """Lower case letters and digits only, so OCR slips in punctuation and spacing do not matter."""
    return "".join(c for c in text.lower() if c.isalnum())


def ocr(image_path):
    done = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OCR_SCRIPT),
                           str(image_path)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=60)
    if done.returncode:
        raise ScreenError(f"OCR failed: {done.stderr.strip()[-300:]}")
    return [Line(**json.loads(row, strict=False)) for row in done.stdout.splitlines() if row.startswith("{")]


def focus_box(image_path, region=None, step=2):
    """The bounding box (x0, y0, x1, y1) of Playden's orange focus outline inside region, or None.

    The outline is a ring (or a filled button): its edge columns and rows hold the most orange pixels, while
    orange cover art is scattered, so only columns and rows with at least 70% of the busiest one's count count."""
    from PIL import Image
    image = Image.open(image_path).convert("RGB")
    x0, y0, x1, y1 = region or (0, 0, image.width, image.height)
    pixels = image.load()
    cols, orange = {}, set()
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            r, g, b = pixels[x, y]
            if r > 200 and 90 < g < 170 and b < 90 and r - g > 70:  # Playden's focus orange, about (235, 130, 50)
                cols[x] = cols.get(x, 0) + 1
                orange.add((x, y))
    if len(orange) < 40:
        return None
    top_col = max(cols.values())
    xs = [x for x, n in cols.items() if n >= 0.7 * top_col]
    left, right = min(xs), max(xs)

    # The outline's top and bottom run almost the whole width (all but the rounded corners); a progress bar
    # (77% on Settings > Storage) or a line of orange art does not.
    ys = [y for y in range(y0, y1, step)
          if sum((x, y) in orange for x in range(left, right + 1, step)) >= 0.85 * (right - left) / step]
    if not ys:
        return None
    return left, min(ys), right, max(ys)


def read_fps(image_path):
    """The frame rate on the performance overlay at the top left of a game ("Fps: 30.00"), or None without one."""
    from PIL import Image
    image = Image.open(image_path)
    corner = image.crop((0, 0, 420, 140)).resize((1260, 420), Image.LANCZOS)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "corner.png"
        corner.save(path)
        text = " ".join(line.text for line in ocr(path))
    found = re.search(r"fps\W{0,3}(\d{1,3}(?:[.,]\d+)?)", text, re.I)
    return float(found.group(1).replace(",", ".")) if found else None


class Screen:
    def __init__(self, capture):
        self.capture = capture
        self.folder = Path(tempfile.mkdtemp(prefix="playden-screen-"))
        self.count = 0

    def grab(self, settle=0.8):
        """A fresh screenshot path after letting the UI settle."""
        time.sleep(settle)
        self.count += 1
        return self.capture.snapshot(self.folder / f"screen-{self.count:04d}.png")

    def read(self, settle=0.8, region=None):
        """(lines, focus box, image path) of the screen now."""
        path = self.grab(settle)
        return ocr(path), focus_box(path, region), path

    @staticmethod
    def inside(lines, box, margin=6):
        if not box:
            return []
        x0, y0, x1, y1 = box
        return [l for l in lines if x0 - margin <= l.center[0] <= x1 + margin and y0 - margin <= l.center[1] <= y1 + margin]

    @staticmethod
    def has(lines, *texts):
        """True when every text appears (normalized) somewhere on screen."""
        seen = [normalize(l.text) for l in lines]
        return all(any(normalize(t) in s for s in seen) for t in texts)
