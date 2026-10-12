"""Reaktion-Diffusion – Turing-Muster (Gray-Scott, numpy)"""
import numpy as np

size(800, 800)
muster = param("Muster", "Korallen", options=["Korallen", "Punkte", "Labyrinth", "Zellen"])
schritte = param("Schritte", 2000, 200, 8000)
pal = palette(param("Palette", "mint", options=palettes()))

f, k = {"Korallen": (0.0545, 0.062), "Punkte": (0.0367, 0.0649),
        "Labyrinth": (0.029, 0.057), "Zellen": (0.0263, 0.06)}[muster]
N = 180
A = np.ones((N, N))
B = np.zeros((N, N))
for _ in range(14):                        # zufällige Keime
    cx, cy = random_int(10, N - 10), random_int(10, N - 10)
    B[cy - 4:cy + 4, cx - 4:cx + 4] = 1


def lap(Z):
    return (np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)) * 0.2 + \
           (np.roll(np.roll(Z, 1, 0), 1, 1) + np.roll(np.roll(Z, 1, 0), -1, 1) +
            np.roll(np.roll(Z, -1, 0), 1, 1) + np.roll(np.roll(Z, -1, 0), -1, 1)) * 0.05 - Z


for _ in range(schritte):
    ABB = A * B * B
    A += 1.0 * lap(A) - ABB + f * (1 - A)
    B += 0.5 * lap(B) + ABB - (k + f) * B

wert = np.clip((A - B + 1) / 2, 0, 1)
wert = (wert - wert.min()) / (np.ptp(wert) or 1)
farben = [color(p) for p in pal]
rgb = np.zeros((N, N, 3))
for i, kanal in enumerate("rgb"):
    rgb[..., i] = np.interp(wert, np.linspace(0, 1, len(farben)), [getattr(c, kanal) for c in farben]) / 255
image(rgb, 0, 0, width, height)
