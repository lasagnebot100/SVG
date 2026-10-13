import importlib.util
import io
import json
import shutil
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile
from pathlib import Path

from plotart import bridge
from plotart.sketch import run_sketch
from plotart.sketch.animation import Animation
from plotart.sketchfiles import SketchFileError, SketchFolder

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_FFMPEG = shutil.which("ffmpeg") is not None

LOOP = """
size(60, 40)
animation(frames=6, fps=12)
def draw():
    background(255)
    fill("red"); no_stroke()
    circle(10 + 40 * t, 20, 10)
    print(frame_count)
"""

TRAILS = """
size(60, 40)
animation(frames=8, fps=8)
x = 0
def setup():
    background("white")
def draw():
    global x
    background(255, 255, 255, 30)
    fill("blue"); no_stroke()
    rect(x, 10, 6, 6)
    x += 6
"""


class AnimationTests(unittest.TestCase):
    def test_frames_variables_and_state(self):
        a = Animation(LOOP)
        self.assertTrue(a.animated)
        self.assertEqual((a.total, a.fps), (6, 12))
        frames = []
        while (f := a.next_frame()) is not None:
            frames.append(f)
        self.assertEqual(len(frames), 6)
        self.assertEqual([f.log.strip() for f in frames], ["1", "2", "3", "4", "5", "6"])
        self.assertTrue(all(f.clears for f in frames))          # opaque background each frame
        self.assertIn('cx="10"', a.frame_svg(frames[0]))
        self.assertIn('cx="43.33"', a.frame_svg(frames[5]))     # t = 5/6

    def test_trails_do_not_clear(self):
        a = Animation(TRAILS)
        flags = []
        while (f := a.next_frame()) is not None:
            flags.append(f.clears)
        self.assertEqual(flags[0], True)
        self.assertFalse(any(flags[1:]))

    def test_static_and_no_loop(self):
        self.assertFalse(Animation("circle(1, 1, 1)").animated)
        self.assertFalse(Animation("def draw():\n    no_loop()\n    circle(1, 1, 1)\nno_loop()").animated)
        r = run_sketch(LOOP)
        self.assertTrue(r["animated"])
        self.assertEqual((r["frames"], r["fps"]), (6, 12))

    def test_error_in_later_frame(self):
        a = Animation("animation(frames=5)\ndef draw():\n    if frame_count == 3:\n        1 / 0\n")
        a.next_frame(), a.next_frame()
        f = a.next_frame()
        self.assertEqual(f.error["line"], 4)
        self.assertIsNone(a.next_frame())

    def test_transform_reset_per_frame(self):
        a = Animation("animation(frames=3)\ndef draw():\n    translate(10, 0)\n    rect(0, 0, 1, 1)\n")
        mats = [a.next_frame().items[0].matrix for _ in range(3)]
        self.assertEqual(mats[0], mats[2])                      # no accumulation across frames

    def test_loop_noise_is_seamless(self):
        a = Animation("v0 = loop_noise(0.3, 0.7, 0)\nv1 = loop_noise(0.3, 0.7, 1)\nprint(abs(v0 - v1) < 1e-12)")
        self.assertEqual(a.log.strip(), "True")

    def test_bridge_streaming_and_restart(self):
        first = bridge.anim_frames({"source": LOOP, "start": 0, "count": 4})
        self.assertEqual((len(first["frames"]), first["next"], first["total"]), (4, 4, 6))
        rest = bridge.anim_frames({"source": LOOP, "start": 4, "count": 10})
        self.assertTrue(rest["done"])
        again = bridge.anim_frames({"source": LOOP, "start": 1, "count": 1})   # going back restarts
        self.assertEqual((again["start"], again["next"]), (1, 2))


