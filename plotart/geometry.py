"""Geometry helpers that produce plotter-friendly polylines (lists of (x, y) in mm)."""
from __future__ import annotations

import math

Point = tuple[float, float]
Path = list[Point]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def smoothstep(e0: float, e1: float, x: float) -> float:
    t = clamp((x - e0) / (e1 - e0))
    return t * t * (3 - 2 * t)


def segments_for_radius(r: float, tolerance: float = 0.05) -> int:
    """Number of segments so the chord error stays below `tolerance` mm."""
    if r <= tolerance:
        return 8
    return max(8, int(math.ceil(math.pi / math.acos(1 - tolerance / r))))


def circle(cx: float, cy: float, r: float, start: float = 0.0) -> Path:
    n = segments_for_radius(r)
    return [(cx + r * math.cos(start + math.tau * i / n),
             cy + r * math.sin(start + math.tau * i / n)) for i in range(n + 1)]


def arc(cx: float, cy: float, r: float, a0: float, a1: float) -> Path:
    n = max(2, int(segments_for_radius(r) * abs(a1 - a0) / math.tau) + 1)
    return [(cx + r * math.cos(lerp(a0, a1, i / n)),
             cy + r * math.sin(lerp(a0, a1, i / n))) for i in range(n + 1)]


def rect(x0: float, y0: float, x1: float, y1: float) -> Path:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def filled_rect(x0: float, y0: float, x1: float, y1: float, pen: float,
                spacing: float) -> Path:
    """Outline plus serpentine hatching as ONE continuous path (no pen lifts).

    The path is inset by half the pen width so the inked result matches the
    requested rectangle.
    """
    h = pen / 2
    ax, ay, bx, by = x0 + h, y0 + h, x1 - h, y1 - h
    if bx - ax <= 0 and by - ay <= 0:          # smaller than the pen: a dot
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return [(cx - 0.05, cy), (cx + 0.05, cy)]
    if bx - ax <= 0:
        cx = (x0 + x1) / 2
        return [(cx, ay), (cx, by)]
    if by - ay <= 0:
        cy = (y0 + y1) / 2
        return [(ax, cy), (bx, cy)]
    path = rect(ax, ay, bx, by)
    vertical = (by - ay) >= (bx - ax)            # strokes along the long side
    span = (bx - ax) if vertical else (by - ay)
    n = max(1, int(math.ceil(span / spacing)))
    for i in range(n + 1):
        t = i / n
        if vertical:
            x = lerp(ax, bx, t)
            ends = [(x, ay), (x, by)]
        else:
            y = lerp(ay, by, t)
            ends = [(ax, y), (bx, y)]
        path.extend(ends if i % 2 == 0 else ends[::-1])
    return path


def hatch_circle(cx: float, cy: float, r: float, spacing: float, angle: float) -> Path:
    """Serpentine hatching of a disc as one continuous path."""
    ca, sa = math.cos(angle), math.sin(angle)
    n = int(2 * r / spacing)
    path: Path = []
    for i in range(n + 1):
        off = -r + (2 * r) * (i + 0.5) / (n + 1)
        half = math.sqrt(max(0.0, r * r - off * off))
        # chord perpendicular to direction (ca, sa) at offset `off`
        px, py = cx - sa * off, cy + ca * off
        a = (px - ca * half, py - sa * half)
        b = (px + ca * half, py + sa * half)
        path.extend([a, b] if i % 2 == 0 else [b, a])
    return path


def spiral(cx: float, cy: float, r: float, spacing: float, start: float = 0.0) -> Path:
    """Archimedean spiral from the rim to the centre."""
    if r <= spacing:
        return circle(cx, cy, max(r, 0.05), start)
    turns = r / spacing
    path: Path = []
    theta_max = turns * math.tau
    theta = 0.0
    while theta < theta_max:
        rr = r * (1 - theta / theta_max)
        path.append((cx + rr * math.cos(start + theta), cy + rr * math.sin(start + theta)))
        theta += max(0.02, min(0.4, 0.4 / max(rr, 0.1)))
    path.append((cx, cy))
    return circle(cx, cy, r, start) + path


def clip_polyline(path: Path, box: tuple[float, float, float, float]) -> list[Path]:
    """Clip a polyline to an axis-aligned box (Liang–Barsky per segment)."""
    x0, y0, x1, y1 = box
    out: list[Path] = []
    cur: Path = []
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        dx, dy = bx - ax, by - ay
        t0, t1 = 0.0, 1.0
        ok = True
        for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
            if p == 0:
                if q < 0:
                    ok = False
                    break
            else:
                t = q / p
                if p < 0:
                    if t > t1:
                        ok = False
                        break
                    t0 = max(t0, t)
                else:
                    if t < t0:
                        ok = False
                        break
                    t1 = min(t1, t)
        if not ok:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
            continue
        sx, sy = ax + dx * t0, ay + dy * t0
        ex, ey = ax + dx * t1, ay + dy * t1
        if t0 > 0 or not cur:
            if len(cur) >= 2:
                out.append(cur)
            cur = [(sx, sy)]
        cur.append((ex, ey))
        if t1 < 1:
            out.append(cur)
            cur = []
    if len(cur) >= 2:
        out.append(cur)
    return out


def path_length(path: Path) -> float:
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))
