"""Shader: Nachbearbeitung wie ein alter Druck"""
# Erst normal zeichnen (Kreis-Raster), dann apply_shader(): das Gezeichnete ist iChannel0
# und der Shader verschiebt die Farbkanäle (Fehldruck), legt Körnung und eine Vignette darüber.
size(800, 800)

versatz = param("Kanal-Versatz", 3.0, 0.0, 12.0)
koernung = param("Körnung", 0.08, 0.0, 0.3)
pal = palette(param("Palette", "risograph", options=palettes()))

background(pal[0])
no_stroke()
n = 9
for i in range(n):
    for j in range(n):
        d = 70 * (0.3 + noise(i * 0.4, j * 0.4))
        fill(pal[1 + (i + j) % (len(pal) - 1)])
        circle(80 + i * 80, 80 + j * 80, d)

druck = create_shader("""
uniform float versatz;
uniform float koernung;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 d = versatz / iResolution.xy;
    float r = texture(iChannel0, uv + d).r;              // Rot nach rechts oben …
    float g = texture(iChannel0, uv).g;
    float b = texture(iChannel0, uv - d).b;              // … Blau nach links unten
    vec3 col = vec3(r, g, b);
    col += (hash(fragCoord) - 0.5) * koernung;           // Körnung
    float vig = smoothstep(0.95, 0.35, length(uv - 0.5));
    fragColor = vec4(col * mix(0.75, 1.0, vig), 1.0);
}
""")
apply_shader(druck, versatz=versatz, koernung=koernung)
