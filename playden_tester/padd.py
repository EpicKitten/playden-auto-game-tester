"""Client for padd, the virtual-DualSense payload from ps5-mcp (MIT, github.com/leolobato/ps5-mcp).

padd listens on TCP 9305 and speaks PMCP v1 (ps5-mcp docs/protocol.md): controller states, and commands that
go home, launch a title and close the running game through the console's own system services. A disconnect only
returns the pad to neutral, so each call here opens its own short connection. Only one client at a time: while
another (such as the ps5-mcp app) is connected, padd answers BUSY.
"""
import socket
import struct
import time

PORT = 9305
MAGIC = b"PMCP"
HEADER = struct.Struct("<4sBBH")
HELLO, STATE, PING, ACK, ERROR, SHUTDOWN, GET_STATE, COMMAND, GET_USER = range(1, 10)
HOME, LAUNCH, CLOSE = 1, 2, 3
FLAG_PAD_READY, FLAG_USER_NAME = 0x1, 0x4

BUTTONS = {
    "l3": 0x2, "r3": 0x4, "options": 0x8,
    "up": 0x10, "right": 0x20, "down": 0x40, "left": 0x80,
    "l2": 0x100, "r2": 0x200, "l1": 0x400, "r1": 0x800,
    "triangle": 0x1000, "circle": 0x2000, "cross": 0x4000, "square": 0x8000,
    "touchpad": 0x100000,
}
CENTER = 0x80
_STATE = struct.Struct("<II6B2x" + "BBHH" * 2)
_HELLO = struct.Struct("<HHiiII")
_ACK = struct.Struct("<Ii")
_COMMAND = struct.Struct("<II32s")
_USER = struct.Struct("<ii64s")
ERRNO_TEXT = {6: "no virtual pad", 22: "invalid argument", 38: "not supported by this padd"}


class PaddError(Exception):
    pass


def button_mask(names):
    mask = 0
    for name in names:
        if name.lower() not in BUTTONS:
            raise ValueError(f"unknown button {name!r}; known: {', '.join(BUTTONS)}")
        mask |= BUTTONS[name.lower()]
    return mask


def stick_byte(value):
    """-1.0..1.0 (up/left negative) to 0..255, 0x80 at rest."""
    return max(0, min(255, round(CENTER + max(-1.0, min(1.0, float(value))) * 127.5)))


def status_text(status):
    if status < 0:
        return f"SCE error {status & 0xFFFFFFFF:#010x}"
    return ERRNO_TEXT.get(status, f"errno {status}")


