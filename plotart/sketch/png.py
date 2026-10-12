"""Minimal PNG encoding for image(): numpy arrays, PIL images or nested lists → PNG bytes."""
from __future__ import annotations

import io
import struct
import zlib


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _encode(width: int, height: int, channels: int, rows) -> bytes:
    color_type = {1: 0, 2: 4, 3: 2, 4: 6}[channels]
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 6))
            + _chunk(b"IEND", b""))


def to_png(img) -> tuple[bytes, int, int]:
    """Returns (png_bytes, width, height).

    Accepted: PIL.Image; numpy array (H, W), (H, W, 3) or (H, W, 4) – floats are
    treated as 0–1, integers as 0–255; nested lists of the same shapes.
    """
    if hasattr(img, "save") and hasattr(img, "size"):          # PIL image
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), img.size[0], img.size[1]

    if hasattr(img, "shape") and hasattr(img, "dtype"):          # numpy array
        import numpy as np
        a = np.asarray(img)
        if a.ndim not in (2, 3) or (a.ndim == 3 and a.shape[2] not in (1, 2, 3, 4)):
            raise ValueError(f"image(): Form {a.shape} nicht unterstützt – erwartet (H, W), (H, W, 3) oder (H, W, 4)")
        if a.dtype.kind == "f":
            a = np.clip(a * 255 + 0.5, 0, 255)
        a = np.clip(a, 0, 255).astype(np.uint8)
        if a.ndim == 3 and a.shape[2] == 1:
            a = a[:, :, 0]
        h, w = a.shape[:2]
        ch = 1 if a.ndim == 2 else a.shape[2]
        a = np.ascontiguousarray(a)
        return _encode(w, h, ch, (a[y].tobytes() for y in range(h))), w, h

    rows = [list(r) for r in img]                                # nested lists
    h, w = len(rows), len(rows[0])
    first = rows[0][0]
    ch = len(first) if isinstance(first, (tuple, list)) else 1
    is_float = any(isinstance(v, float) for v in (first if ch > 1 else [first]))

    def conv(v):
        v = v * 255 if is_float else v
        return max(0, min(255, int(round(v))))

    out = []
    for r in rows:
        if ch == 1:
            out.append([conv(v) for v in r])
        else:
            out.append([conv(c) for px in r for c in px])
    return _encode(w, h, ch, out), w, h
