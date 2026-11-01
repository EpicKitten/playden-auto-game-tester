import socket
import struct
import threading
import unittest

from playden_tester import padd

HEADER = struct.Struct("<4sBBH")


class FakePadd:
    """Answers HELLO, ACKs STATE and COMMAND, and records what it got."""

    def __init__(self, command_status=0):
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen()
        self.port = self.server.getsockname()[1]
        self.states, self.commands = [], []
        self.command_status = command_status
        threading.Thread(target=self.serve, daemon=True).start()

    def send(self, conn, kind, payload):
        conn.sendall(HEADER.pack(b"PMCP", 1, kind, len(payload)) + payload)

    def serve(self):
        while True:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            with conn:
                self.send(conn, padd.HELLO, struct.pack("<HHiiII", 1, 0x0103, 7, 0x10000001, padd.FLAG_PAD_READY, 0))
                buffer = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    while len(buffer) >= 8:
                        _, _, kind, length = HEADER.unpack_from(buffer)
                        if len(buffer) < 8 + length:
                            break
                        payload, buffer = buffer[8:8 + length], buffer[8 + length:]
                        if kind == padd.STATE:
                            seq, buttons = struct.unpack_from("<II", payload)
                            self.states.append((buttons, payload[8]))
                            self.send(conn, padd.ACK, struct.pack("<Ii", seq, 0))
                        elif kind == padd.COMMAND:
                            seq, op, arg = struct.unpack("<II32s", payload)
                            self.commands.append((op, arg.rstrip(b"\0").decode()))
                            self.send(conn, padd.ACK, struct.pack("<Ii", seq, self.command_status))

    def close(self):
        self.server.close()


class PaddTest(unittest.TestCase):
    def client(self, **fake):
        self.fake = FakePadd(**fake)
        self.addCleanup(self.fake.close)
        return padd.Padd("127.0.0.1", self.fake.port)

    def test_hello(self):
        info = self.client().hello()
        self.assertEqual(info["version"], "1.3")
        self.assertTrue(info["pad_ready"])

    def test_press_sends_button_then_neutral(self):
        self.client().press("cross", "up")
        self.assertEqual(self.fake.states[0][0], padd.BUTTONS["cross"] | padd.BUTTONS["up"])
        self.assertEqual(self.fake.states[-1], (0, padd.CENTER))

    def test_launch_and_close_commands(self):
        client = self.client()
        client.launch("FAKE78009")
        client.close_app()
        self.assertEqual(self.fake.commands, [(padd.LAUNCH, "FAKE78009"), (padd.CLOSE, "")])

    def test_refused_command_raises(self):
        client = self.client(command_status=-0x7F6BFFF0)  # 0x80940010
        with self.assertRaisesRegex(padd.PaddError, "0x80940010"):
            client.launch("FAKE78009")

    def test_unknown_button(self):
        with self.assertRaises(ValueError):
            padd.button_mask(["ps"])

    def test_not_running(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with self.assertRaisesRegex(padd.PaddError, "not reachable"):
            padd.Padd("127.0.0.1", port).hello()


if __name__ == "__main__":
    unittest.main()