class Session:
    """One connection to padd."""

    def __init__(self, host, port=PORT, timeout=10.0):
        try:
            self.sock = socket.create_connection((host, port), timeout=timeout)
        except OSError as error:
            raise PaddError(f"padd is not reachable on {host}:{port} ({error}); start it with 'padd start'") from None
        self.buffer = b""
        self.seq = 0
        kind, payload = self._receive()
        if kind == ERROR:
            raise PaddError(f"padd refused the connection: {payload[4:].decode(errors='replace')}")
        if kind != HELLO:
            raise PaddError(f"padd sent message {kind} instead of HELLO")
        protocol, version, self.pad_handle, self.user_id, self.flags, self.add_status = _HELLO.unpack(payload)
        self.version = f"{version >> 8}.{version & 0xFF}"

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    @property
    def pad_ready(self):
        return bool(self.flags & FLAG_PAD_READY)

    def _send(self, kind, payload=b""):
        self.sock.sendall(HEADER.pack(MAGIC, 1, kind, len(payload)) + payload)

    def _receive(self):
        while True:
            if len(self.buffer) >= HEADER.size:
                magic, _, kind, length = HEADER.unpack_from(self.buffer)
                if magic != MAGIC:
                    raise PaddError("padd sent a bad header")
                if len(self.buffer) >= HEADER.size + length:
                    payload = self.buffer[HEADER.size:HEADER.size + length]
                    self.buffer = self.buffer[HEADER.size + length:]
                    return kind, payload
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                raise PaddError("padd did not answer in time") from None
            if not chunk:
                raise PaddError("padd closed the connection")
            self.buffer += chunk

    def _ack(self, seq):
        while True:
            kind, payload = self._receive()
            if kind == ACK:
                acked, status = _ACK.unpack(payload)
                if acked == seq:
                    return status
            elif kind == ERROR:
                raise PaddError(f"padd error: {payload[4:].decode(errors='replace')}")

    def state(self, buttons=0, lx=CENTER, ly=CENTER, rx=CENTER, ry=CENTER, l2=0, r2=0):
        self.seq += 1
        self._send(STATE, _STATE.pack(self.seq, buttons, lx, ly, rx, ry, l2, r2, 0, 0, 0, 0, 0, 0, 0, 0))
        status = self._ack(self.seq)
        if status:
            raise PaddError(f"input refused: {status_text(status)}")

    def hold(self, seconds, **state):
        """Keep a state for some seconds; padd drops held input after 1 s without a new STATE."""
        end = time.monotonic() + seconds
        while True:
            self.state(**state)
            left = end - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(0.1, left))

    def press(self, *names, seconds=0.12):
        self.hold(seconds, buttons=button_mask(names))
        self.state()

    def command(self, op, arg=""):
        self.seq += 1
        self._send(COMMAND, _COMMAND.pack(self.seq, op, arg.encode()[:31]))
        return self._ack(self.seq)

    def user(self):
        """(user id, local profile name) of the user the pad is assigned to; padd 1.2+."""
        if not self.flags & FLAG_USER_NAME:
            return self.user_id, ""
        self._send(GET_USER)
        while True:
            kind, payload = self._receive()
            if kind == GET_USER:
                status, user_id, raw = _USER.unpack(payload)
                return user_id, raw.split(b"\0", 1)[0].decode("utf-8", "replace") if status == 0 else ""

    def shutdown(self):
        """Remove the virtual pad and stop padd (the clean way; killing it can leave a phantom controller)."""
        self._send(SHUTDOWN)
        try:
            self._ack(0)
        except PaddError:
            pass


class Padd:
    """The calls the tester makes; each one is a short session."""

    def __init__(self, host, port=PORT):
        self.host, self.port = host, port

    def session(self):
        return Session(self.host, self.port)

    def available(self):
        try:
            with self.session():
                return True
        except PaddError:
            return False

    def hello(self):
        with self.session() as s:
            user_id, name = s.user()
            return {"version": s.version, "pad_ready": s.pad_ready, "user_id": user_id, "user": name,
                    "add_status": s.add_status}

    def press(self, *names, seconds=0.12):
        with self.session() as s:
            s.press(*names, seconds=seconds)

    def stick(self, side, x, y, seconds):
        axes = {"lx": stick_byte(x), "ly": stick_byte(y)} if side == "left" else {"rx": stick_byte(x), "ry": stick_byte(y)}
        with self.session() as s:
            s.hold(seconds, **axes)
            s.state()

    def launch(self, title):
        """Start a title. The game then takes input from the virtual pad only."""
        with self.session() as s:
            status = s.command(LAUNCH, title)
        if status:
            raise PaddError(f"launch of {title} refused: {status_text(status)}")

    def close_app(self):
        """Close the running game (sceLncUtilKillApp). Raises when there is none, or it is refused."""
        with self.session() as s:
            status = s.command(CLOSE)
        if status:
            raise PaddError(f"close refused: {status_text(status)}")

    def home(self):
        """Suspend the running game and show the Home screen."""
        with self.session() as s:
            status = s.command(HOME, "suspend")
        if status:
            raise PaddError(f"home refused: {status_text(status)}")

    def shutdown(self):
        with self.session() as s:
            s.shutdown()
