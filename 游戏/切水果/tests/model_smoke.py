"""Offline real-model smoke check: python tests/model_smoke.py [--model-dir DIR]."""
import argparse
import inspect
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediapipe_engine import MediaPipeHandEngine, _valid_model

SAMPLES = (
    "2021-02-01_13-52-49_284.jpg",
    "2021-02-01_13-52-50_378.jpg",
    "2021-02-01_13-52-53_532.jpg",
    "2021-02-01_13-52-55_721.jpg",
    "2021-02-01_13-52-59_987.jpg",
)


def local_model(model_dir):
    """Resolve an existing valid model before constructing any engine."""
    folders = [Path(model_dir)] if model_dir else [
        ROOT / "backend" / "models", Path.home() / ".mediapipe_cache",
    ]
    for folder in folders:
        candidate = folder / "hand_landmarker.task"
        if _valid_model(candidate):
            return candidate.resolve()
    raise FileNotFoundError(
        "No valid local hand_landmarker.task. Place it in backend/models or "
        "~/.mediapipe_cache, or pass --model-dir. This check does not download models."
    )


def small_hand(image):
    height = 96
    width = round(image.shape[1] * height / image.shape[0])
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    x, y = (640 - width) // 2, (480 - height) // 2
    frame[y:y + height, x:x + width] = cv2.resize(
        image, (width, height), interpolation=cv2.INTER_AREA,
    )
    return frame


def detect(model, frame, **options):
    # A fresh VIDEO engine prevents earlier cases from supplying a tracked ROI.
    engine = MediaPipeHandEngine(str(model.parent), **options)
    try:
        result = engine.detect_hand(frame, 0)
    finally:
        engine.close()
    valid = False
    if result is not None:
        points = np.asarray(result.get("landmarks"), dtype=float)
        valid = points.shape == (21, 3) and bool(np.isfinite(points).all())
    return {"detected": result is not None, "valid_21_landmarks": valid}


def run(model):
    positives = []
    negatives = []
    baselines = []
    failures = []
    for name in SAMPLES:
        path = ROOT / "backend" / "handpose_x" / "handpose_datasets" / name
        image = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Cannot decode sample: {path}")
        conditions = {"original": image, "mirror": cv2.flip(image, 1), "small_h96": small_hand(image)}
        for condition, frame in conditions.items():
            result = detect(model, frame)
            passed = result["detected"] and result["valid_21_landmarks"]
            positives.append({"image": name, "condition": condition, **result, "passed": passed})
            if not passed:
                failures.append(f"Positive sample failed: {name}/{condition}")
            if name == SAMPLES[3] and condition in ("mirror", "small_h96"):
                legacy = detect(model, frame, min_detection_confidence=0.5)
                # Baseline successes are allowed if a future model improves.
                # Any old-threshold miss must still be recovered by the defaults.
                baselines.append({
                    "image": name, "condition": condition,
                    "legacy_detection_threshold": 0.5,
                    "legacy_detected": legacy["detected"],
                    "default_detected": result["detected"],
                    "recovered": not legacy["detected"] and passed,
                    "passed": passed,
                })
    rng = np.random.default_rng(20261015)
    frames = {
        "black": np.zeros((480, 640, 3), np.uint8),
        "gray": np.full((480, 640, 3), 128, np.uint8),
        "white": np.full((480, 640, 3), 255, np.uint8),
        "seeded_noise": rng.integers(0, 256, (480, 640, 3), dtype=np.uint8),
    }
    for condition, frame in frames.items():
        result = detect(model, frame)
        passed = not result["detected"]
        negatives.append({"condition": condition, "detected": result["detected"], "passed": passed})
        if not passed:
            failures.append(f"False positive: {condition}")
    default = inspect.signature(MediaPipeHandEngine).parameters["min_detection_confidence"].default
    return {
        "passed": not failures,
        "model": str(model),
        "method": "Fresh VIDEO engine per case; no camera; local model only",
        "default_detection_threshold": default,
        "positive_passed": sum(row["passed"] for row in positives),
        "positive_total": len(positives),
        "negative_passed": sum(row["passed"] for row in negatives),
        "negative_total": len(negatives),
        "legacy_misses_recovered": sum(row["recovered"] for row in baselines),
        "positives": positives,
        "negatives": negatives,
        "legacy_comparison": baselines,
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", help="Directory containing an existing hand_landmarker.task")
    args = parser.parse_args()
    try:
        report = run(local_model(args.model_dir))
    except Exception as exc:
        report = {"passed": False, "failures": [str(exc)]}
    report_path = ROOT / "artifacts" / "model-smoke-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key not in ("positives", "negatives", "legacy_comparison")}
    summary["report"] = str(report_path)
    print(json.dumps(summary, ensure_ascii=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
