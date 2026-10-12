"""Path optimisation for pen plotters: join touching paths and minimise pen-up travel."""
from __future__ import annotations

import math
from collections import defaultdict

from .geometry import Path


def merge_paths(paths: list[Path], tol: float = 0.05) -> list[Path]:
    """Join open paths whose endpoints touch (within `tol` mm)."""

    def key(p):
        return (round(p[0] / tol), round(p[1] / tol))

    index: dict[tuple, list[tuple[int, int]]] = defaultdict(list)
    closed = [math.dist(p[0], p[-1]) <= tol for p in paths]
    for i, p in enumerate(paths):
        if not closed[i]:
            index[key(p[0])].append((i, 0))
            index[key(p[-1])].append((i, 1))
    used = [False] * len(paths)

    def take(pt):
        for i, end in index.get(key(pt), ()):
            if not used[i]:
                used[i] = True
                p = paths[i]
                return p if end == 0 else p[::-1]
        return None

    result: list[Path] = []
    for i, p in enumerate(paths):
        if used[i]:
            continue
        used[i] = True
        if closed[i]:
            result.append(p)
            continue
        chain = list(p)
        while (nxt := take(chain[-1])) is not None:
            chain.extend(nxt[1:])
        chain.reverse()
        while (nxt := take(chain[-1])) is not None:
            chain.extend(nxt[1:])
        result.append(chain)
    return result


def sort_paths(paths: list[Path], start: tuple[float, float] = (0.0, 0.0)) -> list[Path]:
    """Greedy nearest-neighbour ordering (paths may be reversed) using a spatial hash."""
    n = len(paths)
    if n < 2:
        return list(paths)
    xs = [pt[0] for p in paths for pt in (p[0], p[-1])]
    ys = [pt[1] for p in paths for pt in (p[0], p[-1])]
    minx, miny = min(xs), min(ys)
    area = max((max(xs) - minx) * (max(ys) - miny), 1.0)
    cell = max(math.sqrt(area / n) * 1.5, 0.5)

    def ckey(x, y):
        return (int((x - minx) // cell), int((y - miny) // cell))

    grid: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for i, p in enumerate(paths):
        grid[ckey(*p[0])].append((i, 0))
        grid[ckey(*p[-1])].append((i, 1))
    gx = int((max(xs) - minx) // cell) + 2
    gy = int((max(ys) - miny) // cell) + 2
    max_ring = max(gx, gy) + 1

    used = [False] * n
    remaining = n
    out: list[Path] = []
    px, py = start
    while remaining:
        best, best_end, best_d = -1, 0, math.inf
        if remaining <= 48:
            for i in range(n):
                if used[i]:
                    continue
                for end in (0, 1):
                    q = paths[i][0 if end == 0 else -1]
                    d = (q[0] - px) ** 2 + (q[1] - py) ** 2
                    if d < best_d:
                        best, best_end, best_d = i, end, d
        else:
            cx, cy = ckey(px, py)
            for r in range(max_ring + 1):
                if r == 0:
                    cells = [(cx, cy)]
                else:
                    cells = [(cx + dx, cy + dy) for dx in range(-r, r + 1) for dy in (-r, r)]
                    cells += [(cx + dx, cy + dy) for dx in (-r, r) for dy in range(-r + 1, r)]
                for c in cells:
                    lst = grid.get(c)
                    if not lst:
                        continue
                    alive = [e for e in lst if not used[e[0]]]
                    if len(alive) != len(lst):
                        grid[c] = alive
                    for i, end in alive:
                        q = paths[i][0 if end == 0 else -1]
                        d = (q[0] - px) ** 2 + (q[1] - py) ** 2
                        if d < best_d:
                            best, best_end, best_d = i, end, d
                if best >= 0 and best_d <= (r * cell) ** 2:
                    break
        used[best] = True
        remaining -= 1
        p = paths[best] if best_end == 0 else paths[best][::-1]
        out.append(p)
        px, py = p[-1]
    return out


def simplify(path: Path, min_dist: float = 0.1) -> Path:
    """Drop points closer than `min_dist` to the previously kept point."""
    if len(path) <= 2:
        return path
    out = [path[0]]
    for pt in path[1:-1]:
        if math.dist(pt, out[-1]) >= min_dist:
            out.append(pt)
    out.append(path[-1])
    return out
