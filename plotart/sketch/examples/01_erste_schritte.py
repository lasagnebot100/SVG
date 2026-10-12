"""Erste Schritte – Formen, Farben, Regler"""
# Willkommen im plotart Studio!
# Ändere eine Zahl – mit „Live“ siehst du das Ergebnis sofort.
# Strg/⌘ + Enter = ausführen, 🎲 = neuer Zufall, „? Hilfe“ = alle Funktionen.

size(800, 800)                      # Leinwand in Pixel (oder size("A3") in mm)

# param(...) erzeugt automatisch einen Regler rechts
anzahl = param("Anzahl Kreise", 140, 10, 600)
groesse = param("Max. Größe", 110, 10, 300)
mischen = param("Farben mischen", True)
pal = palette(param("Palette", "risograph", options=palettes()))

background(pal[0])                  # erste Farbe der Palette = Hintergrund
no_stroke()
if mischen:
    blend_mode(MULTIPLY)            # überlappende Farben mischen sich wie Druckfarbe

for i in range(anzahl):
    fill(color(random(pal[1:])).alpha(0.85))
    d = random(8, groesse) * random() ** 0.5
    circle(random(width), random(height), d)

print("Gezeichnet:", anzahl, "Kreise")   # erscheint in der Konsole
