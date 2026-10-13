"""Muster: Höhenlinien (Marching Squares)"""
# Ein Feld – Noise-Landschaft oder Reaktion-Diffusion – wird in Höhenlinien zerlegt,
# wie auf einer Wanderkarte. Jede Höhe bekommt ihre Farbe.
size(800, 800)

quelle = param("Quelle", "noise", options=[("noise", "Noise-Landschaft"), ("rd", "Reaktion-Diffusion")])
stufen = param("Höhenstufen", 18, 3, 60)
zoom = param("Noise-Zoom", 0.004, 0.001, 0.02)
pal = palette(param("Palette", "erde", options=palettes()))

background(pal[0])
no_fill()
stroke_weight(1.2)
if quelle == "rd":
    feld = reaction_diffusion(160, 160, 2500, 0.055, 0.062)
    stufen_liste = [(i + 0.5) / stufen for i in range(stufen)]
    linien = [(lv, contour_lines(feld, lv, 0, 0, width / 159)) for lv in stufen_liste]
else:
    noise_detail(5, 0.5)

    def hoehe(x, y):
        d = dist(x, y, width / 2, height / 2) / width
        return noise(x * zoom, y * zoom) * (1.2 - d)

    raster = 4
    feld = [[hoehe(x * raster, y * raster) for x in range(width // raster + 1)] for y in range(height // raster + 1)]
    lo = min(map(min, feld))
    hi = max(map(max, feld))
    linien = [(i / stufen, contour_lines(feld, lo + (hi - lo) * (i + 0.5) / stufen, 0, 0, raster)) for i in range(stufen)]
for lv, ps in linien:
    stroke(color_ramp(pal[1:], lv))
    for p in ps:
        polyline(p)
