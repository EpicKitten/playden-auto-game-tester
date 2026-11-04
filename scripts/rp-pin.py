#!/usr/bin/env python3
"""Send rp-get-pin.elf to elfldr and show what it prints: the Remote Play PIN and account ID, then how pairing went.

Open chiaki-ng's Register window first, because the PIN lasts 120 seconds. Sending it a second time cancels pairing.
Usage: python scripts/rp-pin.py [PS5 address]   (or set PS5_HOST)
"""
import os
import socket
import sys
from pathlib import Path

ELFLDR_PORT = 9021
ELF = Path(__file__).resolve().parent.parent / "build" / "rp-get-pin" / "rp-get-pin.elf"


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PS5_HOST")
    if not host:
        sys.exit("give the PS5's address, or set PS5_HOST")
    if not ELF.is_file():
        sys.exit(f"{ELF} not found: wsl -d Ubuntu -- bash scripts/build-rp-get-pin.sh")
    with socket.create_connection((host, ELFLDR_PORT), timeout=15) as link:
        link.sendall(ELF.read_bytes())
        link.shutdown(socket.SHUT_WR)  # elfldr starts the ELF once it has all of it
        link.settimeout(150)
        while True:
            try:
                data = link.recv(4096)
            except TimeoutError:
                sys.exit("nothing more from the console after 150 s")
            if not data:
                return
            sys.stdout.write(data.decode("utf-8", "replace"))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
