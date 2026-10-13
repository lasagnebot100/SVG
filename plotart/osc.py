"""Open Sound Control (OSC 1.0) over UDP – pure Python, no dependencies.

Used to connect the Studio with TouchDesigner, Max/MSP, Pure Data, VCV Rack,
TouchOSC on a phone and so on:

    plotart studio --osc-in 9000 --osc-out 127.0.0.1:9001

Incoming messages:
  /param/<Name> <value>   set a slider (name or label)
  /seed <n>, /random      change the seed
  /play, /pause           control the animation player
  /live <0|1>             interactive mode on/off
  anything else           readable in the sketch with osc("/adresse", standard)

Spec: https://opensoundcontrol.stanford.edu/spec-1_0.html
"""
from __future__ import annotations

import socket
import struct
import threading
import time


# ------------------------------------------------------------------------ encoding
def _pad(b: bytes) -> bytes:
    return b + b"\0" * (4 - len(b) % 4)


def _string(s: str) -> bytes:
    return _pad(s.encode("utf-8"))


def encode_message(address: str, *args) -> bytes:
    """address + int/float/str/bytes/bool arguments → OSC packet."""
    tags, data = ",", b""
    for a in args:
        if isinstance(a, bool):
            tags += "T" if a else "F"
        elif isinstance(a, int) and -2 ** 31 <= a < 2 ** 31:
            tags += "i"
            data += struct.pack(">i", a)
        elif isinstance(a, (int, float)):
            tags += "f"
            data += struct.pack(">f", float(a))
        elif isinstance(a, (bytes, bytearray)):
            tags += "b"
            data += struct.pack(">i", len(a)) + bytes(a) + b"\0" * (-len(a) % 4)
        elif a is None:
            tags += "N"
        else:
            tags += "s"
            data += _string(str(a))
    return _string(address) + _string(tags) + data


def _read_string(data: bytes, i: int) -> tuple[str, int]:
    end = data.index(b"\0", i)
    return data[i:end].decode("utf-8", errors="replace"), (end // 4 + 1) * 4


def decode(data: bytes, _t: float | None = None) -> list[tuple[str, list]]:
    """OSC packet (message or bundle) → [(address, [values])]."""
    if data.startswith(b"#bundle\0"):
        out, i = [], 16                          # skip "#bundle" + 8-byte time tag
        while i + 4 <= len(data):
            (size,) = struct.unpack_from(">i", data, i)
            out += decode(data[i + 4:i + 4 + size])
            i += 4 + size
        return out
    address, i = _read_string(data, 0)
    if not address.startswith("/"):
        raise ValueError("keine OSC-Nachricht")
    if i >= len(data):
        return [(address, [])]
    tags, i = _read_string(data, i)
    values = []
    for t in tags.lstrip(","):
        if t == "i":
            values.append(struct.unpack_from(">i", data, i)[0]); i += 4
        elif t == "f":
            values.append(struct.unpack_from(">f", data, i)[0]); i += 4
        elif t == "d":
            values.append(struct.unpack_from(">d", data, i)[0]); i += 8
        elif t == "h":
            values.append(struct.unpack_from(">q", data, i)[0]); i += 8
        elif t == "s" or t == "S":
            v, i = _read_string(data, i); values.append(v)
        elif t == "b":
            (n,) = struct.unpack_from(">i", data, i)
            values.append(data[i + 4:i + 4 + n]); i += 4 + n + (-n % 4)
        elif t == "T":
            values.append(True)
        elif t == "F":
            values.append(False)
        elif t in "NI":
            values.append(None)
        elif t == "c":
            values.append(chr(struct.unpack_from(">i", data, i)[0])); i += 4
        elif t in "rmt":
            values.append(struct.unpack_from(">I", data, i)[0]); i += 4 if t != "t" else 8
        else:
            break                                # unknown tag: stop safely
    return [(address, values)]


# ------------------------------------------------------------------------ UDP
class OSCClient:
    def __init__(self, host: str, port: int):
        self.addr = (host, int(port))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, address: str, *args):
        self.sock.sendto(encode_message(address, *args), self.addr)

    def close(self):
        self.sock.close()


class OSCServer:
    """Receives OSC in a background thread; keeps the latest values per address."""

    def __init__(self, port: int, host: str = "0.0.0.0", on_message=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, int(port)))
        self.sock.settimeout(0.5)
        self.port = self.sock.getsockname()[1]
        self.values: dict[str, list] = {}
        self.lock = threading.Lock()
        self.on_message = on_message
        self.count = 0
        self.last = 0.0
        self._stop = False
        self.thread = threading.Thread(target=self._run, daemon=True, name="osc-in")
        self.thread.start()

    def _run(self):
        while not self._stop:
            try:
                data, _ = self.sock.recvfrom(65536)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                messages = decode(data)
            except Exception:
                continue
            for address, values in messages:
                with self.lock:
                    self.values[address] = [v for v in values if isinstance(v, (int, float, str, bool))]
                    self.count += 1
                    self.last = time.time()
                if self.on_message:
                    try:
                        self.on_message(address, values)
                    except Exception:
                        pass

    def snapshot(self) -> dict:
        with self.lock:
            return {k: list(v) for k, v in self.values.items()}

    def close(self):
        self._stop = True
        self.sock.close()
