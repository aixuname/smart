"""Reproducible synthetic filter comparison; does not claim human latency results."""
import json
import math
from pathlib import Path
import random
import statistics
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_tracking import GestureTracker, DEFAULT_SETTINGS


def run():
    rng = random.Random(42)
    points = []
    for i in range(240):
        t = i / 30
        truth = 0.2 if t < 2 else 0.2 + (t - 2) * 0.6 if t < 3 else 0.8 if t < 5 else max(0.2, 0.8 - (t - 5) * 0.6)
        points.append((t, truth, truth + rng.gauss(0, 0.004)))
    report = {}
    for mode in ("ema", "one_euro"):
        tracker = GestureTracker()
        output = []
        for t, truth, measured in points:
            sample = {"landmarks": [[measured, 0.5, 0] for _ in range(21)], "track_id": 1}
            output.append(tracker.update(sample, {**DEFAULT_SETTINGS, "filter": mode}, t)["x"])
        jitter = statistics.pstdev(output[15:60])
        motion_error = statistics.mean(abs(output[i] - points[i][1]) for i in list(range(66, 90)) + list(range(156, 180)))
        report[mode] = {"rest_jitter_norm": round(jitter, 6), "motion_mae_norm": round(motion_error, 6),
                        "max_output": round(max(output), 6), "min_output": round(min(output), 6)}
    report["method"] = "30Hz; fixed seed 42; Gaussian noise sigma=.004; 240 samples; rest/ramp/hold/reverse"
    return report


if __name__ == "__main__":
    result = run()
    out = Path(__file__).resolve().parents[1] / "artifacts"
    out.mkdir(exist_ok=True)
    (out / "filter-benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
