"""Typografie – Buchstaben-Raster mit Noise"""
size("A4")

wort = param("Wort", "PLOTART")
spalten = param("Spalten", 14, 3, 40)
massstab = param("Noise-Maßstab", 0.12, 0.01, 0.5)
drehung = param("Drehung", 0.6, 0.0, 3.0)
pal = palette(param("Palette", "kobalt", options=palettes()))

background(pal[0])
rand = 14
zelle = (width - 2 * rand) / spalten
zeilen = int((height - 2 * rand) / zelle)
no_stroke()
text_font("Helvetica, Arial, sans-serif")
text_style(BOLD)
text_align(CENTER, CENTER)
i = 0
for r in range(zeilen):
    for c in range(spalten):
        n = noise(c * massstab, r * massstab)
        with push():
            translate(rand + (c + 0.5) * zelle, rand + (r + 0.5) * zelle)
            rotate((n - 0.5) * drehung * TAU)
            text_size(zelle * map_range(n, 0.32, 0.68, 0.25, 1.7, clamp=True))
            fill(color_ramp(pal[1:], n))
            text(wort[i % len(wort)], 0, 0)
        i += 1
