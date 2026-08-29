"""SFTP-Lite shared protocol constants and framing helpers.

TCP is a byte stream with no message boundaries (Ch3) — a line
(command or status) and the raw bytes that follow it can arrive in
the same recv() call. ConnBuffer is the one place that split is
handled, so both server.py and client.py read through it instead of
calling socket.recv() directly.
"""

DISCOVERY_MAGIC = "SFTPLITE_ANNOUNCE"
DEFAULT_TCP_PORT = 5050
DEFAULT_DISCOVERY_PORT = 5051
DEFAULT_BROADCAST_ADDR = "255.255.255.255"
BEACON_INTERVAL_SEC = 2
RECV_CHUNK = 4096


class ConnBuffer:
    """Wraps a connected TCP socket, buffering bytes read past a line
    boundary so they aren't lost when the next read wants raw payload."""

    def __init__(self, sock):
        self._sock = sock
        self._buf = b""

    def read_line(self):
        """Read up to and including the next b'\\r\\n', return it decoded
        without the terminator. Any bytes read past the terminator stay
        buffered for the next read_line()/read_exact() call."""
        while b"\r\n" not in self._buf:
            chunk = self._sock.recv(RECV_CHUNK)
            if not chunk:
                return None
            self._buf += chunk
        line, self._buf = self._buf.split(b"\r\n", 1)
        return line.decode("utf-8", errors="replace")

    def read_exact(self, n):
        """Read exactly n bytes, pulling from the buffered remainder first.
        Returns fewer than n bytes only on disconnect (caller must check)."""
        data = b""
        if self._buf:
            take = self._buf[:n]
            self._buf = self._buf[n:]
            data += take
        while len(data) < n:
            chunk = self._sock.recv(min(RECV_CHUNK, n - len(data)))
            if not chunk:
                break
            data += chunk
        return data

    def send_line(self, line):
        # utf-8, not ascii: filenames in real use (e.g. Thai) aren't ASCII.
        # Safe with the \r\n line-boundary logic above — \r (0x0D) and \n
        # (0x0A) never appear inside a multi-byte UTF-8 sequence, since
        # every continuation/lead byte in UTF-8 is >= 0x80.
        self._sock.sendall((line + "\r\n").encode("utf-8"))

    def send_bytes(self, data):
        self._sock.sendall(data)


def log(direction, line):
    """direction: '>>' for sent, '<<' for received."""
    print(f"{direction} {line}")
