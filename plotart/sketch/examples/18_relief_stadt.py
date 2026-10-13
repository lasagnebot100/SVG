"""Relief-Stadt – für Blender: Helligkeit wird zur Höhe"""
# Im Studio ein ruhiges Raster – in Blender mit „Relief: Nach Helligkeit“
# und „Kamera: Perspektive“ wird daraus eine Stadt aus Türmen.
size(900, 900)

zellen = param("Zellen", 26, 6, 60)
luecke = param("Lücke", 0.18, 0.0, 0.5)
massstab = param("Noise-Maßstab", 0.12, 0.02, 0.4)
kontrast = param("Kontrast", 2.2, 0.5, 5.0)
pal = palette(param("Palette", "kobalt", options=palettes()))

background(pal[-1])
no_stroke()
z = width / zellen
for r in range(zellen):
    for c in range(zellen):
        n = noise(c * massstab, r * massstab)
        hell = constrain((n - 0.5) * kontrast + 0.5, 0, 1)
        if hell < 0.12:
            continue                                   # Plätze und Straßen
        fill(lerp_color(pal[1], "#ffffff", hell ** 1.5))
        s = z * (1 - luecke)
        rect(c * z + (z - s) / 2, r * z + (z - s) / 2, s, s, s * 0.08)
