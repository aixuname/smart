"""Local HTTP/WebSocket service; camera and inference share a single worker."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import threading
import time

import cv2
from aiohttp import web

import config
from gesture_tracking import GestureTracker, validate_settings
from mediapipe_engine import MediaPipeHandEngine
from instance import SERVICE_ID, PROJECT_ID, CameraLease
from metrics import PipelineMetrics

CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
               (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
               (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


class GestureServer:
    def __init__(self, camera_id=None, no_camera=False, settings_path=None):
        self.settings_path = Path(settings_path or Path(config.BASE_DIR) / "settings.json")
        self.settings = validate_settings({
            "camera_id": config.CAMERA_ID, "target_fps": config.TARGET_FPS,
            "smooth_alpha": config.SMOOTH_ALPHA, "blade_point_index": config.BLADE_POINT_INDEX,
            "min_detection_confidence": config.MP_MIN_DETECTION})
        try:
            self.settings = validate_settings(json.loads(self.settings_path.read_text(encoding="utf-8")), self.settings)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            print("[设置] 已忽略无效设置文件: %s" % exc)
        if camera_id is not None:
            self.settings = validate_settings({"camera_id": camera_id}, self.settings)
        self.no_camera = no_camera
        self.cap = self.engine = self.thread = None
        self.camera_lease = None
        self.camera_ok = False
        self.model_missing = False
        self.initializing = not no_camera
        self.model_error = self.camera_error = self.inference_error = ""
        self.fps = 0.0
        self.clients = {}  # websocket -> latest-only outgoing queue
        self.stop_event = threading.Event()
        self.retry_event = threading.Event()
        self.lock = threading.Lock()
        self.latest_gesture = None
        # Publish image, anchor metadata and capture time as one immutable snapshot.
        self.preview_snapshot = None
        self.preview_requested = 0.0
        self.revision = 0
        self.applied_revision = -1
        self.tracker = GestureTracker()
        self.sequence = 0
        self.metrics = PipelineMetrics()
        self.loop = None
        self.frame_ready = None
        self.last_frame_at = None

    def build_app(self):
        @web.middleware
        async def no_cache(request, handler):
            if request.method == "POST":
                origin = request.headers.get("Origin")
                if origin and origin != "%s://%s" % (request.scheme, request.host):
                    raise web.HTTPForbidden(text="仅允许同源设置请求")
            response = await handler(request)
            response.headers["Cache-Control"] = "no-store"
            return response
        app = web.Application(middlewares=[no_cache], client_max_size=4096)
        app.router.add_get("/ws", self.handle_ws)
        app.router.add_get("/api/status", self.handle_status_http)
        app.router.add_get("/api/settings", self.get_settings)
        app.router.add_post("/api/settings", self.set_settings)
        app.router.add_post("/api/retry", self.retry)
        app.router.add_get("/api/preview.jpg", self.preview)
        app.router.add_get("/", self.index)
        app.router.add_static("/", config.FRONTEND_DIR, show_index=False)
        app.on_startup.append(self._on_startup)
        app.on_shutdown.append(self._on_shutdown)
        return app

    async def index(self, request):
        return web.FileResponse(Path(config.FRONTEND_DIR) / "index.html")

    async def get_settings(self, request):
        return web.json_response(self.settings)

    async def set_settings(self, request):
        try:
            updated = validate_settings(await request.json(), self.settings)
        except (ValueError, TypeError):
            return web.json_response({"error": "设置格式或范围不正确"}, status=400)
        try:
            temp = self.settings_path.with_suffix(".tmp")
            temp.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.settings_path)
        except OSError as exc:
            return web.json_response({"error": "保存设置失败: " + str(exc)}, status=500)
        with self.lock:
            self.settings = updated
            self.revision += 1
        return web.json_response({"settings": updated, "revision": self.revision})

    async def retry(self, request):
        self.retry_event.set()
        return web.json_response({"ok": True, "camera_disabled": self.no_camera})

    async def preview(self, request):
        now = time.perf_counter()
        self.preview_requested = now
        snapshot = self.preview_snapshot
        if not self.camera_ok or snapshot is None or now - snapshot[2] > 2:
            return web.Response(status=503, text="摄像头画面暂不可用")
        jpeg, metadata, _ = snapshot
        return web.Response(body=jpeg, content_type="image/jpeg",
                            headers={"X-Preview-Gesture": metadata})

    async def handle_status_http(self, request):
        return web.json_response(self.status_msg())

    def status_msg(self):
        frame_age = (time.perf_counter() - self.last_frame_at) if self.last_frame_at is not None else None
        stalled = self.camera_ok and frame_age is not None and frame_age > 2
        return {"type": "status", "service_id": SERVICE_ID, "project_id": PROJECT_ID,
                "model_missing": self.model_missing,
                "camera_ok": self.camera_ok and not stalled, "camera_disabled": self.no_camera,
                "initializing": self.initializing, "fps": 0 if stalled else round(self.fps, 1),
                "error": self.model_error or self.camera_error or self.inference_error or
                         ("采集或识别长时间未返回结果，请重连；若无效请重启服务" if stalled else ""),
                "frame_age_ms": round(frame_age * 1000, 1) if frame_age is not None else None,
                "settings": self.settings, "revision": self.revision,
                "applied_revision": self.applied_revision, "metrics": self.metrics.snapshot()}

    async def _on_startup(self, app):
        self.loop = asyncio.get_running_loop()
        self.frame_ready = asyncio.Event()
        self.thread = threading.Thread(target=self._camera_loop, name="gesture-camera", daemon=True)
        self.thread.start()
        self.publisher = asyncio.create_task(self._publisher())

    async def _on_shutdown(self, app):
        self.stop_event.set()
        self.publisher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self.publisher
        await asyncio.gather(*(ws.close(code=1001, message=b"Server shutdown") for ws in list(self.clients)))
        # Native camera resources belong to the worker, never close them concurrently.
        await asyncio.to_thread(self.thread.join, 3)

    async def handle_ws(self, request):
        ws = web.WebSocketResponse(heartbeat=15)
        await ws.prepare(request)
        queue = asyncio.Queue(maxsize=1)
        self.clients[ws] = queue
        async def sender():
            while True:
                batch = await queue.get()
                for msg in batch:
                    await asyncio.wait_for(ws.send_json(msg), timeout=2)
        async def guarded_sender():
            try:
                await sender()
            except (ConnectionError, asyncio.TimeoutError, RuntimeError):
                await ws.close()
        task = asyncio.create_task(guarded_sender())
        queue.put_nowait([self.status_msg()])
        try:
            async for _ in ws:
                pass
        finally:
            self.clients.pop(ws, None)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return ws

    async def _publisher(self):
        # A bounded mailbox prevents old frames accumulating when a client is slow.
        last_status = 0
        while True:
            timeout = max(0.001, 1 / max(config.STATUS_FPS, 1) - (time.perf_counter() - last_status))
            try:
                await asyncio.wait_for(self.frame_ready.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass
            self.frame_ready.clear()
            now = time.perf_counter()
            with self.lock:
                gesture, self.latest_gesture = self.latest_gesture, None
            if gesture:
                generated_at = gesture.pop("_generated_at", now)
                self.metrics.record("dispatch", (now - generated_at) * 1000)
            batch = [gesture] if gesture else []
            if now - last_status >= 1 / max(config.STATUS_FPS, 1):
                last_status = now
                batch.insert(0, self.status_msg())
            if not batch:
                continue
            for queue in list(self.clients.values()):
                if queue.full():
                    self.metrics.increment("client_dropped")
                    previous = queue.get_nowait()
                    if not any(m["type"] == "status" for m in batch):
                        batch_for_client = [m for m in previous if m["type"] == "status"] + batch
                    else:
                        batch_for_client = batch
                else:
                    batch_for_client = batch
                queue.put_nowait(batch_for_client)

    def _release_camera(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = None
        if self.camera_lease:
            self.camera_lease.release()
            self.camera_lease = None

    def _open_camera(self, camera_id):
        self._release_camera()
        self.camera_ok = False
        self.preview_snapshot = None
        self.tracker.reset()
        self.camera_lease = CameraLease(camera_id)
        try:
            acquired = self.camera_lease.acquire()
        except OSError as exc:
            self.camera_error = "无法创建摄像头占用锁: " + str(exc)
            self.camera_lease = None
            return
        if not acquired:
            self.camera_lease = None
            self.camera_error = "摄像头 %s 正由另一游戏服务使用，请关闭旧服务后重连" % camera_id
            return
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
        for backend in backends:
            cap = None
            try:
                cap = cv2.VideoCapture(camera_id, backend)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAP_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAP_HEIGHT)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap = cap
                    self.camera_error = ""
                    return
            except Exception as exc:
                self.camera_error = str(exc)
            finally:
                if cap is not None and cap is not self.cap:
                    cap.release()
        self.camera_error = "无法打开摄像头 %s；请检查连接、Windows 摄像头权限或是否被其他程序占用" % camera_id
        self._release_camera()

    def _close_engine(self):
        engine, self.engine = self.engine, None
        if engine is not None:
            try:
                engine.close()
            except Exception as exc:
                # Native close can fail; keep the worker available for retry.
                self.inference_error = "关闭识别器失败: " + str(exc)
                print("[手势] " + self.inference_error)

    def _init_engine(self, settings):
        self.initializing = True
        try:
            self.engine = MediaPipeHandEngine(
                config.MODELS_DIR, num_hands=config.MP_MAX_HANDS,
                min_detection_confidence=settings["min_detection_confidence"],
                min_tracking_confidence=config.MP_MIN_TRACKING)
            self.model_missing = False
            self.model_error = ""
            self.inference_error = ""
        except Exception as exc:
            self.model_missing = True
            self.model_error = str(exc)
            print("[手势] " + self.model_error)
        finally:
            self.initializing = False

    def _publish_gesture(self, hand, settings, now, aspect=4 / 3):
        msg = self.tracker.update(hand, settings, now, aspect)
        self.sequence += 1
        msg.update(type="gesture", ts=time.time(), revision=self.applied_revision, seq=self.sequence)
        with self.lock:
            notify = self.latest_gesture is None
            if self.latest_gesture is not None:
                self.metrics.increment("publisher_dropped")
            # The game only needs the anchor and cut state; preview draws the skeleton locally.
            self.latest_gesture = {k: v for k, v in msg.items() if k != "landmarks"}
            self.latest_gesture["_generated_at"] = time.perf_counter()
        if notify and self.loop is not None:
            try:
                self.loop.call_soon_threadsafe(self.frame_ready.set)
            except RuntimeError:
                pass
        return msg

    def _make_preview(self, frame, msg, now):
        snapshot = self.preview_snapshot
        if now - self.preview_requested > 2 or (snapshot is not None and now - snapshot[2] < 0.1):
            return
        frame = frame.copy()
        h, w = frame.shape[:2]
        points = [(int(p[0] * w), int(p[1] * h)) for p in msg["landmarks"]]
        if points:
            for a, b in CONNECTIONS:
                cv2.line(frame, points[a], points[b], (200, 220, 0), 2, cv2.LINE_AA)
            for p in points:
                cv2.circle(frame, p, 3, (255, 255, 255), -1)
            color = (0, 255, 100) if msg["active"] else (0, 180, 255)
            cv2.circle(frame, (int(msg["x"] * w), int(msg["y"] * h)), 10, color, 3)
        ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            metadata = json.dumps({key: msg[key] for key in
                                   ("x", "y", "visible", "active", "seq", "revision")},
                                  separators=(",", ":"), allow_nan=False)
            # The HTTP thread must never pair a newer anchor with an older JPEG.
            self.preview_snapshot = (jpeg.tobytes(), metadata, now)

    def _camera_loop(self):
        camera_id = None
        next_open = 0
        last_frame = None
        engine_confidence = None
        try:
            while not self.stop_event.is_set():
                now = time.perf_counter()
                frame_start = now
                with self.lock:
                    settings = dict(self.settings)
                    revision = self.revision
                retry = self.retry_event.is_set()
                if retry:
                    self.retry_event.clear()
                    next_open = 0
                confidence = settings["min_detection_confidence"]
                if not self.no_camera and (retry or confidence != engine_confidence):
                    # A recognizer can keep missing without raising an exception.
                    # Explicit retry must recreate its VIDEO tracking state too.
                    self.tracker.reset()
                    self._publish_gesture(None, settings, now)
                    self.preview_snapshot = None
                    self._close_engine()
                    self._init_engine(settings)
                    engine_confidence = confidence
                    last_frame = None
                if revision != self.applied_revision:
                    self.tracker.reset()
                    self.applied_revision = revision
                if self.no_camera:
                    self.fps = 0
                    self._publish_gesture(None, settings, now)
                    self.stop_event.wait(0.5)
                    continue
                if settings["camera_id"] != camera_id or retry or (self.cap is None and now >= next_open):
                    camera_id = settings["camera_id"]
                    self._open_camera(camera_id)
                    next_open = time.perf_counter() + 3
                try:
                    capture_start = time.perf_counter()
                    ok, frame = self.cap.read() if self.cap is not None else (False, None)
                    captured_at = time.perf_counter()
                    self.metrics.record("capture", (captured_at - capture_start) * 1000)
                    if not ok:
                        self.camera_ok = False
                        self.fps = 0
                        last_frame = None
                        self.preview_snapshot = None
                        if self.cap is not None:
                            self._release_camera()
                            self.camera_error = "摄像头读帧失败，正在自动重连"
                        self._publish_gesture(None, settings, now)
                        self.stop_event.wait(0.2)
                        continue
                    self.camera_ok = True
                    self.last_frame_at = captured_at
                    self.camera_error = ""
                    hand = self.engine.detect_hand(frame, int(captured_at * 1000)) if self.engine else None
                    self.metrics.record("inference", (time.perf_counter() - captured_at) * 1000)
                    self.inference_error = ""
                    now = time.perf_counter()
                    msg = self._publish_gesture(hand, settings, now, frame.shape[1] / frame.shape[0])
                    preview_start = time.perf_counter()
                    self._make_preview(frame, msg, now)
                    self.metrics.record("preview", (time.perf_counter() - preview_start) * 1000)
                    self.metrics.record("processing", (time.perf_counter() - capture_start) * 1000)
                    self.metrics.increment("frames")
                    if last_frame is not None:
                        measured = 1 / max(now - last_frame, 0.001)
                        self.fps = measured if self.fps == 0 else self.fps * 0.85 + measured * 0.15
                    last_frame = now
                except Exception as exc:
                    self.inference_error = "识别失败: " + str(exc)
                    self.fps = 0
                    self._publish_gesture(None, settings, time.perf_counter())
                    self.stop_event.wait(0.2)
                self.stop_event.wait(max(0, 1 / settings["target_fps"] - (time.perf_counter() - frame_start)))
        finally:
            self._release_camera()
            self._close_engine()
