"""Shader: Plasma-Feld (GPU)"""
# Ein Fragment-Shader rechnet jedes Pixel gleichzeitig auf der Grafikkarte.
# Schreibweise wie auf shadertoy.com: mainImage(), iResolution, iTime, iMouse.
# Regler gehen als Uniforms hinein – param() in draw() wirkt auch live.
# Am Computer braucht es einmalig: pip install moderngl. Im Browser-Studio läuft es sofort.
size(800, 800)
animation(frames=180, fps=30)

plasma = create_shader("""
uniform float zoom;
uniform float wirbel;
uniform vec3 farbe_a;
uniform vec3 farbe_b;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - 0.5 * iResolution.xy) / iResolution.y * zoom;
    vec2 m = iMouse.z > 0.0 ? (iMouse.xy - 0.5 * iResolution.xy) / iResolution.y * zoom : vec2(0.0);
    float t = iTime * 0.6;
    float v = 0.0;
    for (int i = 1; i <= 4; i++) {                       // überlagerte Sinusfelder
        float fi = float(i);
        p += wirbel * 0.25 * vec2(sin(p.y * fi + t), cos(p.x * fi - t)) / fi;
        v += sin(length(p - m) * 3.0 * fi - t * fi) / fi;
    }
    vec3 col = mix(farbe_a, farbe_b, 0.5 + 0.5 * sin(v * 2.0));
    col *= 0.85 + 0.15 * cos(v * 6.0);                   // feine Rillen
    fragColor = vec4(col, 1.0);
}
""")

pal = palette(param("Palette", "neon", options=palettes()))


def draw():
    shader_image(plasma,
                 zoom=param("Zoom", 3.0, 0.5, 10.0),
                 wirbel=param("Wirbel", 1.0, 0.0, 3.0),
                 farbe_a=pal[1], farbe_b=pal[2])
