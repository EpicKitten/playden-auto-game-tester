"""See the PS5's screen through an HDMI capture card, with ffmpeg (DirectShow on Windows, v4l2 on Linux).

The PS5 must have HDCP off (Settings > System > HDMI > Enable HDCP), or the card gets a blank picture.
Only one program can use the card at a time: close the Camera app, OBS and the like first.
"""
import re
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROBE_W, PROBE_H = 64, 36  # small grey frames are enough to tell black, frozen and moving apart
BLACK_BELOW = 10.0         # mean brightness (0-255) of a black screen; a dark game scene is higher
STILL_BELOW = 0.6          # mean change per pixel between frames when nothing moves


class CaptureError(Exception):
    pass


def find_ffmpeg():
    found = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not found:
        raise CaptureError("ffmpeg not found: install it (winget install Gyan.FFmpeg) or set FFMPEG")
    return found


@dataclass
class ScreenCheck:
    brightness: float
    motion: float
    frames: int

    @property
    def verdict(self):
        if self.brightness < BLACK_BELOW:
            return "black"
        if self.motion < STILL_BELOW:
            return "still"
        return "moving"

    def as_dict(self):
        return {"verdict": self.verdict, "brightness": round(self.brightness, 1), "motion": round(self.motion, 2),
                "frames": self.frames}


def check_frames(frames):
    """Brightness and motion of equal-sized grey frames (bytes, one byte per pixel)."""
    if not frames:
        raise CaptureError("no frames")
    pixels = len(frames[0])
    brightness = sum(sum(f) for f in frames) / (pixels * len(frames))
    changes = [sum(abs(a - b) for a, b in zip(x, y)) / pixels for x, y in zip(frames, frames[1:])]
    return ScreenCheck(brightness, sum(changes) / len(changes) if changes else 0.0, len(frames))


class Capture:
    def __init__(self, device, ffmpeg=None):
        self.device = device
        self.ffmpeg = ffmpeg or find_ffmpeg()

    def _input(self):
        if sys.platform == "win32":
            return ["-f", "dshow", "-rtbufsize", "256M", "-i", f"video={self.device}"]
        return ["-f", "v4l2", "-i", self.device]

    def _run(self, args, timeout):
        try:
            done = subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *self._input(), *args],
                                  capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise CaptureError(f"ffmpeg took longer than {timeout:.0f} s") from None
        if done.returncode:
            text = done.stderr.decode(errors="replace").strip().splitlines()
            reason = text[-1] if text else f"ffmpeg exit {done.returncode}"
            if "I/O error" in reason:
                reason += " (is another program, such as the Camera app or OBS, using the card?)"
            raise CaptureError(f"capture from {self.device!r} failed: {reason}")
        return done.stdout

    def snapshot(self, path):
        """Save one full-size frame (PNG or JPEG, by extension)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-frames:v", "1", "-update", "1", str(path)], timeout=20)
        return path

    def check(self, seconds=3.0, fps=4):
        """Watch the screen for a few seconds: is it black, still, or moving?"""
        count = max(2, round(seconds * fps))
        raw = self._run(["-vf", f"fps={fps},scale={PROBE_W}:{PROBE_H},format=gray", "-frames:v", str(count),
                         "-f", "rawvideo", "-"], timeout=seconds + 20)
        size = PROBE_W * PROBE_H
        frames = [raw[i:i + size] for i in range(0, len(raw) - size + 1, size)]
        return check_frames(frames)


    def frame(self):
        """One small grey frame, to compare with another."""
        return self._run(["-vf", f"scale={PROBE_W}:{PROBE_H},format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
                         timeout=20)

    def clip(self, path, seconds):
        """Record a small video of the screen; this takes as long as the clip."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-t", str(seconds), "-vf", "scale=960:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                   str(path)], timeout=seconds + 30)
        return path

    def audio_level(self, seconds=3.0):
        """Mean loudness of the card's sound in dB (about -91 is silence), or None when it can't say."""
        if sys.platform != "win32":
            return None
        device = f"audio=HDMI ({self.device})"
        try:
            done = subprocess.run([self.ffmpeg, "-hide_banner", "-f", "dshow", "-i", device, "-t", str(seconds),
                                   "-af", "volumedetect", "-f", "null", "-"], capture_output=True,
                                  timeout=seconds + 20)
        except subprocess.TimeoutExpired:
            return None
        found = re.search(r"mean_volume: (-?[\d.]+) dB", done.stderr.decode(errors="replace"))
        return float(found.group(1)) if found else None


def list_devices(ffmpeg=None):
    """Video capture device names (Windows DirectShow)."""
    if sys.platform != "win32":
        return sorted(str(p) for p in Path("/dev").glob("video*"))
    done = subprocess.run([ffmpeg or find_ffmpeg(), "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                          capture_output=True, timeout=20)
    names = []
    for line in done.stderr.decode(errors="replace").splitlines():
        if line.rstrip().endswith("(video)") and '"' in line:
            names.append(line.split('"')[1])
    return names
