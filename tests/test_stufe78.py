"""Stages 7–8: sound & interaction, 3D in sketches, OSC, TouchDesigner, web viewer."""
import base64
import importlib.util
import json
import math
import unittest
from pathlib import Path

from plotart import bridge
from plotart.sketch import execute, run_sketch
from plotart.sketch.animation import Animation

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_NUMPY = importlib.util.find_spec("numpy") is not None
EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"

CUBE = 'size(400, 400)\nlights()\ntranslate(200, 200)\nrotate_x(0.5)\nrotate_y(0.6)\nfill("#1f5fbf")\nbox(120)\n'


class ThreeDTests(unittest.TestCase):
    def test_cube_projects_three_shaded_faces(self):
        sk, log, err, _ = execute(CUBE)
        self.assertIsNone(err, err)
        faces = [it for it in sk.items if it.data.get("from3d")]
        self.assertEqual(len(faces), 3)                          # back faces culled
        shades = {it.style.fill.hex for it in faces}
        self.assertEqual(len(shades), 3)                         # lit differently
        self.assertEqual(len(sk.meshes3d), 1)
        self.assertEqual(len(sk.meshes3d[0]["faces"]), 6)

    def test_z0_plane_matches_2d_canvas(self):
        # without rotation a plane at z = 0 lands exactly where a 2D rect would be
        sk, _, err, _ = execute('size(300, 200)\nfill(0)\ntranslate(150, 100)\nplane(100, 50)')
        self.assertIsNone(err, err)
        segs = sk.items[0].data["subpaths"][0]
        xs = sorted({round(s[1], 6) for s in segs})
        ys = sorted({round(s[2], 6) for s in segs})
        self.assertEqual(xs, [100, 200])
        self.assertEqual(ys, [75, 125])

    def test_depth_order_and_2d_on_top(self):
        src = ('size(200, 200)\nno_stroke()\ntranslate(100, 100)\nfill(255, 0, 0)\ntranslate(0, 0, 50)\nplane(40)\n'
               'fill(0, 0, 255)\ntranslate(0, 0, -100)\nplane(80)\nreset_matrix()\nfill(0, 255, 0)\ncircle(10, 10, 5)')
        sk, _, err, _ = execute(src)
        self.assertIsNone(err, err)
        fills = [it.style.fill.hex for it in sk.items]
        self.assertEqual(fills, ["#0000ff", "#ff0000", "#00ff00"])   # far → near, then 2D

    def test_lights_reset_per_frame_and_meshes_per_frame(self):
        src = ('animation(frames=2)\ndef draw():\n    background(0)\n    if frame_count == 1:\n        lights()\n'
               '    translate(200, 200)\n    fill(200)\n    box(100)\n')
        a = Animation(src)
        f1, f2 = a.next_frame(), a.next_frame()
        self.assertEqual(len(f1.meshes), 1)
        self.assertEqual(len(f2.meshes), 1)
        lit = {it.style.fill.hex for it in f1.items if it.data.get("from3d")}
        unlit = {it.style.fill.hex for it in f2.items if it.data.get("from3d")}
        self.assertEqual(unlit, {"#c8c8c8"})
        self.assertNotEqual(lit, unlit)

    def test_run_sketch_flag(self):
        self.assertTrue(run_sketch(CUBE)["has3d"])
        self.assertFalse(run_sketch("circle(10, 10, 5)")["has3d"])

    def test_glb_and_obj(self):
        from plotart.sketch.export3d import read_glb
        out = bridge.dispatch("sketch_3d", {"source": CUBE + "stroke(0)\nline3d(0, 0, 0, 0, -100, 0)"})
        glb = base64.b64decode(out["glb_base64"])
        doc = read_glb(glb)
        self.assertEqual(doc["asset"]["version"], "2.0")
        self.assertEqual(len(doc["meshes"]), 2)
        self.assertEqual(doc["meshes"][1]["primitives"][0]["mode"], 1)     # line
        pos = doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
        self.assertEqual(pos["count"], 36)                                 # 6 quads → 12 triangles
        self.assertLess(max(abs(v) for v in pos["max"] + pos["min"]), 1.2)  # 120 px ≈ 1.2 m, centred
        obj = base64.b64decode(bridge.dispatch("sketch_3d", {"source": CUBE, "format": "obj"})["obj_base64"]).decode()
        self.assertEqual(obj.count("\nv "), 8)
        self.assertEqual(obj.count("\nf "), 6)
        self.assertIn("error", bridge.dispatch("sketch_3d", {"source": "circle(1, 1, 1)"}))

    def test_hidden_lines(self):
        from plotart.sketch import to_plotter
        sk, _, err, _ = execute('size(400, 400)\nbackground(255)\nstroke(0)\nfill(255)\nrect(50, 50, 200, 200)\n'
                                'rect(150, 150, 200, 200)')
        full = to_plotter(sk, optimize=False).stats()["draw_mm"]
        hidden = to_plotter(sk, optimize=False, hidden_lines=True).stats()["draw_mm"]
        px = 25.4 / 96
        self.assertAlmostEqual(full - hidden, 200 * px, delta=0.1)             # the covered corner (2 × 100 px)

    def test_blender_scene_has_real_meshes(self):
        from plotart.blender.scene import build_scene
        sc = build_scene('size(400, 400)\nbackground(255)\n' + CUBE.split("\n", 1)[1] + 'fill(0)\ncircle(20, 20, 5)')
        shapes = sc["frames"][0]["shapes"]
        types = [s["type"] for s in shapes]
        self.assertEqual(types.count("mesh3d"), 1)
        self.assertEqual(types.count("fill"), 1)                         # projected faces are not duplicated
        bg = next(s for s in shapes if s["type"] == "background")
        dot = next(s for s in shapes if s["type"] == "fill")
        mesh = next(s for s in shapes if s["type"] == "mesh3d")
        zs = [v[2] for v in mesh["verts"]]
        self.assertLess(bg["z_base"], min(zs))                           # background behind the cube
        self.assertGreater(dot["z_base"], max(zs))                       # later 2D in front

    def test_examples_run(self):
        for path in sorted(EXAMPLES.glob("2[5-9]_*.py")):
            with self.subTest(path.name):
                r = run_sketch(path.read_text(encoding="utf-8"))
                self.assertIsNone(r["error"], r["error"])


