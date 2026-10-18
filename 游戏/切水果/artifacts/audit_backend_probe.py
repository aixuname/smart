"""Read-only audit probes: mocked camera/model and ephemeral localhost HTTP only.

Run with .venv/Scripts/python.exe artifacts/audit_backend_probe.py.
No user settings, camera, browser, model download, or OpenCV window are used.
"""
import asyncio
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from aiohttp import ClientSession, web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_server import GestureServer
from gesture_tracking import validate_settings
import preview


def report(name, **details):
    print(json.dumps({"probe": name, **details}, ensure_ascii=True))


def capture_exception_probe():
    with tempfile.TemporaryDirectory() as folder:
        server = GestureServer(settings_path=Path(folder) / "settings.json")
        clock = [100.0]
        reads = []
        opens = []
        released = []

        class Capture:
            def read(self):
                clock[0] += 1.1
                reads.append(clock[0])
                if len(reads) == 1:
                    return True, np.zeros((48, 64, 3), dtype=np.uint8)
                if len(reads) == 7:
                    server.stop_event.set()
                raise RuntimeError("simulated native read failure")

            def release(self):
                released.append(len(reads))

        def open_camera(camera_id):
            opens.append(camera_id)
            server.cap = Capture()

        with patch.object(server, "_open_camera", open_camera), patch.object(
                server.stop_event, "wait", return_value=False), patch(
                "gesture_server.time.perf_counter", side_effect=lambda: clock[0]), patch(
                "gesture_server.MediaPipeHandEngine", return_value=Mock(detect_hand=Mock(return_value=None))):
            server._camera_loop()
            status = server.status_msg()
        assert len(opens) == 1 and len(reads) == 7
        assert released == [7], "capture is only released during final cleanup"
        assert "simulated native read failure" in status["error"]
        report("capture_exception_does_not_reopen", reads=len(reads), opens=len(opens),
               failed_duration_seconds=round(reads[-1] - reads[0], 1),
               release_after_read_numbers=released, status_error=status["error"])


async def cross_origin_ws_probe():
    with tempfile.TemporaryDirectory() as folder:
        server = GestureServer(no_camera=True, settings_path=Path(folder) / "settings.json")
        runner = web.AppRunner(server.build_app())
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        try:
            async with ClientSession() as client:
                origin = "https://unrelated-origin.invalid"
                async with client.ws_connect(url + "/ws", headers={"Origin": origin}) as ws:
                    first = await ws.receive_json(timeout=2)
                    sample = {"landmarks": [[0.5, 0.5, 0.0]] * 21, "track_id": 1}
                    server._publish_gesture(sample, server.settings, 100.0)
                    for _ in range(8):
                        gesture = await ws.receive_json(timeout=2)
                        if gesture["type"] == "gesture" and gesture["visible"]:
                            break
                    else:
                        raise AssertionError("expected synthetic visible gesture")
                    assert first["type"] == "status" and "settings" in first
                async with client.post(url + "/api/retry", json={}, headers={"Origin": origin}) as response:
                    assert response.status == 403
                    post_status = response.status
            report("cross_origin_websocket_accepted", origin=origin, status_settings_read=True,
                   gesture_visible=gesture["visible"], comparable_cross_origin_post_status=post_status)
        finally:
            await runner.cleanup()


def preview_failed_read_probe():
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    capture = Mock()
    capture.isOpened.return_value = True
    capture.read.side_effect = [(True, frame), (False, None), (False, None), (False, None),
                                RuntimeError("probe stop after three failed reads")]
    native = Mock()
    native.detect_for_video.return_value = SimpleNamespace(hand_landmarks=[])
    with ExitStack() as stack:
        stack.enter_context(patch.object(sys, "argv", ["preview.py"]))
        stack.enter_context(patch("preview.ensure_model", return_value="unused.task"))
        stack.enter_context(patch("preview.Path.read_bytes", return_value=b"mock model"))
        stack.enter_context(patch("preview.vision.HandLandmarker.create_from_options", return_value=native))
        stack.enter_context(patch("preview.cv2.VideoCapture", return_value=capture))
        stack.enter_context(patch("preview.cv2.imshow"))
        stack.enter_context(patch("preview.cv2.destroyAllWindows"))
        keyboard = stack.enter_context(patch("preview.cv2.waitKey", side_effect=[-1, 27]))
        stack.enter_context(patch("preview.time.sleep"))
        try:
            preview.main()
        except RuntimeError as exc:
            assert str(exc) == "probe stop after three failed reads"
        else:
            raise AssertionError("expected probe stop: Escape is never consumed")
    assert keyboard.call_count == 1 and capture.read.call_count == 5
    assert capture.release.call_count == 1 and native.close.call_count == 1
    report("preview_failed_reads_skip_keyboard", successful_frames=1, failed_frames=3,
           keyboard_polls=keyboard.call_count, pending_escape_unread=True)


def oversized_integer_probe():
    try:
        validate_settings({"target_fps": 10 ** 400})
    except OverflowError as exc:
        report("oversized_integer_not_validation_error", exception=type(exc).__name__, detail=str(exc))
    else:
        raise AssertionError("expected OverflowError")


if __name__ == "__main__":
    capture_exception_probe()
    asyncio.run(cross_origin_ws_probe())
    preview_failed_read_probe()
    oversized_integer_probe()
