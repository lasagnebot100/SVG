"""Pixel-Raster – Hommage an Rasterdrucke"""
size("A3")                        # Millimeter – direkt druck- oder plotbar

spalten = param("Spalten", 46, 10, 120)
abstand = param("Zwischenraum", 0.24, 0.05, 0.6)
massstab = param("Noise-Maßstab", 0.16, 0.02, 0.6)
streckung = param("Vertikale Streckung", 3.0, 1.0, 10.0)
farbe = param("Farbe", "#1f5fbf")

background("#f6f3ec")
rand = 25
zelle = (width - 2 * rand) / spalten
zeilen = int((height - 2 * rand) / zelle)
s = zelle * (1 - abstand)
no_stroke()
fill(farbe)

for r in range(zeilen):
    u = r / zeilen
    band = max(smoothstep(0.45, 0.08, u), smoothstep(0.78, 0.97, u))   # oben & unten dicht
    for c in range(spalten):
        v = 0.6 * band + 0.4 * noise(c * massstab, r * massstab / streckung) + random(-0.08, 0.08)
        x = rand + c * zelle + (zelle - s) / 2
        y = rand + r * zelle + (zelle - s) / 2
        if v > 0.72 and r + 1 < zeilen:          # Balken: verbindet sich mit der Zelle darunter
            rect(x, y, s, zelle + s * 0.02)
        elif v > 0.42:
            rect(x, y, s, s)
        elif v > 0.26:
            k = s * map_range(v, 0.26, 0.42, 0.35, 0.85)
            rect(x + (s - k) / 2, y + (s - k) / 2, k, k)
        elif v > 0.12:
            rect(x, y + s / 2 - 0.25, s, 0.5)    # Strich
        elif chance(0.5):
            circle(x + s / 2, y + s / 2, 0.8)    # Punkt
