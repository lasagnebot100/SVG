"""Live & VJ (E): live coding without restart, tempo (tap, Ableton Link), output window, NDI/Spout."""
import importlib.util
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from plotart import bridge
from plotart.sketch import run_sketch
from plotart.sketch.animation import Animation

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_NUMPY = importlib.util.find_spec("numpy") is not None
EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"

BASE = """size(100, 100)
animation(frames=30, fps=30)
SCHRITT = 1
zaehler = 0
abgeleitet = SCHRITT * 10
gestartet = []

def setup():
    gestartet.append(1)

def draw():
    global zaehler
    zaehler += SCHRITT
"""


def frames(anim, n):
    for _ in range(n):
        fr = anim.next_frame()
        assert fr is not None and fr.error is None, fr and fr.error
    return anim


class HotSwapTests(unittest.TestCase):
    def test_state_stays_changed_lines_win(self):
        a = frames(Animation(BASE, endless=True), 3)
        self.assertEqual(a.ns["zaehler"], 3)
        self.assertEqual(a.hot_swap(BASE.replace("SCHRITT = 1", "SCHRITT = 5")), {"ok": True})
        self.assertEqual(a.ns["zaehler"], 3)                          # state kept
        self.assertEqual(a.ns["abgeleitet"], 50)                      # depends on the changed line
        self.assertEqual(a.ns["gestartet"], [1])                      # setup() did not run again
        frames(a, 2)
        self.assertEqual(a.ns["zaehler"], 13)
        self.assertEqual(a.frame, 5)                                  # frame_count continues

    def test_functions_and_classes_are_replaced(self):
        src = BASE + "\nclass Ding:\n    def wert(self):\n        return SCHRITT\n\nding = Ding()\n"
        a = frames(Animation(src, endless=True), 1)
        new = src.replace("zaehler += SCHRITT", "zaehler += 100").replace("return SCHRITT", "return SCHRITT * 2")
        self.assertEqual(a.hot_swap(new), {"ok": True})
        frames(a, 1)
        self.assertEqual(a.ns["zaehler"], 101)                        # new draw() …
        self.assertEqual(a.ns["Ding"]().wert(), 2)                    # … and new class, globals from the live run
        a.ns["SCHRITT"] = 7
        self.assertEqual(a.ns["Ding"]().wert(), 14)

    def test_errors_keep_the_old_code(self):
        a = frames(Animation(BASE, endless=True), 2)
        res = a.hot_swap(BASE.replace("def draw():", "def draw(:"))
        self.assertIn("Syntaxfehler", res["error"]["message"])
        res = a.hot_swap(BASE + "\nkaputt = 1 / 0\n")
        self.assertIn("ZeroDivisionError", res["error"]["message"])
        frames(a, 1)
        self.assertEqual(a.ns["zaehler"], 3)
        self.assertEqual(a.hot_swap(BASE.replace("size(100, 100)", "size(200, 100)")), {"restart": True})

    def test_runtime_error_is_fixed_by_a_swap(self):
        a = Animation(BASE.replace("zaehler += SCHRITT", "zaehler += unbekannt"), endless=True)
        self.assertIsNotNone(a.next_frame().error)
        self.assertIsNone(a.next_frame())                             # stopped …
        self.assertEqual(a.hot_swap(BASE), {"ok": True})
        self.assertIsNone(a.next_frame().error)                       # … and running again

    def test_refresh_params(self):
        src = "size(50, 50)\nn = param('Anzahl', 3, 1, 10)\nliste = [0] * n\ndef draw():\n    pass\n"
        a = frames(Animation(src, endless=True), 1)
        a.sk._param_values["Anzahl"] = 7
        a.hot_swap(src)                                               # unchanged code: nothing new
        self.assertEqual(a.ns["n"], 3)
        a.hot_swap(src, refresh_params=True)                          # slider moved
        self.assertEqual((a.ns["n"], len(a.ns["liste"])), (7, 7))

    def test_bridge_hot_flow(self):
        live = lambda src, **kw: bridge.anim_live({"source": src, "seed": 1, "hot": True, **kw})
        live(BASE, restart=True)
        live(BASE)
        r = live(BASE.replace("SCHRITT = 1", "SCHRITT = 2"))
        self.assertTrue(r["swapped"])
        broken = BASE.replace("def draw():", "def draw(:")
        self.assertIn("hot_error", live(broken))
        with mock.patch.object(Animation, "hot_swap", side_effect=AssertionError("kein zweiter Versuch")):
            r = live(broken)                                          # cached: not compiled again
        self.assertIn("hot_error", r)
        self.assertIsNotNone(r["frame"])
        self.assertEqual(bridge._LIVE["anim"].ns["zaehler"], 1 + 1 + 2 + 2 + 2)
        r = bridge.anim_live({"source": BASE, "seed": 1})             # without "hot": restart
        self.assertEqual(bridge._LIVE["anim"].ns["zaehler"], 1)


