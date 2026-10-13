"""Daten: Jahreskreis aus einer CSV-Datei"""
# Lädt Tabellen (auch mit Semikolon und Dezimalkomma). Eigene Daten:
# CSV in daten/ legen und unten den Dateinamen eintragen.
size(900, 900)

datei = param("Datei", "beispiel:temperaturen.csv")
pal = palette(param("Palette", "nacht", options=palettes()))

zeilen = load_csv(datei)
spalten = [k for k in zeilen[0] if isinstance(zeilen[0][k], (int, float))]
werte = [r[k] for r in zeilen for k in spalten]
lo, hi = min(werte), max(werte)
print(len(zeilen), "Zeilen ·", spalten)

background(pal[0])
translate(width / 2, height / 2)
n = len(zeilen)
for ri, spalte in reversed(list(enumerate(spalten))):    # außen zuerst
    radius = 150 + ri * 90
    for i, r in enumerate(zeilen):
        a0 = TAU * i / n - HALF_PI
        t = map_range(r[spalte], lo, hi, 0, 1)
        no_stroke()
        fill(color_ramp(pal[1:], t))
        arc(0, 0, (radius + 30 + 50 * t) * 2, (radius + 30 + 50 * t) * 2, a0 + 0.02, a0 + TAU / n - 0.02, PIE)
    fill(pal[0])
    circle(0, 0, (radius + 22) * 2)
fill(pal[2]); text_align(CENTER, CENTER); text_size(26)
text(datei.replace("beispiel:", ""), 0, 0)
text_size(14)
for i, r in enumerate(zeilen):
    a = TAU * (i + 0.5) / n - HALF_PI
    fill(pal[3])
    text(str(list(r.values())[0])[:3], cos(a) * 125, sin(a) * 125)
