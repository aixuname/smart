import test from 'node:test';
import assert from 'node:assert/strict';
import { GestureClient } from '../frontend/js/net/GestureClient.js';
import { GestureBladeInput } from '../frontend/js/input/GestureBladeInput.js';
import { BladeManager } from '../frontend/js/core/BladeManager.js';
import { Slicer } from '../frontend/js/core/Slicer.js';
import { mapGesture } from '../frontend/js/input/gestureMapping.js';
import { SampleBuffer } from '../frontend/js/input/SampleBuffer.js';
import * as mapping from '../frontend/js/input/gestureMapping.js';

test('default mapping keeps live hand motion near the camera bottom responsive', () => {
  const first = mapGesture({ x: 0.35, y: 0.92 });
  const second = mapGesture({ x: 0.4, y: 0.94 });
  assert.ok(second.y > first.y, 'bottom-of-camera movement must not collapse to a fixed edge');
  assert.ok(first.y < 1 && second.y < 1);
});

test('legacy default mapping upgrades while calibrated ranges remain intact', () => {
  assert.equal(typeof mapping.restoreGestureOptions, 'function');
  assert.deepEqual(mapping.restoreGestureOptions({ sensitivity: 1.4, sensitivityY: 1.4, offsetX: 0, offsetY: 0 }),
    { sensitivity: 1, sensitivityY: 1, offsetX: 0, offsetY: 0 });
  const custom = { sensitivity: 2, sensitivityY: 1.8, offsetX: 0.12, offsetY: -0.1 };
  assert.deepEqual(mapping.restoreGestureOptions(custom), custom);
  const chosen = { sensitivity: 1.4, sensitivityY: 1.4, offsetX: 0, offsetY: 0 };
  assert.deepEqual(mapping.restoreGestureOptions(chosen, 2), chosen);
});

test('edge samples keep the visible blade tip inside the canvas and match collision samples', () => {
  const client = new GestureClient('ws://unused');
  client.connected = true;
  const scene = { scale: { width: 1000, height: 600 } };
  const input = new GestureBladeInput(scene, client, { mirrorX: false, sensitivity: 1 });
  for (const [x, y] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
    client._handle({ type: 'gesture', x, y, visible: true, active: true, stroke_id: 1, revision: 0 });
    const pos = input.getPosition();
    assert.ok(pos.x >= 20 && pos.x <= 980 && pos.y >= 20 && pos.y <= 580,
      'the glowing tip must not be clipped at a screen edge');
    const sample = input.consumeSamples().at(-1);
    assert.equal(pos.x, sample.x);
    assert.equal(pos.y, sample.y);
  }
  input.destroy();
});

test('status uses one consistent naming convention for subscribers', () => {
  const client = new GestureClient('ws://unused');
  let message;
  client.onMessage(m => { message = m; });
  client._handle({ type: 'status', model_missing: true, camera_ok: false, fps: 0 });
  assert.equal(message.modelMissing, true);
  assert.equal(message.cameraOk, false);
});

test('mirror, sensitivity, offset and clamping', () => {
  assert.deepEqual(mapGesture({ x: 0.2, y: 0.4 }, { mirrorX: true, sensitivity: 2, offsetX: 0.1 }), { x: 0.9000000000000001, y: 0.30000000000000004 });
  assert.deepEqual(mapGesture({ x: 0, y: 1 }, { mirrorX: false, sensitivity: 2 }), { x: 0, y: 1 });
});

test('cut gate, stream timeout, reconnect and stroke boundary prevent phantom slices', () => {
  const client = new GestureClient('ws://unused');
  client.connected = true;
  const scene = { scale: { width: 1000, height: 600 } };
  const input = new GestureBladeInput(scene, client, { mirrorX: false, sensitivity: 1 });
  const manager = new BladeManager(scene);
  manager.add(input);
  const send = (x, stroke = 1, active = true) => client._handle({ type: 'gesture', x, y: 0.5, visible: true, active, stroke_id: stroke, revision: 0 });
  send(0.1);
  assert.equal(manager.update().length, 0);
  send(0.9);
  assert.equal(manager.update().length, 1);
  assert.equal(manager.update().length, 0, 'stationary input must not replay an old motion segment');
  send(0.1, 2);
  assert.equal(manager.update().length, 0, 'new stroke must not span the screen');
  send(0.5, 2, false);
  assert.equal(input.isActive(), false);
  assert.ok(input.getPosition(), 'inactive cursor still available');
  const inactiveX = input.getPosition().x;
  send(0.7, 2, false);
  assert.ok(input.getPosition().x > inactiveX, 'hand still moves the blade when optional cutting gate is off');
  input.lastReceived -= 1000;
  assert.equal(input.getPosition(), null);
  send(0.9, 3);
  assert.equal(manager.update().length, 0);
  client.connected = false;
  client._emit({ type: 'disconnected' });
  assert.equal(input.isActive(), false);
  input.destroy();
  assert.equal(client._listeners.size, 0);
});

test('fast swipe intersects fruit without tunnelling and deduplicates hits', () => {
  const fruit = {};
  const segment = { x1: 0, y1: 100, x2: 1000, y2: 100 };
  assert.equal(Slicer.hitTestAll([segment, segment], [{ x: 500, y: 100, r: 20, obj: fruit }]).size, 1);
  assert.equal(Slicer.segHitsCircle(segment, 500, 200, 20), false);
});

test('two turns in one render frame preserve the path rather than cutting the diagonal', () => {
  const client = new GestureClient('ws://unused');
  client.connected = true;
  const scene = { scale: { width: 1000, height: 1000 } };
  const input = new GestureBladeInput(scene, client, { mirrorX: false, sensitivity: 1 });
  const manager = new BladeManager(scene);
  manager.add(input);
  for (const [x, y] of [[0.1, 0.1], [0.1, 0.9], [0.9, 0.9]]) {
    client._handle({type:'gesture', x, y, visible:true, active:true, stroke_id:1, revision:0});
  }
  const segments = manager.update();
  assert.equal(segments.length, 2);
  assert.equal(Slicer.hitTestAll(segments, [{x:500, y:500, r:30, obj:'bomb'}]).size, 0);
  assert.equal(Slicer.hitTestAll(segments, [{x:100, y:500, r:30, obj:'fruit'}]).size, 1);
  input.destroy();
});

test('bounded sample overflow starts a fresh stroke', () => {
  const buffer = new SampleBuffer(2);
  buffer.push({x:0, y:0}, 1);
  const original = buffer.take()[0].strokeId;
  for (let i = 0; i < 3; i++) buffer.push({x:i, y:i}, 1);
  const current = buffer.take();
  assert.equal(current.length, 1);
  assert.notEqual(original, current[0].strokeId);
});