class TempoTests(unittest.TestCase):
    SRC = """size(10, 10)
animation(frames=60, fps=30)
tempo(120)
schlaege = []
werte = []
def on_beat(n):
    schlaege.append(n)
def draw():
    werte.append((round(beat, 6), bpm, round(beat_phase, 6), bar))
"""

    def test_offline_beats(self):
        a = frames(Animation(self.SRC), 60)
        self.assertEqual(a.ns["schlaege"], [0, 1, 2, 3])               # 2 s at 120 BPM
        self.assertEqual(a.ns["werte"][15], (1.0, 120.0, 0.0, 0))
        self.assertEqual(a.ns["werte"][59][3], 0)
        self.assertAlmostEqual(a.sk.beat_pulse(), math.exp(-6 * (59 / 30 * 2 % 1)))

    def test_live_clock_and_own_names(self):
        a = Animation(self.SRC, endless=True)
        a.set_input({"tempo": {"bpm": 90, "beat": 9.25}})
        frames(a, 1)
        self.assertEqual(a.ns["werte"][-1], (9.25, 90.0, 0.25, 2))
        self.assertEqual(a.ns["schlaege"], [])                         # joined mid-beat: wait for the next one
        a.set_input({"tempo": {"bpm": 90, "beat": 10.05}})
        frames(a, 1)
        self.assertEqual(a.ns["schlaege"], [10])
        a.set_input({"tempo": None})                                   # back to the sketch's tempo()
        frames(a, 1)
        self.assertEqual(a.ns["werte"][-1][1], 120.0)
        own = frames(Animation("size(10, 10)\nbeat = 'meins'\ndef draw():\n    pass\n"), 2)
        self.assertEqual(own.ns["beat"], "meins")                      # never overwritten

    def test_preview_and_validation(self):
        r = run_sketch("size(10,10)\ntempo(90)\nn = []\ndef on_beat():\n    n.append(1)\n"
                       "def draw():\n    print(bpm, len(n))\n")
        self.assertIsNone(r["error"], r["error"])
        self.assertEqual(r["log"].split(), ["90.0", "1"])
        self.assertIn("bpm muss", run_sketch("tempo(5000)")["error"]["message"])

    def test_link(self):
        from plotart import tempo as tempo_mod
        tempo_mod._link = None
        with mock.patch.dict(sys.modules, {"link": None}):
            req = {"input": {"tempo": {"link": True}}}
            self.assertIn("LinkPython-extern", tempo_mod.resolve_tempo(req))
            self.assertIsNone(req["input"]["tempo"])

        class State:
            def tempo(self):
                return 128.0

            def beatAtTime(self, micros, quantum):
                return micros / 1e6

        class Link:
            def __init__(self, bpm):
                self.enabled = False

            def captureSessionState(self):
                return State()

            def clock(self):
                return types.SimpleNamespace(micros=lambda: 3_500_000)

            def numPeers(self):
                return 2

        tempo_mod._link = None
        with mock.patch.dict(sys.modules, {"link": types.SimpleNamespace(Link=Link)}):
            req = {"input": {"tempo": {"link": True}}}
            self.assertIsNone(tempo_mod.resolve_tempo(req))
        self.assertEqual(req["input"]["tempo"], {"bpm": 128.0, "beat": 3.5, "peers": 2})
        self.assertIsNone(tempo_mod.resolve_tempo({"input": {"tempo": {"bpm": 1, "beat": 2}}}))
        tempo_mod._link = None


