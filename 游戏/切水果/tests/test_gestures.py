import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_tracking import DEFAULT_SETTINGS, GestureTracker, validate_settings, blade_position
from mediapipe_engine import ensure_model
from gesture_server import GestureServer
from aiohttp import ClientSession, web


def hand():
    points = [[0.5, 0.7, 0] for _ in range(21)]
    for i, xy in {0: (0.5, 0.9), 5: (0.4, 0.6), 6: (0.4, 0.4), 8: (0.4, 0.2),
                  9: (0.5, 0.6), 17: (0.65, 0.65), 4: (0.2, 0.55)}.items():
        points[i] = [*xy, 0]
    return {"landmarks": points, "track_id": 1, "handedness": "Right"}


class TrackingTests(unittest.TestCase):
    def test_loss_reacquire_and_no_smoothing_across_gap(self):
        tracker = GestureTracker()
        first = tracker.update(hand(), DEFAULT_SETTINGS, 1)
        missing = tracker.update(None, DEFAULT_SETTINGS, 1.03)
        self.assertFalse(missing["active"])
        second = hand()
        second["landmarks"] = [[p[0] + 0.2, p[1], p[2]] for p in second["landmarks"]]
        result = tracker.update(second, DEFAULT_SETTINGS, 1.06)
        self.assertGreater(result["stroke_id"], first["stroke_id"])
        self.assertAlmostEqual(result["x"], first["x"] + 0.2)

    def test_palm_anchor_tracks_hand_instead_of_finger_flex(self):
        sample = hand()
        first = GestureTracker().update(sample, DEFAULT_SETTINGS, 1)
        self.assertTrue(first["active"], "default movement requires no pose command")
        folded = copy.deepcopy(sample)
        for i in (4, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18, 19, 20):
            folded["landmarks"][i] = [0.9, 0.9, 0]
        second = GestureTracker().update(folded, DEFAULT_SETTINGS, 1)
        self.assertEqual((first["x"], first["y"]), (second["x"], second["y"]))
        self.assertTrue(second["active"])
        self.assertNotEqual(blade_position(folded["landmarks"], 8), blade_position(sample["landmarks"], 8))
        moved = copy.deepcopy(sample)
        moved["landmarks"] = [[p[0] - 0.15, p[1] - 0.1, p[2]] for p in sample["landmarks"]]
        third = GestureTracker().update(moved, DEFAULT_SETTINGS, 2)
        self.assertAlmostEqual(third["x"], first["x"] - 0.15)
        self.assertAlmostEqual(third["y"], first["y"] - 0.1)

    def test_pinch_hysteresis_and_release(self):
        tracker = GestureTracker()
        settings = {**DEFAULT_SETTINGS, "activation": "pinch"}
        sample = hand()
        self.assertFalse(tracker.update(sample, settings, 1)["active"])
        sample["landmarks"][4] = [0.41, 0.21, 0]
        self.assertTrue(tracker.update(sample, settings, 1.1)["active"])
        sample["landmarks"][4] = [0.505, 0.2, 0]
        self.assertTrue(tracker.update(sample, settings, 1.2)["active"])
        sample["landmarks"][4] = [0.7, 0.2, 0]
        self.assertFalse(tracker.update(sample, settings, 1.3)["active"])

    def test_index_rotation_fold_and_point_choice(self):
        tracker = GestureTracker()
        settings = {**DEFAULT_SETTINGS, "activation": "index", "blade_point_index": 0}
        sample = hand()
        result = tracker.update(sample, settings, 1)
        self.assertTrue(result["active"])
        self.assertEqual((result["x"], result["y"]), (0.5, 0.9))
        rotated = copy.deepcopy(sample)
        rotated["landmarks"] = [[1 - p[0], 1 - p[1], p[2]] for p in sample["landmarks"]]
        self.assertTrue(tracker.update(rotated, settings, 1.1)["active"])
        sample["landmarks"][8] = [0.45, 0.7, 0]
        self.assertFalse(tracker.update(sample, settings, 1.2)["active"])

    def test_finite_and_validated_settings(self):
        for invalid in [{"camera_id": -1}, {"smooth_alpha": float("nan")}, {"camera_id": True},
                        {"target_fps": 20.5}, {"activation": "unknown"}, {"unknown": 1}, []]:
            with self.assertRaises(ValueError):
                validate_settings(invalid)
        sample = hand()
        sample["landmarks"][8][0] = float("nan")
        self.assertFalse(GestureTracker().update(sample, DEFAULT_SETTINGS, 1)["visible"])

    def test_local_unicode_model_preferred_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "中文模型"
            folder.mkdir()
            model = folder / "hand_landmarker.task"
            with zipfile.ZipFile(model, "w") as bundle:
                bundle.writestr("hand_detector.tflite", b"test")
                bundle.writestr("hand_landmarks_detector.tflite", b"test")
            with patch("mediapipe_engine.urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
                self.assertEqual(ensure_model(folder), str(model))

    def test_corrupt_download_does_not_replace_cache(self):
        import io
        with tempfile.TemporaryDirectory() as temp:
            model = Path(temp) / "hand_landmarker.task"
            model.write_bytes(b"incomplete")
            with patch("mediapipe_engine._cache_dir", return_value=temp), patch(
                    "mediapipe_engine.urllib.request.urlopen", return_value=io.BytesIO(b"error page")):
                self.assertIsNone(ensure_model())
            self.assertEqual(model.read_bytes(), b"incomplete")
            self.assertFalse(list(Path(temp).glob("*.part")))


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "settings.json"
        self.server = GestureServer(camera_id=3, no_camera=True, settings_path=self.path)
        self.runner = web.AppRunner(self.server.build_app())
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        self.url = "http://127.0.0.1:%d" % self.site._server.sockets[0].getsockname()[1]
        self.client = ClientSession()

    async def asyncTearDown(self):
        await self.client.close()
        await self.runner.cleanup()
        self.temp.cleanup()

    async def test_no_camera_still_has_status_heartbeat_and_static_files(self):
        async with self.client.get(self.url + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("gesture-preview", await response.text())
        async with self.client.ws_connect(self.url + "/ws") as ws:
            first = await ws.receive_json(timeout=2)
            self.assertTrue(first["camera_disabled"])
            deadline = time.monotonic() + 2
            heartbeat = False
            while time.monotonic() < deadline:
                msg = await ws.receive_json(timeout=2)
                if msg["type"] == "status":
                    heartbeat = True
                    break
            self.assertTrue(heartbeat)

    async def test_settings_validation_persistence_and_camera_override(self):
        async with self.client.get(self.url + "/api/settings") as response:
            self.assertEqual((await response.json())["camera_id"], 3)
        async with self.client.post(self.url + "/api/settings", json={"activation": "pinch", "camera_id": 2}) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(self.path.read_text())["activation"], "pinch")
        async with self.client.post(self.url + "/api/settings", json={"smooth_alpha": -1}) as response:
            self.assertEqual(response.status, 400)
        async with self.client.post(self.url + "/api/settings", data="null", headers={"Content-Type": "application/json"}) as response:
            self.assertEqual(response.status, 400)
        async with self.client.post(self.url + "/api/retry", json={}, headers={"Origin": "https://example.com"}) as response:
            self.assertEqual(response.status, 403)
        async with self.client.get(self.url + "/api/preview.jpg") as response:
            self.assertEqual(response.status, 503)

    async def test_stalled_capture_is_reported_without_waiting_for_native_read(self):
        self.server.camera_ok = True
        self.server.last_frame_at = time.perf_counter() - 3
        status = self.server.status_msg()
        self.assertFalse(status["camera_ok"])
        self.assertEqual(status["fps"], 0)
        self.assertIn("长时间", status["error"])

    async def test_gesture_wakes_publisher_and_omits_unused_landmarks(self):
        async with self.client.ws_connect(self.url + "/ws") as ws:
            await ws.receive_json(timeout=2)
            self.server._publish_gesture(hand(), self.server.settings, time.perf_counter())
            msg = await ws.receive_json(timeout=1)
            while msg["type"] != "gesture":
                msg = await ws.receive_json(timeout=1)
            self.assertTrue(msg["visible"])
            self.assertNotIn("landmarks", msg)
            self.assertNotIn("_generated_at", msg)
            self.assertGreater(msg["seq"], 0)


class CameraRecoveryTests(unittest.TestCase):
    def test_failed_read_is_reopened_and_resources_released(self):
        import numpy as np
        calls = []
        captures = []
        engines = []
        with tempfile.TemporaryDirectory() as temp:
            server = GestureServer(camera_id=4, settings_path=Path(temp) / "settings.json")
            class Capture:
                def __init__(self, camera_id, backend):
                    calls.append(camera_id)
                    captures.append(self)
                    self.released = False
                def isOpened(self): return True
                def set(self, *args): pass
                def release(self): self.released = True
                def read(self):
                    if len(captures) == 1:
                        server.retry_event.set()
                        return False, None
                    server.stop_event.set()
                    return True, np.zeros((48, 64, 3), dtype=np.uint8)
            class Engine:
                def __init__(self, *args, **kwargs):
                    self.closed = False
                    engines.append(self)
                def detect_hand(self, frame, ts): return hand()
                def close(self): self.closed = True
            with patch("gesture_server.cv2.VideoCapture", Capture), patch("gesture_server.MediaPipeHandEngine", Engine):
                server._camera_loop()
            self.assertEqual(calls, [4, 4])
            self.assertTrue(server.latest_gesture["visible"])
            self.assertTrue(all(c.released for c in captures))
            self.assertTrue(all(engine.closed for engine in engines))
            self.assertIsNone(server.engine)


if __name__ == "__main__":
    unittest.main()