class AudioTests(unittest.TestCase):
    def test_sample_analysis(self):
        from plotart.sketch.audio import load_audio
        a = load_audio("beispiel:beat.wav")
        self.assertAlmostEqual(a.duration, 8.0, 2)
        beats = a.beats()
        self.assertGreaterEqual(len(beats), 15)                          # 120 BPM → every 0.5 s
        self.assertLess(abs(beats[1] - 0.5), 0.03)
        self.assertTrue(a.beat(0.5))
        self.assertFalse(a.beat(0.75))
        for v in a.spectrum(16, 0.5) + [a.level(0.5), a.bass(0.5), a.mid(0.5), a.treble(0.5)]:
            self.assertTrue(0.0 <= v <= 1.0)
        self.assertGreater(a.level(0.5), a.level(0.45))                  # kick louder than the tail
        self.assertEqual(len(a.waveform(64, 1.0)), 64)
        self.assertEqual(a.frames(30), 240)

    def test_wav_formats(self):
        import io, struct, wave
        from plotart.sketch.audio import _decode_wav
        for width in (1, 2, 3, 4):
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(2); w.setsampwidth(width); w.setframerate(44100)
                full = 2 ** (8 * width - 1) - 1
                frames = b""
                for i in range(4410):
                    v = int(full * 0.5 * math.sin(math.tau * 441 * i / 44100))
                    if width == 1:
                        frames += bytes([v + 128]) * 2
                    else:
                        frames += v.to_bytes(width, "little", signed=True) * 2
                w.writeframes(frames)
            samples, rate = _decode_wav(buf.getvalue())
            self.assertEqual(rate, 22050)
            self.assertAlmostEqual(len(samples), 2205, delta=2)
            self.assertAlmostEqual(max(samples), 0.5, delta=0.02)

    def test_sketch_length_follows_sound(self):
        r = run_sketch('animation(fps=24)\na = load_audio("beispiel:beat.wav")\ndef draw():\n    background(0)')
        self.assertEqual(r["frames"], 192)
        self.assertEqual(r["audio"], ["beispiel:beat.wav"])
        r = run_sketch('a = load_audio("beispiel:beat.wav")\nanimation(frames=10)\ndef draw():\n    pass')
        self.assertEqual(r["frames"], 10)                                # explicit length wins

    def test_audio_data_command(self):
        out = bridge.dispatch("audio_data", {"name": "beispiel:beat.wav"})
        self.assertEqual(out["mime"], "audio/wav")
        self.assertTrue(base64.b64decode(out["base64"]).startswith(b"RIFF"))

    @unittest.skipUnless(HAS_PIL and importlib.util.find_spec("shutil") and __import__("shutil").which("ffmpeg"),
                         "ffmpeg/Pillow fehlt")
    def test_video_contains_sound(self):
        import subprocess, tempfile
        from plotart.sketch.video import export_animation
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "v.mp4"
            export_animation('load_audio("beispiel:beat.wav")\nanimation(frames=15)\ndef draw():\n    background(0)',
                             str(out), "mp4", scale=0.1)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                    str(out)], capture_output=True, text=True).stdout.split()
            self.assertEqual(sorted(probe), ["audio", "video"])