class VideoOutTests(unittest.TestCase):
    def test_missing_packages_are_named(self):
        from plotart import videoout
        with mock.patch.object(videoout.importlib.util, "find_spec", return_value=None):
            with self.assertRaises(videoout.VideoOutError) as cm:
                videoout.check_packages("ndi")
        self.assertIn("pip install ndi-python numpy Pillow", str(cm.exception))
        with self.assertRaises(videoout.VideoOutError):
            videoout.VideoOut("syphon")

    @unittest.skipUnless(HAS_PIL and HAS_NUMPY, "Pillow/numpy fehlt")
    def test_frames_reach_the_sender(self):
        from plotart import videoout
        sent, closed = [], []

        class FakeSender:
            def __init__(self, name):
                self.name = name

            def send(self, rgba, fps):
                sent.append((rgba.shape, tuple(int(v) for v in rgba[5, 5]), tuple(int(v) for v in rgba[5, 30]), fps))

            def close(self):
                closed.append(self.name)

        src = ("size(40, 20)\nanimation(fps=25)\ndef draw():\n    if frame_count == 1:\n        background(0, 0, 255)\n"
               "    fill(255, 0, 0)\n    no_stroke()\n    rect(frame_count * 20 - 20, 0, 10, 10)\n")
        with mock.patch.object(videoout, "check_packages"), mock.patch.object(videoout, "_NDISender", FakeSender):
            for i in range(2):
                r = bridge.anim_live({"source": src, "seed": 1, "restart": i == 0,
                                      "video": {"kind": "ndi", "name": "test", "width": 80}})
                self.assertNotIn("video_error", r)
            bridge.anim_live({"source": src, "seed": 1, "video": {"kind": None}})
        self.assertEqual(sent[0][0], (40, 80, 4))
        self.assertEqual(sent[0][1], (255, 0, 0, 255))                # frame 1: red square on blue
        self.assertEqual(sent[1][1], (255, 0, 0, 255))                # frame 2 accumulates (no background)
        self.assertEqual(sent[1][2][:3], (0, 0, 255))
        self.assertEqual(sent[0][3], 25.0)
        self.assertEqual(closed, ["test"])                            # switched off → sender closed


class OutputWindowTests(unittest.TestCase):
    def test_page_served_on_ipv6_loopback(self):
        import urllib.request
        from plotart import web
        self.assertEqual(web.PAGES["/ausgabe.html"], "ausgabe.html")
        srv = web._ipv6_loopback(0)
        if srv is None:
            self.skipTest("kein IPv6 auf diesem Rechner")
        try:
            port = srv.server_address[1]
            with urllib.request.urlopen(f"http://[::1]:{port}/ausgabe.html", timeout=10) as r:
                self.assertIn("plotart-ausgabe", r.read().decode("utf-8"))
        finally:
            srv.shutdown()
            srv.server_close()

    def test_web_build_contains_output_window(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        import build_web
        with tempfile.TemporaryDirectory() as tmp:
            build_web.build(Path(tmp), "https://example.org/pyodide/")
            self.assertIn("BroadcastChannel", (Path(tmp) / "ausgabe.html").read_text(encoding="utf-8"))


class ExampleTests(unittest.TestCase):
    def test_examples_60_61(self):
        for name in ("60_live_takt.py", "61_live_coding.py"):
            with self.subTest(name):
                src = (EXAMPLES / name).read_text(encoding="utf-8")
                r = run_sketch(src, seed=2)
                self.assertIsNone(r["error"], r["error"])
                frames(Animation(src, seed=2), 40)

    def test_api_in_help(self):
        from plotart.sketch.runner import api_reference
        ref = {g["category"]: {e["name"] for e in g["entries"]} for g in api_reference()}
        self.assertTrue({"tempo", "beat_pulse"} <= ref["Ton & Interaktion"])
        self.assertTrue({"bpm", "beat", "beat_phase", "bar"} <= ref["Variablen"])


if __name__ == "__main__":
    unittest.main()
