"""Bild: Stippling – ein Foto aus Punkten"""
# Eigenes Foto: in den Ordner daten/ legen (im Studio: Bereich „Daten“) und
# unten den Namen eintragen, z. B. "katze.jpg".
size(800, 800)

quelle = param("Bild", "beispiel:portrait", options=["beispiel:portrait", "beispiel:kugeln", "beispiel:schrift"])
punkte = param("Punkte", 9000, 500, 40000)
groesse = param("Punktgröße", 2.4, 0.5, 8.0)
kontrast = param("Kontrast", 1.6, 0.5, 4.0)
farbe = param("Farbe", "#1d1d1f")

img = load_image(quelle)
# Bild so skalieren, dass es die Leinwand füllt
s = max(width / img.width, height / img.height)
ox, oy = (width - img.width * s) / 2, (height - img.height * s) / 2

background("#f6f3ec")
no_stroke()
fill(farbe)
gesetzt = 0
for _ in range(punkte * 4):                      # Verwerfungsverfahren: dunkel = mehr Punkte
    x, y = random(width), random(height)
    dunkel = 1 - img.brightness((x - ox) / s, (y - oy) / s)
    if random() < dunkel ** kontrast:
        circle(x, y, groesse * (0.6 + 0.6 * dunkel))
        gesetzt += 1
        if gesetzt >= punkte:
            break
print(gesetzt, "Punkte")
