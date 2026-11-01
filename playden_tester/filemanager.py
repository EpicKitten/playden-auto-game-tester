"""Client for ps5-web-file-manager's JSON API (port 8888 by default).

Only the calls the tester needs: list a folder, read and write text files,
download a whole file, and hand an ELF payload to elfldr.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class FileManagerError(Exception):
    """The file manager answered with an error, or could not be reached."""

    def __init__(self, message, status=None, code=None):
        super().__init__(message)
        self.status = status
        self.code = code


class FileManager:
    def __init__(self, host, port=8888, timeout=10.0):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def _request(self, method, path, query=None, body=None, headers=None):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                detail = json.loads(raw)
                raise FileManagerError(detail.get("error") or str(error), error.code, detail.get("error_code")) from None
            except ValueError:
                raise FileManagerError(raw.decode("utf-8", "replace").strip() or str(error), error.code) from None
        except (urllib.error.URLError, OSError) as error:
            raise FileManagerError(f"cannot reach {self.base}: {error}") from None

    def _json(self, method, path, query=None, form=None):
        body = urllib.parse.urlencode(form).encode() if form is not None else None
        headers = {"Content-Type": "application/x-www-form-urlencoded"} if form is not None else None
        raw, _ = self._request(method, path, query, body, headers)
        data = json.loads(raw)
        if not data.get("ok", False):
            raise FileManagerError(data.get("error", "request failed"), code=data.get("error_code"))
        return data

    def ping(self):
        """True when the file manager answers."""
        try:
            self.list("/data")
            return True
        except FileManagerError:
            return False

    def list(self, path):
        """The entries of a folder: dicts with name, path, type ('-' file, 'd' folder), size, mtime."""
        return self._json("GET", "/api/list", {"path": path})["entries"]

    def exists(self, folder, name):
        try:
            return any(entry["name"] == name for entry in self.list(folder))
        except FileManagerError:
            return False

    def read_text(self, path):
        """(text, version) of a text file. Large files come back cut short; use download() for those."""
        raw, headers = self._request("GET", "/api/text", {"path": path})
        if raw[:1] == b"{":
            try:
                data = json.loads(raw)
                if data.get("ok") is False:
                    raise FileManagerError(data.get("error", "read failed"), code=data.get("error_code"))
            except ValueError:
                pass
        version = next((v for k, v in headers.items() if k.lower() == "x-text-version"), None)
        return raw.decode("utf-8", "replace"), version

    def write_text(self, path, text):
        """Write a text file, creating it first when it is missing."""
        folder, _, name = path.rpartition("/")
        version = None
        if self.exists(folder or "/", name):
            try:
                _, version = self.read_text(path)
            except FileManagerError as error:
                # The text API only opens known text types; a file without an extension has to be replaced.
                if error.code != "text_type_not_editable":
                    raise
                self.delete(path)
        if not version:
            version = self._json("POST", "/api/text/create", {"path": folder or "/", "name": name}).get("version")
        query = {"path": path}
        if version:
            query["version"] = version
        raw, _ = self._request("POST", "/api/text/save", query, text.encode("utf-8"),
                               {"Content-Type": "text/plain; charset=utf-8"})
        data = json.loads(raw)
        if not data.get("ok", False):
            raise FileManagerError(data.get("error", "save failed"), code=data.get("error_code"))

    def delete(self, path, timeout=10.0):
        """Delete a file and wait until it is gone (the file manager deletes in a background task)."""
        self._json("POST", "/api/delete", form={"paths": path})
        folder, _, name = path.rpartition("/")
        deadline = time.monotonic() + timeout
        while self.exists(folder or "/", name):
            if time.monotonic() > deadline:
                raise FileManagerError(f"{path} was not deleted")
            time.sleep(0.25)
        time.sleep(0.25)  # let the task finish, or the next call answers "another task is running"

    def download(self, path, retries=20):
        """The whole content of a file, as bytes."""
        task = self._json("POST", "/api/download/prepare", form={"paths": path})["task_id"]
        for _ in range(retries):
            try:
                raw, _ = self._request("GET", "/api/download", {"id": task})
                return raw
            except FileManagerError as error:
                if error.code != "active_task_not_found":
                    raise
                time.sleep(0.25)
        raise FileManagerError(f"download of {path} never became ready")

    def launch_elf(self, path):
        """Send an ELF that is already on the console to elfldr (port 9021)."""
        self._json("POST", "/api/launch-elf", form={"path": path})
