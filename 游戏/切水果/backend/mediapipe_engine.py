"""MediaPipe Tasks hand landmarks, with offline and Unicode path support."""
import math
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile
from gesture_tracking import blade_position, PALM_POINT_INDEX

try:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    from mediapipe import Image, ImageFormat
    _MP_AVAILABLE = True
    MP_IMPORT_ERROR = ""
except Exception as exc:
    _MP_AVAILABLE = False
    MP_IMPORT_ERROR = str(exc)

MODEL_URLS = [
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task",
]


def _cache_dir():
    path = Path.home() / ".mediapipe_cache"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _valid_model(path):
    try:
        with zipfile.ZipFile(path) as bundle:
            names = bundle.namelist()
            return ("hand_detector.tflite" in names and
                    "hand_landmarks_detector.tflite" in names and
                    bundle.testzip() is None)
    except (OSError, zipfile.BadZipFile):
        return False


def ensure_model(model_dir=None):
    """Prefer a supplied local model; download atomically with a bounded timeout."""
    if model_dir:
        local = Path(model_dir) / "hand_landmarker.task"
        if _valid_model(local):
            return str(local)
    model_path = Path(_cache_dir()) / "hand_landmarker.task"
    if _valid_model(model_path):
        return str(model_path)
    for url in MODEL_URLS:
        temp_path = None
        try:
            print("[MediaPipe] 正在下载手部模型（约 8MB）...")
            with tempfile.NamedTemporaryFile(dir=model_path.parent, suffix=".part", delete=False) as out:
                temp_path = Path(out.name)
                with urllib.request.urlopen(url, timeout=15) as response:
                    shutil.copyfileobj(response, out)
            if not _valid_model(temp_path):
                raise ValueError("下载内容不是完整的 HandLandmarker 模型")
            os.replace(temp_path, model_path)
            return str(model_path)
        except Exception as exc:
            print("[MediaPipe] 模型下载失败: %s" % exc)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    return None


class MediaPipeHandEngine:
    def __init__(self, model_dir, num_hands=1,
                 min_detection_confidence=0.35, min_tracking_confidence=0.5,
                 blade_point_index=PALM_POINT_INDEX, recover_fast_motion=True):
        if not _MP_AVAILABLE:
            raise ImportError("MediaPipe 导入失败: " + MP_IMPORT_ERROR)
        model_path = ensure_model(model_dir)
        if not model_path:
            raise FileNotFoundError("模型下载失败，请将 hand_landmarker.task 放入 " + str(model_dir))
        self.blade_point_index = blade_point_index
        self._last_ts = -1
        self._wrist = None
        self._last_detected_ts = None
        self._retry_after_ts = -1
        self.recover_fast_motion = recover_fast_motion
        self.recovery_attempts = 0
        self.recovery_successes = 0
        self.num_hands = num_hands
        self.track_id = 0
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=Path(model_path).read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=float(min_detection_confidence),
            min_hand_presence_confidence=float(min_tracking_confidence),
            min_tracking_confidence=float(min_tracking_confidence),
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def detect_hand(self, frame_bgr, ts_ms):
        if frame_bgr is None or frame_bgr.size == 0:
            return None
        self._last_ts = max(int(ts_ms), self._last_ts + 1)
        frame_ts = self._last_ts
        recent = self._last_detected_ts is not None and frame_ts - self._last_detected_ts <= 200
        rgb = frame_bgr[:, :, ::-1].copy()
        image = Image(image_format=ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, self._last_ts)
        if (not result.hand_landmarks and self.recover_fast_motion and recent and
                self._wrist is not None and frame_ts >= self._retry_after_ts):
            # A fast hand can leave VIDEO's previous crop. Once that crop fails,
            # the next inference searches for a palm again. Retry this real frame
            # once, instead of publishing an avoidable blank or predicting a hand.
            self.recovery_attempts += 1
            self._last_ts += 1
            result = self.landmarker.detect_for_video(image, self._last_ts)
            if result.hand_landmarks:
                self.recovery_successes += 1
            else:
                # Do not repeatedly spend extra inference on blur or an empty view.
                self._retry_after_ts = frame_ts + 120
        if not result.hand_landmarks:
            self._wrist = None
            return None
        hands = result.hand_landmarks
        idx = 0
        if self._wrist is not None:
            idx = min(range(len(hands)), key=lambda i: math.hypot(
                hands[i][0].x - self._wrist[0], hands[i][0].y - self._wrist[1]))
        wrist = (hands[idx][0].x, hands[idx][0].y)
        # Single-player swipes may cross much of the frame between valid results.
        # A fixed distance cut-off used to discard exactly those fast cutting paths.
        # Keep the old spatial guard only for optional multi-hand association.
        if (self._wrist is None or not recent or
                (self.num_hands > 1 and math.dist(wrist, self._wrist) > 0.3)):
            self.track_id += 1
        self._wrist = wrist
        self._last_detected_ts = frame_ts
        return {"landmarks": [[float(p.x), float(p.y), float(p.z)] for p in hands[idx]],
                "handedness": result.handedness[idx][0].category_name,
                "track_id": self.track_id}

    def detect(self, frame_bgr, ts_ms):
        hand = self.detect_hand(frame_bgr, ts_ms)
        return tuple(blade_position(hand["landmarks"], self.blade_point_index)) if hand else None

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None
