"""Playden's web access (port 7031, Playden 0.9.0 and later): its status and the report zip its Logs page offers.

Playden builds the zip itself, with the Steam account name and SteamIDs redacted. It answers only while Playden is
open and in front, so the zip is fetched after Playden starts again following a game.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

PORT = 7031


class WebAccessError(Exception):
    pass


class WebAccess:
    def __init__(self, host, port=PORT, timeout=60):
        self.base, self.timeout = f"http://{host}:{port}", timeout

    def _get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=self.timeout) as response:
                return response.read()
        except (urllib.error.URLError, OSError) as error:
            raise WebAccessError(f"Playden's web access ({self.base}{path}): {error}") from None

    def status(self):
        return json.loads(self._get("/api/status"))

    def logs(self):
        return json.loads(self._get("/api/logs"))

    def report_zip(self, title, path, tries=6, wait=10):
        """Save Playden's report zip (its own logs plus the title's log) to path. Playden takes a moment to answer
        after it starts, so this tries again a few times."""
        query = "?" + urllib.parse.urlencode({"title": title}) if title else ""
        for attempt in range(tries):
            try:
                data = self._get("/api/report.zip" + query)
                if data[:2] != b"PK":
                    raise WebAccessError(f"Playden's report for {title} is not a zip")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                return path
            except WebAccessError:
                if attempt == tries - 1:
                    raise
                time.sleep(wait)
