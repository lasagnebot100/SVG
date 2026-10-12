"""L-System – Pflanzen aus einfachen Regeln"""
size(900, 1000)

stufen = param("Generationen", 4, 1, 7)
winkel = param("Winkel", 22.5, 5, 60)
laenge = param("Ast-Länge", 17.0, 1.0, 40.0)
zufall = param("Zufall im Winkel", 6.0, 0.0, 20.0)
regel = param("Regel", "F=FF+[+F-F-F]-[-F+F+F]",
              options=["F=FF+[+F-F-F]-[-F+F+F]", "F=F[+F]F[-F]F", "F=F[+F]F[-F][F]", "F=FF-[-F+F+F]+[+F-F-F]"])
pal = palette(param("Palette", "wald", options=palettes()))

links, rechts = regel.split("=")
text_ = "F"
for _ in range(stufen):
    text_ = "".join(rechts if ch == links else ch for ch in text_)

background(pal[0])
translate(width / 2, height - 40)
rotate(-HALF_PI)
stroke_cap(ROUND)
tiefe = 0
for ch in text_:
    if ch == "F":
        stroke(lerp_color(pal[1], pal[3], min(1, tiefe / 6)))
        stroke_weight(max(0.6, 5 - tiefe * 0.8))
        line(0, 0, laenge, 0)
        translate(laenge, 0)
    elif ch == "+":
        rotate(radians(winkel + random(-zufall, zufall)))
    elif ch == "-":
        rotate(-radians(winkel + random(-zufall, zufall)))
    elif ch == "[":
        push()
        tiefe += 1
    elif ch == "]":
        pop()
        tiefe -= 1
print(len(text_), "Zeichen")
