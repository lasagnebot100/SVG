"""Text als Pfade – schraffierte Buchstaben für den Plotter"""
# text_paths() liefert die Umrisse der Buchstaben als Punktlisten. Damit lassen
# sich Schriften verformen, schraffieren und plotten.
size("A4", landscape=True)

wort = param("Text", "plotart")
groesse = param("Schriftgröße (mm)", 70, 10, 140)
schrift = param("Schrift", "sans-bold")     # „sans-bold“ = eine fette Schrift, die dieser Rechner hat
abstand = param("Schraffur-Abstand (mm)", 1.2, 0.4, 5.0)
winkel = param("Winkel", 35, 0, 180)
wackeln = param("Wackeln", 0.6, 0.0, 4.0)

background(255)
umrisse = text_paths(wort, width / 2, height / 2 + groesse * 0.35, groesse, font=schrift, align=CENTER)

# Umrisse leicht verformen (Noise) – sieht handgezeichnet aus
def wackel(p):
    return [(x + (noise(x * 0.05, y * 0.05) - 0.5) * wackeln * 4,
             y + (noise(x * 0.05 + 9, y * 0.05) - 0.5) * wackeln * 4) for x, y in p]

no_fill()
stroke("#1f5fbf")
stroke_weight(0.35)
for u in umrisse:
    polygon(wackel(u))
# Schraffur: Linien im Buchstaben (Löcher wie im „o“ bleiben frei)
stroke("#d2412f")
linien = []
for u in umrisse:
    linien += hatch_polygon(u, abstand, radians(winkel))
for a, b in linien:
    # Mittelpunkt in einer geraden Zahl von Umrissen → liegt in einem Loch
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if sum(point_in_polygon(mx, my, u) for u in umrisse) % 2 == 1:
        line(*a, *b)
