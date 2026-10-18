"""Recognition settings and recovery at the camera/model boundary."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_server import GestureServer
from gesture_tracking import validate_settings


class RecognitionSettingsTests(unittest.TestCase):
    def test_detection_threshold_accepts_supported_values_and_rejects_invalid_input(self):
        for value in (0.25, 0.35, 0.5):
            with self.subTest(value=value):
                try:
                    settings = validate_settings({"min_detection_confidence": value})
                except ValueError as exc:
                    self.fail(f"Valid recognition sensitivity rejected: {exc}")
                self.assertEqual(settings["min_detection_confidence"], value)
        for value in (True, "0.35", 0, 1, float("nan"), float("inf")):
            with self.subTest(invalid=value), self.assertRaises(ValueError):
                validate_settings({"min_detection_confidence": value})

    def test_legacy_settings_gain_detection_default_without_losing_saved_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            path.write_text('{"activation":"pinch","pinch_threshold":0.6}', encoding="utf-8")
            server = GestureServer(no_camera=True, settings_path=path)
            self.assertEqual(server.settings["activation"], "pinch")
            self.assertEqual(server.settings["pinch_threshold"], 0.6)
            self.assertGreater(server.settings.get("min_detection_confidence", 0), 0)


class RecognitionRecoveryTests(unittest.TestCase):
    def run_worker(self, change, close_error=False):
        """Two captured frames; the first asks the real worker to recover/reconfigure."""
        engines = []
        captures = []
        frames = []
        with tempfile.TemporaryDirectory() as temp:
            server = GestureServer(settings_path=Path(temp) / "settings.json")

            class Capture:
                def read(self):
                    return True, np.zeros((48, 64, 3), dtype=np.uint8)

                def release(self):
                    pass

            def open_camera(camera_id):
                captures.append(camera_id)
                server.cap = Capture()

            class Engine:
                def __init__(self, *args, **kwargs):
                    self.options = kwargs
                    self.closed = False
                    self.previous_closed = not engines or engines[-1].closed
                    engines.append(self)

                def detect_hand(self, frame, ts):
                    frames.append(ts)
                    if len(frames) == 1:
                        change(server)
                    else:
                        server.stop_event.set()
                    # The old recognizer produces only misses; a new one can recover.
                    return ({"landmarks": [[0.5, 0.5, 0.0]] * 21, "track_id": 1}
                            if len(engines) > 1 else None)

                def close(self):
                    self.closed = True
                    if close_error and self is engines[0]:
                        raise RuntimeError("native close failed")

            with patch.object(server, "_open_camera", open_camera), patch(
                    "gesture_server.MediaPipeHandEngine", Engine):
                server._camera_loop()
        return server, engines, captures

    def test_retry_recreates_model_even_when_it_silently_returns_no_hands(self):
        server, engines, captures = self.run_worker(lambda s: s.retry_event.set())
        self.assertTrue(server.latest_gesture["visible"], "retry must recover a recognizer returning only misses")
        self.assertEqual(len(engines), 2)
        self.assertTrue(engines[1].previous_closed)
        self.assertTrue(all(engine.closed for engine in engines))
        self.assertEqual(len(captures), 2)

    def test_sensitivity_change_reloads_model_without_reopening_camera(self):
        def change(server):
            server.settings = {**server.settings, "min_detection_confidence": 0.25}
            server.revision += 1

        server, engines, captures = self.run_worker(change)
        self.assertTrue(server.latest_gesture["visible"], "new sensitivity must reach the recognizer")
        self.assertEqual(engines[-1].options["min_detection_confidence"], 0.25)
        self.assertEqual(engines[-1].options["min_tracking_confidence"], 0.5)
        self.assertEqual(len(engines), 2)
        self.assertTrue(engines[1].previous_closed)
        self.assertEqual(len(captures), 1)
        self.assertEqual(server.applied_revision, 1)

    def test_retry_survives_old_model_close_failure(self):
        server, engines, _ = self.run_worker(lambda s: s.retry_event.set(), close_error=True)
        self.assertTrue(server.latest_gesture["visible"])
        self.assertEqual(len(engines), 2)
        self.assertTrue(all(engine.closed for engine in engines))
        self.assertEqual(server.status_msg()["error"], "")

    def test_smoothing_change_keeps_model_and_camera(self):
        def change(server):
            server.settings = {**server.settings, "smooth_alpha": 0.9}
            server.revision += 1

        server, engines, captures = self.run_worker(change)
        self.assertEqual(len(engines), 1)
        self.assertEqual(len(captures), 1)
        self.assertEqual(server.applied_revision, 1)


if __name__ == "__main__":
    unittest.main()
