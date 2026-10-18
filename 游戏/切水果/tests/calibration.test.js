import test from 'node:test';
import assert from 'node:assert/strict';
import { HandCalibration, mappingFromCorners } from '../frontend/js/input/Calibration.js';
import { mapGesture } from '../frontend/js/input/gestureMapping.js';
import { validRanks, storage } from '../frontend/js/core/Storage.js';

test('two-point calibration maps asymmetric comfortable region onto all screen corners', () => {
  const opts = {...mappingFromCorners({x:0.2, y:0.3}, {x:0.8, y:0.7}), mirrorX:false};
  const first = mapGesture({x:0.2, y:0.3}, opts);
  const second = mapGesture({x:0.8, y:0.7}, opts);
  assert.ok(first.x < 1e-8 && first.y < 1e-8);
  assert.ok(second.x > 1 - 1e-8 && second.y > 1 - 1e-8);
  assert.throws(() => mappingFromCorners({x:0.5, y:0.5}, {x:0.4, y:0.8}));
  assert.throws(() => mappingFromCorners({x:NaN, y:0.1}, {x:0.8, y:0.8}));
});

test('calibration requires fresh stable hand samples, and can cancel without modifying mapping', () => {
  const calibration = new HandCalibration();
  calibration.start(0);
  calibration.update({visible:false}, 3600);
  assert.equal(calibration.stage, 0);
  assert.match(calibration.error, /识别/);
  calibration.start(0);
  for (let i = 0; i < 9; i++) calibration.update({x:0.8, y:0.2, visible:true, receivedAt:2700+i*100}, 2700+i*100, true);
  assert.equal(calibration.stage, 2);
  for (let i = 0; i < 9; i++) calibration.update({x:0.2, y:0.8, visible:true, receivedAt:6200+i*100}, 6200+i*100, true);
  assert.equal(calibration.stage, 0);
  assert.ok(calibration.result);
  calibration.start(0);
  calibration.cancel();
  assert.equal(calibration.result, null);
});

test('corrupt leaderboard data is rejected and unavailable storage falls back to session memory', () => {
  assert.equal(validRanks([null, {}, {name:'x', score:NaN, date:1, mode:'timed'}]).length, 0);
  assert.equal(validRanks([{name:'player', score:12.2, date:1, mode:'timed'}])[0].score, 12);
  assert.equal(storage.set('test', 'value'), false);
  assert.equal(storage.get('test'), 'value');
});
