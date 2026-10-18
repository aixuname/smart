"""Bounded real-image re-detection and stroke continuity during a fast swipe."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from mediapipe_engine import MediaPipeHandEngine
from gesture_tracking import DEFAULT_SETTINGS, GestureTracker


def result(x=None):
    if x is None:
        return SimpleNamespace(hand_landmarks=[], handedness=[])
    return SimpleNamespace(
        hand_landmarks=[[SimpleNamespace(x=x, y=0.5, z=0) for _ in range(21)]],
        handedness=[[SimpleNamespace(category_name='Right')]])


class FastRecoveryTests(unittest.TestCase):
    def engine(self, results, **options):
        native = Mock()
        native.detect_for_video.side_effect = results
        with patch('mediapipe_engine.ensure_model', return_value='local.task'), patch(
                'mediapipe_engine.Path.read_bytes', return_value=b'test model'), patch(
                'mediapipe_engine.vision.HandLandmarker.create_from_options', return_value=native):
            engine = MediaPipeHandEngine('unused', **options)
        self.addCleanup(engine.close)
        return engine, native

    def setUp(self):
        self.frame = np.zeros((32, 32, 3), np.uint8)

    def test_tracked_hand_is_recovered_from_same_image_before_publishing_a_miss(self):
        engine, native = self.engine([result(0.2), result(), result(0.4), result(0.5)])
        first = engine.detect_hand(self.frame, 100)
        recovered = engine.detect_hand(self.frame, 133)
        self.assertIsNotNone(recovered, 're-detect the current frame before making the blade disappear')
        self.assertEqual(recovered['track_id'], first['track_id'])
        engine.detect_hand(self.frame, 133)  # Repeated source timestamp still stays strictly monotonic.
        calls = native.detect_for_video.call_args_list
        self.assertEqual([c.args[1] for c in calls], [100, 133, 134, 135])
        self.assertIs(calls[1].args[0], calls[2].args[0], 'retry must use the actual current image')
        self.assertEqual(engine.recovery_attempts, 1)
        self.assertEqual(engine.recovery_successes, 1)

    def test_successful_recovery_does_not_throttle_the_next_fast_swing(self):
        engine, native = self.engine([result(0.2), result(), result(0.4), result(), result(0.6)])
        for ts in (100, 133, 166):
            self.assertIsNotNone(engine.detect_hand(self.frame, ts))
        self.assertEqual(native.detect_for_video.call_count, 5)

    def test_failed_retry_stops_cutting_and_sustained_blank_does_not_repeat_work(self):
        engine, native = self.engine([result(0.2), result(), result(), result(), result(), result(0.6)])
        tracker = GestureTracker()
        first = tracker.update(engine.detect_hand(self.frame, 100), DEFAULT_SETTINGS, 0.1)
        missing = tracker.update(engine.detect_hand(self.frame, 133), DEFAULT_SETTINGS, 0.133)
        self.assertFalse(missing['visible'])
        self.assertFalse(missing['active'])
        self.assertIsNone(engine.detect_hand(self.frame, 166))
        self.assertIsNone(engine.detect_hand(self.frame, 200))
        restored = tracker.update(engine.detect_hand(self.frame, 233), DEFAULT_SETTINGS, 0.233)
        self.assertGreater(restored['stroke_id'], first['stroke_id'])
        self.assertEqual(native.detect_for_video.call_count, 6)
        self.assertEqual(engine.recovery_attempts, 1)

    def test_failure_cooldown_and_stale_tracking_skip_extra_detection(self):
        engine, native = self.engine([result(0.2), result(), result(), result(0.3), result(), result(0.4), result()])
        engine.detect_hand(self.frame, 100)
        self.assertIsNone(engine.detect_hand(self.frame, 133))
        self.assertIsNotNone(engine.detect_hand(self.frame, 166))
        self.assertIsNone(engine.detect_hand(self.frame, 200), 'failed retry cools down for 120ms')
        self.assertIsNotNone(engine.detect_hand(self.frame, 266))
        self.assertIsNone(engine.detect_hand(self.frame, 600), 'an old hand does not qualify for immediate retry')
        self.assertEqual(native.detect_for_video.call_count, 7)

    def test_initial_empty_frame_gets_one_pass_and_never_returns_old_coordinates(self):
        engine, native = self.engine([result(), result(), result()])
        for ts in (100, 133, 166):
            self.assertIsNone(engine.detect_hand(self.frame, ts))
        self.assertEqual(native.detect_for_video.call_count, 3)

    def test_continuous_large_motion_keeps_stroke_but_long_gap_breaks_it(self):
        engine, _ = self.engine([result(0.1), result(0.7), result(0.2)])
        tracker = GestureTracker()
        first = tracker.update(engine.detect_hand(self.frame, 100), DEFAULT_SETTINGS, 0.1)
        fast = tracker.update(engine.detect_hand(self.frame, 133), DEFAULT_SETTINGS, 0.133)
        self.assertEqual(fast['stroke_id'], first['stroke_id'], 'a fast valid swipe is still the same stroke')
        self.assertGreater(fast['x'], first['x'])
        resumed = tracker.update(engine.detect_hand(self.frame, 500), DEFAULT_SETTINGS, 0.5)
        self.assertGreater(resumed['stroke_id'], fast['stroke_id'], 'do not bridge a long capture gap')

    def test_recovery_can_be_disabled_for_an_identical_sequence_comparison(self):
        engine, native = self.engine([result(0.2), result()], recover_fast_motion=False)
        engine.detect_hand(self.frame, 100)
        self.assertIsNone(engine.detect_hand(self.frame, 133))
        self.assertEqual(native.detect_for_video.call_count, 2)
        self.assertEqual(engine.recovery_attempts, 0)

    def test_optional_multi_hand_mode_retains_identity_jump_guard(self):
        engine, _ = self.engine([result(0.1), result(0.7)], num_hands=2)
        first = engine.detect_hand(self.frame, 100)
        switched = engine.detect_hand(self.frame, 133)
        self.assertGreater(switched['track_id'], first['track_id'])


if __name__ == '__main__':
    unittest.main()
