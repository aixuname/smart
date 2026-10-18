"""Test-only moving hand photo -> real MediaPipe -> production HTTP/WebSocket.

Never opens a physical camera or writes the user's settings.
"""
import argparse
import math
from pathlib import Path
import sys
import tempfile
import time

import cv2
import numpy as np
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from gesture_server import GestureServer


class PhotoCapture:
    def __init__(self, owner):
        self.owner = owner
        self.start = time.perf_counter()
        self.frames = 0
        path = ROOT / "backend/handpose_x/handpose_datasets/2021-02-01_13-52-53_532.jpg"
        self.photo = cv2.resize(cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR), (150, 270))

    def read(self):
        frame = np.full((480, 640, 3), 75, dtype=np.uint8)
        if not self.owner.blank:
            x = (230 if self.owner.motion == "static" else
                 (40 if (self.frames // 3) % 2 == 0 else 430)
                 if self.owner.motion == "fast" else
                 round(230 + 190 * math.sin((time.perf_counter() - self.start) * 1.2)))
            frame[100:370, x:x + 150] = self.photo
        self.frames += 1
        return True, frame

    def release(self):
        pass


class ReplayServer(GestureServer):
    blank = False
    motion = "smooth"
    test_gesture = None

    def _publish_gesture(self, hand, settings, now, aspect=4 / 3):
        msg = super()._publish_gesture(hand, settings, now, aspect)
        # Test oracle retains the actual model landmarks for this exact WS seq.
        # It never replaces the recognizer or injects coordinates into the game.
        self.test_gesture = msg
        return msg

    async def get_test_gesture(self, request):
        return web.json_response(self.test_gesture)

    def _open_camera(self, camera_id):
        self._release_camera()
        self.cap = PhotoCapture(self)
        self.camera_error = ""

    async def set_feed(self, request):
        patch = await request.json()
        if "motion" in patch:
            if patch["motion"] not in ("fast", "smooth", "static"):
                return web.json_response({"error": "unknown motion"}, status=400)
            self.motion = patch["motion"]
        if "blank" in patch:
            self.blank = bool(patch["blank"])
        return web.json_response({"blank": self.blank, "motion": self.motion})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        server = ReplayServer(settings_path=Path(temp) / "settings.json")
        app = server.build_app()
        app.router.add_post("/test/feed", server.set_feed)
        # POST avoids the production root static GET route shadowing this fixture.
        app.router.add_post("/test/gesture", server.get_test_gesture)
        web.run_app(app, host="127.0.0.1", port=args.port, print=None)
