"""Supplemental audit evidence; only temporary settings and mocked devices."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

import numpy as np
from aiohttp import ClientSession, web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_server import GestureServer


def report(name, **details):
    print(json.dumps({"probe": name, **details}, ensure_ascii=True))


def explicit_retry_after_exception():
    with tempfile.TemporaryDirectory() as folder:
        server = GestureServer(settings_path=Path(folder) / "settings.json")
        clock = [100.0]
        opened, released, reads = [], [], []

        class Capture:
            def __init__(self, generation):
                self.generation = generation

            def read(self):
                clock[0] += 1.1
                reads.append(self.generation)
                if self.generation == 2:
                    server.stop_event.set()
                    return True, np.zeros((48, 64, 3), dtype=np.uint8)
                if len(reads) == 4:
                    server.retry_event.set()
                raise RuntimeError("simulated native read failure")

            def release(self):
                released.append(self.generation)

        def open_camera(camera_id):
            server._release_camera()
            opened.append(camera_id)
            server.cap = Capture(len(opened))

        with patch.object(server, "_open_camera", open_camera), patch.object(
                server.stop_event, "wait", return_value=False), patch(
                "gesture_server.time.perf_counter", side_effect=lambda: clock[0]), patch(
                "gesture_server.MediaPipeHandEngine", return_value=Mock(detect_hand=Mock(return_value=None))):
            server._camera_loop()
        assert len(opened) == 2 and reads == [1, 1, 1, 1, 2]
        assert released == [1, 2] and server.inference_error == "" and server.camera_ok
        report("explicit_retry_after_read_exception", opens=len(opened),
               read_generations=reads, release_generations=released, recovered_frame=True)


async def oversized_json_boundaries():
    payload = json.dumps({"target_fps": 10 ** 400})
    assert len(payload.encode()) < 4096
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "settings.json"
        server = GestureServer(no_camera=True, settings_path=path)
        baseline = dict(server.settings)
        runner = web.AppRunner(server.build_app())
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            async with ClientSession() as client:
                async with client.post(f"http://127.0.0.1:{port}/api/settings", data=payload,
                                       headers={"Content-Type": "application/json"}) as response:
                    assert response.status == 500
                    post_status = response.status
                async with client.get(f"http://127.0.0.1:{port}/api/status") as response:
                    status = await response.json()
                    assert response.status == 200 and status["settings"] == baseline
            assert not path.exists() and server.settings == baseline and server.revision == 0
            report("oversized_integer_http_boundary", json_bytes=len(payload.encode()),
                   post_status=post_status, subsequent_status=200,
                   settings_unchanged=True, no_settings_file_written=True)
        finally:
            await runner.cleanup()
        path.write_text(payload, encoding="utf-8")
        try:
            GestureServer(no_camera=True, settings_path=path)
        except OverflowError as exc:
            report("oversized_integer_saved_file_aborts_construction",
                   exception=type(exc).__name__, no_camera=True)
        else:
            raise AssertionError("expected constructor OverflowError")


if __name__ == "__main__":
    explicit_retry_after_exception()
    asyncio.run(oversized_json_boundaries())
