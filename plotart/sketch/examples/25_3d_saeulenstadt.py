"""3D: Säulenstadt aus Noise"""
# Ein Raster aus Quadern, deren Höhe ein Noise-Feld bestimmt – wie das Pixel-Raster,
# nur in die Tiefe gezogen. Für den Plotter: „Verdeckte Linien entfernen“ ankreuzen.
size(800, 800)

n = param("Raster", 11, 4, 24)
hoehe = param("Höhe", 260.0, 20.0, 500.0)
zoom = param("Noise-Zoom", 0.18, 0.02, 0.6)
neigung = param("Neigung", 0.62, 0.0, 1.4)
drehung = param("Drehung", 0.65, -1.6, 1.6)
pal = palette(param("Palette", "kobalt", options=palettes()))

background(pal[0])
lights()
stroke(pal[0])
stroke_weight(0.8)

zelle = 470 / n
translate(width / 2, height * 0.57, -40)
rotate_x(-neigung)
rotate_y(drehung)

for i in range(n):
    for j in range(n):
        h = 6 + hoehe * noise(i * zoom, j * zoom) ** 2
        with push():
            translate((i - (n - 1) / 2) * zelle, -h / 2, (j - (n - 1) / 2) * zelle)
            fill(color_ramp(pal[1:], min(1, h / hoehe * 1.6)))
            box(zelle * 0.82, h, zelle * 0.82)
