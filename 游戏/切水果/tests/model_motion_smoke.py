"""Offline real-model motion regression: python tests/model_motion_smoke.py.

Uses an existing project hand photo and local model; never opens a camera or
downloads anything. Synthetic blur is reported as a limitation, not a success
target. Inference timing is diagnostic and has no machine-dependent pass limit.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediapipe_engine import MediaPipeHandEngine
from model_smoke import local_model

FAST_SEGMENTS = ("fast_jump", "zigzag")


def motion_frames():
    path = ROOT / "backend/handpose_x/handpose_datasets/2021-02-01_13-52-53_532.jpg"
    photo = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    if photo is None:
        raise ValueError(f"Cannot decode sample: {path}")
    photo = cv2.resize(photo, (150, 270))
    specs = [("warmup", 230, 100, 0)] * 5
    specs += [("ordinary_motion", x, 100, 0) for x in range(200, 341, 20)]
    specs += [("fast_jump", x, 100, 0) for _ in range(5)
              for x in (30, 30, 30, 440, 440, 440)]
    specs += [("zigzag", x, y, 0) for _ in range(3)
              for x, y in ((40, 15), (155, 70), (270, 125), (390, 195), (270, 125), (155, 70))]
    specs += [("short_blank", None, 0, 0)] * 3
    specs += [("reacquire", 80, 100, 0)] * 5
    specs += [("blur15", x, 100, 15) for _ in range(2)
              for x in (50, 160, 270, 380, 270, 160)]
    specs += [("blur31", x, 100, 31) for _ in range(2)
              for x in (50, 160, 270, 380, 270, 160)]
    specs += [("final_blank", None, 0, 0)] * 5
    specs += [("final_reacquire", 230, 100, 0)] * 4
    frames = []
    for index, (segment, x, y, blur) in enumerate(specs):
        frame = np.full((480, 640, 3), 75, dtype=np.uint8)
        if x is not None:
            frame[y:y + 270, x:x + 150] = photo
            if blur:
                kernel = np.zeros((blur, blur), np.float32)
                kernel[blur // 2] = 1 / blur
                frame = cv2.filter2D(frame, -1, kernel)
        frames.append((segment, x is not None, index * 33, frame))
    return frames


def summarize(rows):
    detected = [row for row in rows if row["detected"]]
    return {
        "frames": len(rows),
        "positive_frames": sum(row["positive"] for row in rows),
        "misses": sum(row["positive"] and not row["detected"] for row in rows),
        "negative_frames": sum(not row["positive"] for row in rows),
        "false_positives": sum(not row["positive"] and row["detected"] for row in rows),
        "valid_landmark_frames": sum(row["valid_landmarks"] for row in detected),
        "detected_frames": len(detected),
        "recovery_attempts": sum(row["recovery_attempts"] for row in rows),
        "recovery_successes": sum(row["recovery_successes"] for row in rows),
        "p50_ms": round(float(np.percentile([row["inference_ms"] for row in rows], 50)), 2),
        "p95_ms": round(float(np.percentile([row["inference_ms"] for row in rows], 95)), 2),
    }


def run_variant(model, frames, optimized):
    engine = MediaPipeHandEngine(str(model.parent), recover_fast_motion=optimized)
    rows = []
    last_track = None
    lost = False
    gap_resets = []
    continuous_fast_tracks = []
    try:
        for index, (segment, positive, timestamp, frame) in enumerate(frames):
            before_attempts = engine.recovery_attempts
            before_successes = engine.recovery_successes
            started = time.perf_counter()
            hand = engine.detect_hand(frame, timestamp)
            elapsed = (time.perf_counter() - started) * 1000
            valid = False
            if hand is not None:
                points = np.asarray(hand.get("landmarks"), dtype=float)
                valid = points.shape == (21, 3) and bool(np.isfinite(points).all())
                if lost and last_track is not None:
                    gap_resets.append({"frame": index, "previous_track": last_track,
                                       "new_track": hand["track_id"],
                                       "passed": hand["track_id"] != last_track})
                elif last_track is not None and segment in FAST_SEGMENTS:
                    continuous_fast_tracks.append(hand["track_id"] == last_track)
                last_track = hand["track_id"]
                lost = False
            else:
                lost = True
            rows.append({
                "frame": index, "segment": segment, "timestamp_ms": timestamp,
                "positive": positive, "detected": hand is not None,
                "valid_landmarks": valid, "track_id": hand["track_id"] if hand else None,
                "recovery_attempts": engine.recovery_attempts - before_attempts,
                "recovery_successes": engine.recovery_successes - before_successes,
                "inference_ms": round(elapsed, 3),
            })
    finally:
        engine.close()
    return {
        "recover_fast_motion": optimized,
        **summarize(rows),
        "fast_motion": summarize([row for row in rows if row["segment"] in FAST_SEGMENTS]),
        "segments": {segment: summarize([row for row in rows if row["segment"] == segment])
                     for segment in dict.fromkeys(row["segment"] for row in rows)},
        "loss_reacquisition_track_checks": gap_resets,
        "continuous_fast_track_checks": len(continuous_fast_tracks),
        "continuous_fast_track_failures": continuous_fast_tracks.count(False),
        "frame_results": rows,
    }


def run(model):
    frames = motion_frames()
    baseline = run_variant(model, frames, optimized=False)
    optimized = run_variant(model, frames, optimized=True)
    failures = []
    if optimized["fast_motion"]["misses"] >= baseline["fast_motion"]["misses"]:
        failures.append("Same-frame recovery must strictly reduce fast-motion misses")
    if not optimized["recovery_successes"]:
        failures.append("Expected at least one recovery from a genuine first-pass miss")
    for name, result in (("baseline", baseline), ("optimized", optimized)):
        if result["false_positives"]:
            failures.append(f"{name}: blank frames produced a hand")
        if result["valid_landmark_frames"] != result["detected_frames"]:
            failures.append(f"{name}: a detection did not contain 21 finite landmarks")
        checks = result["loss_reacquisition_track_checks"]
        if not checks or not all(check["passed"] for check in checks):
            failures.append(f"{name}: reacquisition after a real miss must start a new track")
        for segment in ("reacquire", "final_reacquire"):
            if not result["segments"][segment]["detected_frames"]:
                failures.append(f"{name}: no hand recovered after {segment}")
    if not optimized["continuous_fast_track_checks"] or optimized["continuous_fast_track_failures"]:
        failures.append("Valid consecutive fast positions must keep one continuous track")
    return {
        "passed": not failures,
        "method": "Same synthetic project-photo sequence, fresh VIDEO engine per variant, 33ms frame timestamps; no camera or network",
        "model": str(model),
        "limitation": "Synthetic motion blur is measured separately; these counts are not live-camera accuracy",
        "baseline": baseline, "optimized": optimized, "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", help="Directory containing an existing hand_landmarker.task")
    args = parser.parse_args()
    try:
        report = run(local_model(args.model_dir))
    except Exception as exc:
        report = {"passed": False, "failures": [str(exc)]}
    output = ROOT / "artifacts/model-motion-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key not in ("baseline", "optimized")}
    for variant in ("baseline", "optimized"):
        if variant in report:
            summary[variant] = {key: value for key, value in report[variant].items()
                                if key not in ("frame_results", "loss_reacquisition_track_checks")}
    summary["report"] = str(output)
    print(json.dumps(summary, ensure_ascii=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
