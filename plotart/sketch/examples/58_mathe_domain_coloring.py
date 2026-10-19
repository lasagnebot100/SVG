"""Mathe: Domain Coloring"""
# Eine komplexe Funktion f(z) ordnet jedem Punkt der Ebene eine komplexe Zahl zu. Domain
# Coloring macht das sichtbar: Der Farbton zeigt den Winkel, die Helligkeit den Betrag.
# Nullstellen erscheinen als Punkte, um die alle Farben kreisen; Polstellen ebenso, aber
# mit umgekehrter Farbfolge. Die Formel ist frei wählbar (z = komplexe Zahl, i = √-1).
size(800, 800)

text_formel = param("Funktion f(z)", "(z^3 - 1) / (z^2 + 0.5*i)")
stil = param("Stil", "klassisch", options=[("klassisch", "Höhenringe"), ("phase", "nur Farbe"),
                                          ("raster", "Gitter")])
ausschnitt = param("Ausschnitt ±", 2.0, 0.2, 10.0)
aufloesung = param("Auflösung", 400, 100, 1200)

f = formula(text_formel, "z")
bild = domain_coloring(f, aufloesung, aufloesung, -ausschnitt, ausschnitt, -ausschnitt, ausschnitt, stil)
image(bild, 0, 0, width, height)
