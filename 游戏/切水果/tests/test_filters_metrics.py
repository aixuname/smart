from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from motion_filter import OneEuroFilter
from metrics import PipelineMetrics
from benchmark_filters import run


class FilterTests(unittest.TestCase):
    def test_reset_after_gap_has_no_drag_from_old_position(self):
        filter = OneEuroFilter()
        filter.update([0.1, 0.5], 0)
        self.assertEqual(filter.update([0.9, 0.5], 1), [0.9, 0.5])

    def test_no_overshoot_on_stop_at_different_frame_rates(self):
        for fps in (15, 30, 60):
            filter = OneEuroFilter()
            previous = 0.2
            filter.update([previous, 0.5], 0)
            for frame in range(1, fps * 2):
                x = filter.update([0.8, 0.5], frame / fps)[0]
                self.assertGreaterEqual(x, previous)
                self.assertLessEqual(x, 0.8)
                previous = x
            self.assertAlmostEqual(previous, 0.8, delta=0.001)

    def test_repeatable_trace_improves_rest_and_motion_metrics(self):
        result = run()
        self.assertLess(result["one_euro"]["rest_jitter_norm"], result["ema"]["rest_jitter_norm"])
        self.assertLess(result["one_euro"]["motion_mae_norm"], result["ema"]["motion_mae_norm"])

    def test_metrics_window_is_bounded_and_ignores_invalid_samples(self):
        metrics = PipelineMetrics(window=10)
        for i in range(100): metrics.record("inference", i)
        metrics.record("inference", float("nan"))
        metrics.record("inference", -1)
        snapshot = metrics.snapshot()["stages_ms"]["inference"]
        self.assertEqual(snapshot, {"p50": 94, "p95": 99, "samples": 10})
