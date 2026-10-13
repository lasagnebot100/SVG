"""Muster: TSP-Kunst – ein Porträt aus einer einzigen Linie"""
# 1. Punkte dort verteilen, wo das Bild dunkel ist (Stippling).
# 2. Die kürzeste Rundreise durch alle Punkte suchen (Problem des Handlungsreisenden).
# Das Ergebnis ist eine einzige, nie abgesetzte Linie – perfekt auch für den Plotter.
size(800, 800)

bild = load_image(param("Bild", "beispiel:portrait"))
anzahl = param("Punkte", 4000, 300, 12000)
kontrast = param("Kontrast", 3.0, 0.5, 6.0)
zeit = param("Rechenzeit (s)", 2.0, 0.2, 10.0)

background("#f6f1e7")
punkte = []
versuche = 0
while len(punkte) < anzahl and versuche < anzahl * 40:
    versuche += 1
    x, y = random(width), random(height)
    dunkel = 1 - bild.brightness(x / width * (bild.width - 1), y / height * (bild.height - 1))
    if dunkel > 0.2 and random() < dunkel ** kontrast:      # sehr helle Stellen bleiben leer
        punkte.append((x, y))

no_fill()
stroke("#1d3f9e")
stroke_weight(0.9)
polyline(tsp_path(punkte, max_seconds=zeit))
