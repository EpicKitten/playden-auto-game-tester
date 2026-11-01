"""Collect Playden's logs for a game, redacted, as Playden's tools/collect_logs.py does, over the file manager.

The zip holds summary.md (the Versions table the test-report issue asks for) and logs/: every Playden log plus the
game's title-<ID>.log and its title-<ID>.* extras. It never reads /data/playden/user (session.v1 is the Steam
sign-in). Steam account names and SteamIDs are replaced in every file.
"""
import json
import re
import zipfile
from datetime import datetime, timezone

from .console import HOMEBREW, LOGS, PLAYDEN
from .filemanager import FileManagerError

KITS = "/data/playden/kits"
IDENTITY = f"{HOMEBREW}/{PLAYDEN}/playden-package.identity"
ACCOUNT = re.compile(r'L"Steam(?:App)?User" L"([^"]+)"')
STEAM_ID = re.compile(r"\b7656119\d{10}\b")
FIRMWARE = re.compile(r"console_firmware=(\S+)")
SKIP_SUFFIXES = (".ppm",)


def redact(text, names):
    text = STEAM_ID.sub("<steam-id>", text)
    for name in sorted(names, key=len, reverse=True):
        text = re.sub(re.escape(name), "<steam-user>", text, flags=re.IGNORECASE)
    return text


def account_names(texts):
    names = set()
    for text in texts:
        names.update(match.group(1) for match in ACCOUNT.finditer(text))
    return names


def summary_table(info):
    lines = ["| Field | Value |", "| --- | --- |"]
    lines += [f"| {key} | {value if value not in (None, '') else 'unknown'} |" for key, value in info.items()]
    return "\n".join(lines) + "\n"


class LogCollector:
    """Reads the console's logs once per collect() and writes one zip per game."""

    def __init__(self, files):
        self.files = files

    def _text(self, path):
        return self.files.download(path).decode("utf-8", "replace")

    def _kit(self):
        try:
            names = sorted((e["name"] for e in self.files.list(KITS) if e["type"] == "d" and not e["name"].startswith(".")),
                           key=lambda name: name != "playden-kit")
        except FileManagerError:
            return {"kit runtime": None}
        for name in names:
            try:
                manifest = json.loads(self._text(f"{KITS}/{name}/manifest.json"))
            except (FileManagerError, ValueError):
                continue
            return {"kit runtime": (manifest.get("runtime") or {}).get("artifact_revision"),
                    "kit capabilities": ", ".join(manifest.get("capabilities") or [])}
        return {"kit runtime": None}

    def collect(self, title, steam_app, out_path, extra=None):
        """Write the zip for one game; its Versions table (summary.md) as text."""
        entries = [e for e in self.files.list(LOGS) if e["type"] == "-" and not e["name"].endswith(SKIP_SUFFIXES)]
        texts = {}
        for entry in entries:
            name = entry["name"]
            if name.startswith("title-") and not name.startswith(f"title-{title}."):
                continue  # other games' logs stay out of this game's report
            try:
                texts[name] = self._text(f"{LOGS}/{name}")
            except FileManagerError:
                pass
        info = {"collected": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
        try:
            info["Playden package"] = self._text(IDENTITY).split()[-1][:12]
        except (FileManagerError, IndexError):
            info["Playden package"] = None
        try:
            info["Playden version"] = self._text(f"{HOMEBREW}/{PLAYDEN}/playden-version").strip()
        except FileManagerError:
            info["Playden version"] = None
        found = [m.group(1) for name in ("runtime.log.1", "runtime.log") for m in FIRMWARE.finditer(texts.get(name, ""))]
        info["firmware"] = found[-1] if found else None
        info.update(self._kit())
        info["game titles"] = f"{title} (app {steam_app or '?'})" if f"title-{title}.log" in texts else "none"
        info.update(extra or {})
        names = account_names(texts.values())
        texts = {name: redact(text, names) for name, text in texts.items()}
        info["redacted"] = "Steam account name and SteamIDs"
        table = summary_table(info)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("summary.md", table)
            for name, text in sorted(texts.items()):
                archive.writestr(f"logs/{name}", text)
        return table
