import test from 'node:test';
import assert from 'node:assert/strict';
import { guideGeometry, guideInstructions } from '../frontend/js/HandGuide.js';

test('guide connects the hand in the displayed frame to the current blade, respecting mirror', () => {
  const frame = { x: 0.2, y: 0.4 };
  const live = { x: 0.3, y: 0.6 };
  const rect = { left: 800, top: 124, width: 200, height: 150 };
  const mirrored = guideGeometry(frame, live, { mirrorX: true }, rect, 1000, 600);
  assert.deepEqual(mirrored.hand, { x: 960, y: 184 });
  assert.deepEqual(mirrored.blade, { x: 700, y: 360 });
  const direct = guideGeometry(frame, live, { mirrorX: false }, rect, 1000, 600);
  assert.deepEqual(direct.hand, { x: 840, y: 184 });
  assert.deepEqual(direct.blade, { x: 300, y: 360 });
});

test('calibrated frame shows the actual control range and shares the safe blade edges', () => {
  const options = { mirrorX: true, sensitivity: 2, sensitivityY: 2.5, offsetX: 0.1, offsetY: -0.1 };
  const rect = { left: 0, top: 0, width: 200, height: 150 };
  const result = guideGeometry({ x: 0.65, y: 0.2 }, { x: 0, y: 1 }, options, rect, 1000, 600);
  assert.deepEqual(result.area, { left: 0.35, top: 0.2, width: 0.5, height: 0.4 });
  assert.deepEqual(result.blade, { x: 976, y: 576 });
  assert.equal(result.outside, true);
});

test('instructions explain the actual tracked point, cut gate and direction', () => {
  const defaults = guideInstructions({}, {});
  assert.match(defaults.motion, /手掌整体/);
  assert.match(defaults.cut, /不用.*捏合/);
  assert.match(defaults.direction, /同向/);
  const pinch = guideInstructions({ blade_point_index: 8, activation: 'pinch' }, { mirrorX: false });
  assert.match(pinch.motion, /食指指尖/);
  assert.match(pinch.cut, /捏合/);
  assert.doesNotMatch(pinch.cut, /不用/);
  assert.match(pinch.direction, /左右反向/);
  assert.match(guideInstructions({ blade_point_index: 0, activation: 'index' }, {}).motion, /手腕/);
  assert.match(guideInstructions({ activation: 'index' }, {}).cut, /伸直食指/);
});
