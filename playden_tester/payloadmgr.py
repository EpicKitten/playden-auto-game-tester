"""Payload Manager (port 8084, itsPLK's ps5-payload-manager): the payloads and processes running on the console.

It starts when the console's jailbreak loads, so it is the way back when the file manager or padd are not running.
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

PORT = 8084
# Killing these leaves nothing on the console to start payloads with.
KEEP_ALIVE = {"pldmgr.elf", "elfldr.elf"}


class PayloadManagerError(Exception):
    pass


class PayloadManager:
    def __init__(self, host, port=PORT, timeout=15.0):
        self.base, self.timeout = f"http://{host}:{port}", timeout

    def _get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=self.timeout) as response:
                return response.read()
        except (urllib.error.URLError, OSError) as error:
            raise PayloadManagerError(f"Payload Manager ({self.base}{path}): {error}") from None

    def version(self):
        return self._get("/version").decode().strip()

    def processes(self):
        return json.loads(self._get("/processes_list"))["processes"]

    def payloads(self):
        """Paths of the payloads in the console's library."""
        return json.loads(self._get("/list_payloads"))["payloads"]

    def load(self, path):
        self._get("/loadpayload:" + urllib.parse.quote(path, safe="/"))

    def find(self, *words):
        """The newest-looking library payload whose file name has one of the words, or None."""
        names = [p for p in self.payloads() if any(w in p.rsplit("/", 1)[-1].lower() for w in words)]
        return max(names, default=None)

    def kill(self, pid):
        """Stop a process by ID. Payload Manager and elfldr are refused: nothing could restart them."""
        names = {p["pid"]: p["name"] for p in self.processes()}
        if pid not in names:
            raise PayloadManagerError(f"no process with ID {pid}")
        if names[pid] in KEEP_ALIVE:
            raise PayloadManagerError(f"{names[pid]} must stay running")
        self._get(f"/process_kill?pid={pid}")
        return names[pid]


def send_elf(host, elf, port, timeout=30.0):
    """Send an ELF straight to elfldr, which runs it. This writes nothing to the console's disk."""
    with socket.create_connection((host, port), timeout=timeout) as link:
        link.sendall(elf)
