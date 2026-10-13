"""Stage 10: GPU fragment shaders (moderngl on the desktop; WebGL2 is tested in the browser)."""
import unittest
from pathlib import Path

from plotart.sketch import execute, run_sketch
from plotart.sketch.shader import ShaderError, _shader_error, wrap_fragment

EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"


def _gpu():
    try:
        from plotart.sketch.shader import backend
        backend()
        return True
    except Exception:
        return False


HAS_GPU = _gpu()
try:
    import PIL  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class WrapTests(unittest.TestCase):
    def test_shadertoy_style(self):
        src = "uniform float iTime;\nvoid mainImage(out vec4 c, in vec2 p) { c = vec4(1.0); }"
        es = wrap_fragment("#version 100\n" + src, es=True)
        self.assertTrue(es.startswith("#version 300 es\nprecision highp float;"))
        self.assertEqual(es.count("uniform float iTime;"), 1)          # user's declaration is kept, not doubled
        self.assertIn("uniform vec3 iResolution;", es)
        self.assertIn("#line 1\n", es)
        self.assertIn("mainImage(c, gl_FragCoord.xy)", es)
        self.assertTrue(wrap_fragment(src, es=False).startswith("#version 330\n"))

    def test_own_main_and_errors(self):
        own = wrap_fragment("out vec4 o;\nvoid main() { o = vec4(1.0); }", es=False)
        self.assertNotIn("iResolution", own)
        with self.assertRaises(ShaderError):
            wrap_fragment("float x;", es=True)
        e = _shader_error("Shader-Fehler", "GLSL Compiler failed\n\nfragment_shader\n=====\n0:3(5): error: `x' undeclared\n")
        self.assertEqual(str(e), "Shader-Fehler: Zeile 3: `x' undeclared")
        e = _shader_error("Shader-Fehler", "ERROR: 0:7: 'nope' : undeclared identifier\n\0")
        self.assertEqual(str(e), "Shader-Fehler: Zeile 7: 'nope' : undeclared identifier")


@unittest.skipUnless(HAS_GPU, "kein OpenGL-3.3-Kontext (moderngl/EGL)")
class GPUTests(unittest.TestCase):
    def test_orientation_uniforms_and_colors(self):
        from plotart.sketch.shader import Shader
        sh = Shader("uniform vec3 farbe;\nuniform float k;\n"
                    "void mainImage(out vec4 c, in vec2 p) {\n"
                    "  c = p.y > iResolution.y * 0.5 ? vec4(farbe * k, 1.0) : vec4(0.0, 0.0, 1.0, 1.0); }")
        px = sh.render(4, 4, farbe="#ff0000", k=1)
        self.assertEqual(tuple(px[0:4]), (255, 0, 0, 255))               # top row = upper half (y up)
        self.assertEqual(tuple(px[-4:]), (0, 0, 255, 255))

    def test_sketch_shader_image_and_time(self):
        src = ('size(20, 10)\nsh = create_shader("void mainImage(out vec4 c, in vec2 p) '
               '{ c = vec4(fract(iTime), iResolution.x / 40.0, 0.0, 1.0); }")\n'
               'animation(frames=3, fps=2)\ndef draw():\n    shader_image(sh, 0, 0, 10, 10, scale=2)\n')
        r = run_sketch(src)
        self.assertIsNone(r["error"], r["error"])
        self.assertIn("data:image/png", r["svg"])
        from plotart.sketch.animation import Animation
        a = Animation(src)
        a.next_frame()
        fr = a.next_frame()                                              # time = 0.5 s
        img = fr.items[-1]
        self.assertEqual((img.data["w"], img.data["h"]), (10, 10))
        import io
        if HAS_PIL:
            from PIL import Image
            im = Image.open(io.BytesIO(img.data["png"])).convert("RGBA")
            self.assertEqual(im.size, (20, 20))                         # scale=2
            r_, g_, _, _ = im.getpixel((5, 5))
            self.assertAlmostEqual(r_, 128, delta=2)                     # fract(0.5)
            self.assertAlmostEqual(g_, 128, delta=2)                     # 20 / 40

    def test_compile_error_reaches_editor(self):
        r = run_sketch('x = 1\nshader_image(create_shader("void mainImage(out vec4 c, in vec2 p) { c = nope; }"))')
        self.assertEqual(r["error"]["line"], 2)
        self.assertIn("Zeile 1", r["error"]["message"])
        self.assertIn("nope", r["error"]["message"])

    @unittest.skipUnless(HAS_PIL, "Pillow fehlt")
    def test_apply_shader_post_processing(self):
        from PIL import Image
        import io
        sk, _, err, _ = execute('size(40, 20)\nbackground(255, 0, 0)\nfill(0, 0, 255)\nno_stroke()\nrect(0, 0, 20, 20)\n'
                                'apply_shader(create_shader("void mainImage(out vec4 c, in vec2 p) '
                                '{ c = vec4(texture(iChannel0, p / iResolution.xy).bgr, 1.0); }"))')
        self.assertIsNone(err, err)
        self.assertEqual(len(sk.items), 1)
        im = Image.open(io.BytesIO(sk.items[0].data["png"])).convert("RGB")
        self.assertEqual(im.getpixel((5, 10)), (255, 0, 0))             # blue left half → red (channels swapped)
        self.assertEqual(im.getpixel((35, 10)), (0, 0, 255))

    def test_examples(self):
        for path in sorted(EXAMPLES.glob("3[3-9]_shader*.py")):
            with self.subTest(path.name):
                if "nachbearbeitung" in path.name and not HAS_PIL:
                    continue
                r = run_sketch(path.read_text(encoding="utf-8"))
                self.assertIsNone(r["error"], r["error"])


if __name__ == "__main__":
    unittest.main()
