"""A preview image and its hand anchor must describe the same captured frame."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_server import GestureServer


class PreviewMetadataTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = GestureServer(
            no_camera=True, settings_path=Path(__file__).parent / "_absent_preview_settings.json")
        self.server.camera_ok = True
        self.server.preview_requested = 100.0

    def frame(self, value, seq=1, *, visible=True, active=True, now=100.0):
        msg = {"x": 0.25 if visible else 0, "y": 0.75 if visible else 0,
               "visible": visible, "active": active, "seq": seq, "revision": 3,
               "landmarks": [[0.25, 0.75, 0]] * 21 if visible else []}
        self.server._make_preview(np.full((48, 64, 3), value, dtype=np.uint8), msg, now)
        return msg

    async def response(self, now=100.01):
        with patch("gesture_server.time.perf_counter", return_value=now):
            return await self.server.preview(None)

    async def test_header_stays_with_encoded_frame_when_live_gesture_changes(self):
        msg = self.frame(35)
        expected = {key: msg[key] for key in ("x", "y", "visible", "active", "seq", "revision")}
        # Inference/WS can advance before a slower preview request is handled.
        msg.update(x=0.9, y=0.1, seq=2, revision=4, active=False)
        self.server.latest_gesture = msg
        response = await self.response()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "image/jpeg")
        self.assertEqual(json.loads(response.headers["X-Preview-Gesture"]), expected)
        image = cv2.imdecode(np.frombuffer(response.body, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertLess(abs(int(image[0, 0, 0]) - 35), 3)

    async def test_replacement_keeps_inactive_and_no_hand_metadata(self):
        self.frame(35)
        for seq, visible in ((2, True), (3, False)):
            with self.subTest(visible=visible):
                msg = self.frame(140, seq, visible=visible, active=False, now=100 + seq * 0.2)
                response = await self.response(100 + seq * 0.2 + 0.01)
                metadata = json.loads(response.headers["X-Preview-Gesture"])
                self.assertEqual(metadata, {key: msg[key] for key in metadata})
                self.assertEqual(metadata["seq"], seq)
                self.assertEqual(metadata["visible"], visible)
                self.assertFalse(metadata["active"])
                image = cv2.imdecode(np.frombuffer(response.body, dtype=np.uint8), cv2.IMREAD_COLOR)
                self.assertLess(abs(int(image[0, 0, 0]) - 140), 3)

    async def test_unavailable_stale_and_camera_reset_do_not_expose_old_anchor(self):
        self.assertEqual((await self.response()).status, 503)
        self.frame(35)
        stale = await self.response(102.01)
        self.assertEqual(stale.status, 503)
        self.assertNotIn("X-Preview-Gesture", stale.headers)
        self.server.camera_ok = False
        self.assertEqual((await self.response()).status, 503)
        with patch("gesture_server.CameraLease") as lease:
            lease.return_value.acquire.return_value = False
            self.server._open_camera(0)
        # Even if the reopened capture is ready before its first preview, old data is gone.
        self.server.camera_ok = True
        self.assertEqual((await self.response()).status, 503)

    async def test_preview_only_encodes_on_demand_at_most_ten_times_per_second(self):
        self.frame(35)
        with patch("gesture_server.cv2.imencode", wraps=cv2.imencode) as encode:
            self.frame(140, seq=2, now=100.05)
            encode.assert_not_called()
            response = await self.response(100.06)
            self.assertEqual(json.loads(response.headers["X-Preview-Gesture"])["seq"], 1)
            self.frame(140, seq=2, now=100.2)
            self.assertEqual(encode.call_count, 1)
            self.frame(200, seq=3, now=103)
            self.assertEqual(encode.call_count, 1)

    async def test_failed_encoding_cannot_publish_metadata_for_an_old_image(self):
        self.frame(35)
        with patch("gesture_server.cv2.imencode", return_value=(False, None)):
            self.frame(140, seq=2, now=100.2)
        response = await self.response(100.21)
        self.assertEqual(json.loads(response.headers["X-Preview-Gesture"])["seq"], 1)
        self.assertEqual((await self.response(102.01)).status, 503)


if __name__ == "__main__":
    unittest.main()
