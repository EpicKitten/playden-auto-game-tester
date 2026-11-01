"""The Playden games installed on the console: title ID, name and Steam app."""
import json
from dataclasses import dataclass

from . import titlelog
from .console import HOMEBREW, LOGS, PLAYDEN
from .filemanager import FileManagerError


@dataclass
class Game:
    title: str
    name: str
    steam_app: int = None

    def as_dict(self):
        return {"title": self.title, "name": self.name, "steam_app": self.steam_app}


def title_name(files, title):
    try:
        param = json.loads(files.read_text(f"{HOMEBREW}/{title}/sce_sys/param.json")[0])
    except (FileManagerError, ValueError):
        return None
    names = param.get("localizedParameters", {})
    language = names.get("defaultLanguage", "en-US")
    return names.get(language, {}).get("titleName") or param.get("titleId")


def games(files, read_logs=True):
    """Every Playden game title (FAKE7xxxx except Playden itself), in title order."""
    titles = sorted(entry["name"] for entry in files.list(HOMEBREW)
                    if entry["type"] == "d" and entry["name"].startswith("FAKE") and entry["name"] != PLAYDEN)
    logs = {entry["name"] for entry in files.list(LOGS)} if read_logs else set()
    found = []
    for title in titles:
        app = None
        if f"title-{title}.log" in logs:
            try:
                app = titlelog.steam_app(files.read_text(f"{LOGS}/title-{title}.log")[0])
            except FileManagerError:
                pass
        found.append(Game(title, title_name(files, title) or title, app))
    return found
