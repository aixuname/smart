"""Pure gesture interpretation and stroke continuity (no camera required)."""
import math
from motion_filter import OneEuroFilter

PALM_POINT_INDEX = -1
PALM_LANDMARKS = (0, 5, 9, 13, 17)


def blade_position(points, point_index=PALM_POINT_INDEX):
    """Palm anchor excludes fingertips so finger flex does not move the blade."""
    if point_index == PALM_POINT_INDEX:
        return [sum(points[i][axis] for i in PALM_LANDMARKS) / len(PALM_LANDMARKS)
                for axis in (0, 1)]
    return list(points[point_index][:2])

DEFAULT_SETTINGS = {
    "camera_id": 0, "target_fps": 30, "smooth_alpha": 0.5,
    "blade_point_index": PALM_POINT_INDEX, "activation": "always", "pinch_threshold": 0.4,
    "filter": "one_euro", "min_detection_confidence": 0.35,
}


def validate_settings(patch, base=None):
    if not isinstance(patch, dict):
        raise ValueError("设置必须是 JSON 对象")
    result = dict(base or DEFAULT_SETTINGS)
    ranges = {"camera_id": (0, 20, int), "target_fps": (10, 60, int),
              "smooth_alpha": (0.1, 1.0, float), "blade_point_index": (-1, 20, int),
              "pinch_threshold": (0.15, 0.8, float),
              "min_detection_confidence": (0.2, 0.8, float)}
    for key, value in patch.items():
        if key == "filter":
            if value not in ("one_euro", "ema"):
                raise ValueError("未知平滑算法")
        elif key == "activation":
            if value not in ("always", "index", "pinch"):
                raise ValueError("未知出刀方式")
        elif key in ranges:
            low, high, kind = ranges[key]
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                    not math.isfinite(value) or not low <= value <= high or
                    (kind is int and int(value) != value)):
                raise ValueError("%s 必须在 %s ~ %s 范围内" % (key, low, high))
            value = kind(value)
        else:
            raise ValueError("未知设置: " + str(key))
        result[key] = value
    return result


class GestureTracker:
    def __init__(self):
        self.stroke_id = 0
        self.reset()

    def reset(self):
        self.filter = OneEuroFilter()
        self.smooth = None
        self.last_seen = None
        self.was_active = False
        self.pinched = False
        self.track_id = None
        self.stroke_id += 1

    def update(self, hand, settings, now, aspect=4 / 3):
        if hand is None:
            self.was_active = False
            self.pinched = False
            self.smooth = None
            self.filter.reset()
            return {"x": 0, "y": 0, "visible": False, "active": False,
                    "stroke_id": self.stroke_id, "landmarks": [], "gesture": "none"}
        points = hand["landmarks"]
        if len(points) != 21 or any(not math.isfinite(v) for p in points for v in p):
            return self.update(None, settings, now, aspect)
        if hand.get("track_id") != self.track_id:
            self.reset()
            self.track_id = hand.get("track_id")
        def distance(a, b):
            return math.sqrt(((a[0] - b[0]) * aspect) ** 2 + (a[1] - b[1]) ** 2)
        palm = max(distance(points[0], points[9]), distance(points[5], points[17]), 0.001)
        ratio = distance(points[4], points[8]) / palm
        threshold = settings["pinch_threshold"] + (0.12 if self.pinched else 0)
        self.pinched = ratio < threshold
        a, b, c = points[5], points[6], points[8]
        u = ((a[0] - b[0]) * aspect, a[1] - b[1])
        v = ((c[0] - b[0]) * aspect, c[1] - b[1])
        cosine = sum(x * y for x, y in zip(u, v)) / max(math.hypot(*u) * math.hypot(*v), 1e-8)
        extended = cosine < -0.55 and distance(points[8], points[0]) > distance(points[6], points[0]) * 1.12
        mode = settings["activation"]
        active = mode == "always" or (mode == "pinch" and self.pinched) or (mode == "index" and extended)
        pos = [min(1.0, max(0.0, v)) for v in blade_position(points, settings["blade_point_index"])]
        if active and not self.was_active:
            self.stroke_id += 1
            # Opening the cut gate changes stroke continuity, never cursor position.
        if settings.get("filter", "one_euro") == "one_euro":
            self.smooth = self.filter.update(pos, now, settings["smooth_alpha"])
        elif self.smooth is None:
            self.smooth = pos
        else:
            dt = min(0.1, max(0.001, now - (self.last_seen or now)))
            alpha = 1 - (1 - settings["smooth_alpha"]) ** (dt * 30)
            alpha = max(alpha, min(0.9, math.dist(pos, self.smooth) * 4))
            self.smooth = [alpha * p + (1 - alpha) * s for p, s in zip(pos, self.smooth)]
        self.last_seen = now
        self.was_active = active
        return {"x": self.smooth[0], "y": self.smooth[1], "visible": True,
                "active": active, "stroke_id": self.stroke_id, "landmarks": points,
                "gesture": "pinch" if self.pinched else "index" if extended else "hand",
                "handedness": hand.get("handedness", ""), "pinch_ratio": round(ratio, 3)}