class InteractionTests(unittest.TestCase):
    SRC = ('pts = []\ndef mouse_pressed():\n    pts.append((mouse_x, mouse_y))\n'
           'def key_pressed(ev):\n    print("key", ev.key, keyIsPressed)\n'
           'def draw():\n    background(255)\n    print(frame_count, len(pts), mouseX, pmouse_x, param("Größe", 5, 1, 9))\n'
           '    osc_send("/f", frame_count)\n')

    def test_live_command(self):
        bridge._LIVE.update(key=None, anim=None)
        r = bridge.dispatch("anim_live", {"source": self.SRC, "input": {"mouse_x": 10, "mouse_y": 5}})
        self.assertIsNotNone(r["info"])
        self.assertEqual(r["log"].split(), ["1", "0", "10", "10", "5"])
        self.assertEqual(r["osc_out"], [["/f", [1]]] if isinstance(r["osc_out"][0], list) else [("/f", [1])])
        r = bridge.dispatch("anim_live", {"source": self.SRC, "params": {"Größe": 7},
                                          "input": {"mouse_x": 20, "mouse_y": 5, "mouse_is_pressed": True},
                                          "events": [{"type": "mouse_pressed", "x": 20, "y": 5},
                                                     {"type": "key_pressed", "key": "q", "key_code": 81}]})
        self.assertIsNone(r["info"])                                     # same session, no restart
        self.assertEqual(r["log"].split(), ["key", "q", "True", "2", "1", "20", "10", "7"])
        r = bridge.dispatch("anim_live", {"source": self.SRC, "restart": True})
        self.assertEqual(r["log"].split()[:2], ["1", "0"])

    def test_live_runs_past_the_end(self):
        a = Animation('animation(frames=3)\ndef draw():\n    print(frame_count, round(t, 3))', endless=True)
        logs = [a.next_frame().log.split() for _ in range(5)]
        self.assertEqual(logs[3], ["4", "0.0"])
        self.assertFalse(a.done)

    def test_recorded_input_replays(self):
        track = [{"x": 1, "y": 1}, {"x": 50, "y": 60, "p": 1, "e": [{"type": "mouse_pressed", "x": 50, "y": 60}]}]
        a = Animation(self.SRC, {"__input__": track})
        out = [a.next_frame().log.split() for _ in range(3)]
        self.assertEqual(out[0][:3], ["1", "0", "1"])
        self.assertEqual(out[1][:4], ["2", "1", "50", "1"])
        self.assertEqual(out[2][:4], ["3", "1", "50", "50"])            # pmouse catches up

    def test_interactive_flag_and_midi(self):
        self.assertTrue(run_sketch(self.SRC)["interactive"])
        self.assertFalse(run_sketch("circle(1, 1, 1)")["interactive"])
        a = Animation('def draw():\n    print(midi(7), midi(1, 0.5))', endless=True)
        a.set_input({"midi": {"7": 0.25}})
        self.assertEqual(a.next_frame().log.split(), ["0.25", "0.5"])

    def test_color_string_with_alpha(self):
        from plotart.sketch.color import to_color
        self.assertAlmostEqual(to_color(("#ff0000", 51)).a, 0.2)
        self.assertEqual(to_color(("#ff0000", 51)).hex, "#ff0000")


class OSCTests(unittest.TestCase):
    def test_roundtrip(self):
        from plotart.osc import decode, encode_message
        pkt = encode_message("/td/level", 0.5, 3, "hallo", True)
        self.assertEqual(len(pkt) % 4, 0)
        (addr, vals), = decode(pkt)
        self.assertEqual(addr, "/td/level")
        self.assertEqual(vals, [0.5, 3, "hallo", True])
        bundle = b"#bundle\0" + b"\0" * 8
        for m in (encode_message("/a", 1), encode_message("/b", 2.0)):
            bundle += len(m).to_bytes(4, "big") + m
        self.assertEqual(decode(bundle), [("/a", [1]), ("/b", [2.0])])

    def test_udp_and_sketch(self):
        import time
        from plotart.osc import OSCClient, OSCServer
        got = []
        srv = OSCServer(0, host="127.0.0.1", on_message=lambda a, v: got.append(a))
        try:
            cli = OSCClient("127.0.0.1", srv.port)
            cli.send("/td/level", 0.75)
            cli.send("/td/xy", 1.0, 2.0)
            for _ in range(50):
                if len(got) >= 2:
                    break
                time.sleep(0.02)
            cli.close()
            snap = srv.snapshot()
        finally:
            srv.close()
        self.assertEqual(snap["/td/level"], [0.75])
        r = bridge.dispatch("sketch_run", {"source": 'print(osc("/td/level", 0), osc("/td/xy"), osc("/fehlt", 9))',
                                           "osc": snap})
        self.assertEqual(r["log"].split(), ["0.75", "[1.0,", "2.0]", "9"])
        bridge.dispatch("sketch_run", {"source": "pass", "osc": {}})


if __name__ == "__main__":
    unittest.main()
