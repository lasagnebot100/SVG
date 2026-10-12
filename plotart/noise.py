"""Seeded Perlin noise (pure Python) for 2D and 3D, plus fractal Brownian motion."""
from __future__ import annotations

import math
import random

_GRAD2 = [(math.cos(a), math.sin(a)) for a in (i * math.tau / 16 for i in range(16))]
_GRAD3 = [
    (1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0),
    (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
    (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1),
    (1, 1, 0), (-1, 1, 0), (0, -1, 1), (0, -1, -1),
]


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


class Perlin:
    """Classic gradient noise. Values are roughly in [-1, 1]."""

    def __init__(self, seed: int = 0):
        perm = list(range(256))
        random.Random(seed).shuffle(perm)
        self.p = perm * 2

    def noise2(self, x: float, y: float) -> float:
        p = self.p
        xf, yf = math.floor(x), math.floor(y)
        xi, yi = xf & 255, yf & 255
        x -= xf
        y -= yf
        u, v = _fade(x), _fade(y)
        aa = p[p[xi] + yi] & 15
        ab = p[p[xi] + yi + 1] & 15
        ba = p[p[xi + 1] + yi] & 15
        bb = p[p[xi + 1] + yi + 1] & 15
        g = _GRAD2
        n00 = g[aa][0] * x + g[aa][1] * y
        n10 = g[ba][0] * (x - 1) + g[ba][1] * y
        n01 = g[ab][0] * x + g[ab][1] * (y - 1)
        n11 = g[bb][0] * (x - 1) + g[bb][1] * (y - 1)
        nx0 = n00 + u * (n10 - n00)
        nx1 = n01 + u * (n11 - n01)
        return (nx0 + v * (nx1 - nx0)) * 1.41

    def noise3(self, x: float, y: float, z: float) -> float:
        p = self.p
        xf, yf, zf = math.floor(x), math.floor(y), math.floor(z)
        xi, yi, zi = xf & 255, yf & 255, zf & 255
        x -= xf
        y -= yf
        z -= zf
        u, v, w = _fade(x), _fade(y), _fade(z)
        a = p[xi] + yi
        aa, ab = p[a] + zi, p[a + 1] + zi
        b = p[xi + 1] + yi
        ba, bb = p[b] + zi, p[b + 1] + zi

        def grad(h, dx, dy, dz):
            g = _GRAD3[h & 15]
            return g[0] * dx + g[1] * dy + g[2] * dz

        def lerp(t, a_, b_):
            return a_ + t * (b_ - a_)

        return lerp(
            w,
            lerp(v,
                 lerp(u, grad(p[aa], x, y, z), grad(p[ba], x - 1, y, z)),
                 lerp(u, grad(p[ab], x, y - 1, z), grad(p[bb], x - 1, y - 1, z))),
            lerp(v,
                 lerp(u, grad(p[aa + 1], x, y, z - 1), grad(p[ba + 1], x - 1, y, z - 1)),
                 lerp(u, grad(p[ab + 1], x, y - 1, z - 1), grad(p[bb + 1], x - 1, y - 1, z - 1))),
        )

    def fbm2(self, x: float, y: float, octaves: int = 4,
             lacunarity: float = 2.0, gain: float = 0.5) -> float:
        total, amp, norm = 0.0, 1.0, 0.0
        for i in range(octaves):
            # offset each octave so lattice artefacts don't line up
            total += amp * self.noise2(x + i * 17.31, y - i * 9.73)
            norm += amp
            x *= lacunarity
            y *= lacunarity
            amp *= gain
        return total / norm
