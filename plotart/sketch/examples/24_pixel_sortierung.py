"""Pixel: Pixel-Sortierung mit numpy"""
# Bildpunkte als numpy-Array: In jeder Zeile werden helle Abschnitte nach
# Helligkeit sortiert – der typische „Glitch“-Look.
import numpy as np

size(800, 800)
quelle = param("Bild", "beispiel:kugeln", options=["beispiel:kugeln", "beispiel:portrait", "beispiel:schrift"])
schwelle = param("Schwelle", 0.35, 0.0, 1.0)
richtung = param("Richtung", "horizontal", options=["horizontal", "vertikal"])
koernung = param("Körnung", 0.06, 0.0, 0.3)
pal = palette(param("Palette", "sonnenuntergang", options=palettes()))

img = load_image(quelle).resize(400)
px = img.pixels                                  # H × W × 4, Werte 0 … 1
if richtung == "vertikal":
    px = px.transpose(1, 0, 2)
hell = px[..., :3].mean(axis=2)
for y in range(px.shape[0]):
    zeile, maske = px[y], hell[y] > schwelle
    x = 0
    while x < len(maske):                       # zusammenhängende helle Abschnitte sortieren
        if maske[x]:
            ende = x
            while ende < len(maske) and maske[ende]:
                ende += 1
            abschnitt = zeile[x:ende]
            zeile[x:ende] = abschnitt[np.argsort(abschnitt[..., :3].mean(axis=1))]
            x = ende
        else:
            x += 1
if richtung == "vertikal":
    px = px.transpose(1, 0, 2)

# Graustufen in eine Palette einfärben
g = px[..., :3].mean(axis=2)
stufen = np.linspace(0, 1, len(pal))
farben = np.stack([np.interp(g, stufen, [color(c).r / 255 for c in pal]),
                   np.interp(g, stufen, [color(c).g / 255 for c in pal]),
                   np.interp(g, stufen, [color(c).b / 255 for c in pal])], axis=2)
bild = create_image(px.shape[1], px.shape[0]).set_pixels(farben)
image(bild.filter(GRAIN, koernung) if koernung else bild, 0, 0, width, height)