@unittest.skipUnless(HAS_PIL, "Pillow fehlt")
class VideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_png_sequence_accumulates_trails(self):
        from PIL import Image
        from plotart.sketch.video import export_animation
        res = export_animation(TRAILS, str(self.tmp / "t.zip"), "png")
        self.assertEqual(res["frames"], 8)
        with zipfile.ZipFile(self.tmp / "t.zip") as z:
            names = sorted(z.namelist())
            self.assertEqual(len(names), 8)
            last = Image.open(io.BytesIO(z.read(names[-1]))).convert("RGB")
        # the first square is still faintly visible (trail), the newest one is fully blue
        self.assertLess(last.getpixel((3, 13))[0], 250)
        self.assertEqual(last.getpixel((45, 13)), (0, 0, 255))

    def test_gif(self):
        from PIL import Image
        from plotart.sketch.video import export_animation
        export_animation(LOOP, str(self.tmp / "l.gif"), "gif")
        with Image.open(self.tmp / "l.gif") as im:
            self.assertEqual(getattr(im, "n_frames", 1), 6)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg fehlt")
    def test_mp4_and_overrides(self):
        from plotart.sketch.video import export_animation
        res = export_animation(LOOP, str(self.tmp / "l.mp4"), "mp4", frames=10, fps=25, scale=2)
        self.assertEqual((res["frames"], res["fps"], res["width"], res["height"]), (10, 25, 120, 80))
        self.assertGreater(res["bytes"], 500)

    def test_static_sketch_is_rejected(self):
        from plotart.sketch.video import ExportError, export_animation
        with self.assertRaises(ExportError):
            export_animation("circle(1, 1, 1)", str(self.tmp / "x.gif"), "gif")
        self.assertFalse((self.tmp / "x.gif").exists())


class SketchFolderTests(unittest.TestCase):
    def test_save_load_list_and_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = SketchFolder(tmp)
            folder.save("meine skizze", "circle(1, 1, 1)")
            self.assertEqual([f["name"] for f in folder.list()], ["meine skizze.py"])
            self.assertEqual(folder.load("meine skizze.py")["source"], "circle(1, 1, 1)")
            for bad in ("../x.py", "/etc/passwd", "a/b.py", ".versteckt.py", "x" * 100):
                with self.assertRaises(SketchFileError):
                    folder.save(bad, "")
            with self.assertRaises(SketchFileError):
                folder.save("meine skizze.py", "", overwrite=False)


@unittest.skipUnless(HAS_PIL, "Pillow fehlt")
class ServerTests(unittest.TestCase):
    """Starts the real desktop server and drives export jobs and files over HTTP."""

    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        from plotart import web
        from plotart.sketch.worker import SketchWorker
        cls.tmp = Path(tempfile.mkdtemp())
        web.OUTPUT_DIR = cls.tmp / "output"
        web.Handler.worker = SketchWorker(timeout=20)
        web.Handler.sketches = SketchFolder(cls.tmp / "skizzen")
        web.Handler.token = None
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        from plotart import web
        cls.httpd.shutdown()
        web.Handler.worker.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def call(self, cmd, body):
        req = urllib.request.Request(f"{self.base}/api/{cmd}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    def test_export_job_and_download(self):
        job = self.call("export_start", {"source": LOOP, "format": "gif", "name": "test"})
        self.assertEqual(job["state"], "running")
        for _ in range(200):
            st = self.call("export_status", {"id": job["id"]})
            if st["state"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(st["state"], "done", st)
        with urllib.request.urlopen(f"{self.base}/{st['url']}", timeout=10) as r:
            self.assertTrue(r.read().startswith(b"GIF8"))
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(f"{self.base}/files/..%2F..%2Fetc%2Fpasswd", timeout=10)

    def test_files_roundtrip(self):
        self.assertEqual(self.call("sketch_file_save", {"name": "a.py", "source": "x = 1"})["name"], "a.py")
        self.assertEqual(self.call("sketch_file_load", {"name": "a.py"})["source"], "x = 1")
        self.assertIn("error", self.call("sketch_file_save", {"name": "../b.py", "source": ""}))
        self.assertEqual([f["name"] for f in self.call("sketch_files", {})["files"]], ["a.py"])

    def test_anim_frames_runs_in_worker(self):
        r = self.call("anim_frames", {"source": LOOP, "start": 0, "count": 3})
        self.assertEqual(len(r["frames"]), 3)


if __name__ == "__main__":
    unittest.main()
