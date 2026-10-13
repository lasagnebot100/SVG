"""Shader-Animation: Rückkopplung mit iChannel0"""
# Jedes Bild bekommt das vorige als Textur (iChannel0) – der Shader dreht, zoomt und
# verwischt es leicht. Neue Punkte darauf werden zu langen, leuchtenden Schweifen.
size(720, 720)
animation(frames=240, fps=30)

feedback = create_shader("""
uniform float drehung;
uniform float zoom;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy - 0.5;
    float c = cos(drehung), s = sin(drehung);
    uv = mat2(c, -s, s, c) * uv / zoom + 0.5;
    vec2 px = 1.0 / iResolution.xy;
    vec4 a = texture(iChannel0, uv);
    vec4 b = 0.25 * (texture(iChannel0, uv + vec2(px.x, 0.0)) + texture(iChannel0, uv - vec2(px.x, 0.0))
                   + texture(iChannel0, uv + vec2(0.0, px.y)) + texture(iChannel0, uv - vec2(0.0, px.y)));
    fragColor = vec4(mix(a.rgb, b.rgb, 0.5) * 0.975, 1.0);   // weich + langsam verblassend
}
""")

pal = palette(param("Palette", "sonnenuntergang", options=palettes()))
vorher = None


def draw():
    global vorher
    background(0)
    if vorher is not None:
        image(vorher, 0, 0, width, height)
    no_stroke()
    for k in range(3):
        a = TAU * (t * 2 + k / 3)
        fill(pal[1 + k % (len(pal) - 1)])
        circle(width / 2 + cos(a) * 220, height / 2 + sin(a * 1.5) * 160, 26)
    apply_shader(feedback, drehung=param("Drehung", 0.02, -0.1, 0.1), zoom=param("Zoom", 1.012, 0.98, 1.05))
    vorher = snapshot()
