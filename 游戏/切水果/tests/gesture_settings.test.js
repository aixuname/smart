import test from 'node:test';
import assert from 'node:assert/strict';

test('gesture settings report tracking state and persist recognition sensitivity', async (t) => {
  const originals = new Map();
  const replaceGlobal = (name, value) => {
    originals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
    Object.defineProperty(globalThis, name, { value, configurable: true, writable: true });
  };
  t.after(() => {
    for (const [name, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
  });

  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      value: '', textContent: '', style: {}, dataset: {}, tagName: 'INPUT',
      addEventListener() {}, dispatchEvent() {},
      parentElement: { querySelector: () => ({ querySelector: () => ({}) }) },
    });
    return elements.get(id);
  };
  replaceGlobal('location', { protocol: 'http:', host: 'unused' });
  replaceGlobal('document', { getElementById: element, hidden: true });
  replaceGlobal('WebSocket', class {
    constructor() { this.readyState = 0; }
    close() { this.readyState = 3; }
  });
  let tick;
  t.mock.method(globalThis, 'setInterval', (callback) => { tick = callback; return 1; });
  t.mock.method(performance, 'now', () => 1000);
  const apiSettings = { camera_id: 0, target_fps: 30, smooth_alpha: 0.5,
    blade_point_index: -1, activation: 'always', pinch_threshold: 0.4, filter: 'one_euro' };
  const savedSettings = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/settings');
    if (options.method === 'POST') {
      const patch = JSON.parse(options.body);
      savedSettings.push(patch);
      Object.assign(apiSettings, patch);
      return { ok: true, json: async () => ({ settings: apiSettings, revision: savedSettings.length }) };
    }
    return { ok: true, json: async () => apiSettings };
  });
  const { gestureClient: client } = await import('../frontend/js/net/client.js');
  const { setupGestureSettings } = await import('../frontend/js/GestureSettings.js');
  t.after(() => client.destroy());
  const settings = setupGestureSettings({
    getOptions: () => ({ mirrorX: true, sensitivity: 1.4, sensitivityY: 1.4, offsetX: 0, offsetY: 0 }),
    onOptions() {},
  });
  client.connected = true;
  client._handle({ type: 'status', camera_ok: true, initializing: false, model_missing: false, fps: 2 });
  await settings.open();

  await t.test('older settings default recognition sensitivity to 0.35', () => {
    assert.equal(Number(element('gesture-detection').value), 0.35);
  });
  await t.test('applying recognition sensitivity sends the selected numeric threshold', async () => {
    element('gesture-detection').value = '0.25';
    await element('btn-gesture-apply').onclick();
    assert.equal(savedSettings.length, 1);
    assert.equal(savedSettings[0].min_detection_confidence, 0.25);
    assert.equal(savedSettings[0].activation, 'always');
  });
  await t.test('reopening settings restores the saved recognition sensitivity', async () => {
    apiSettings.min_detection_confidence = 0.5;
    await settings.open();
    assert.equal(Number(element('gesture-detection').value), 0.5);
  });
  await t.test('400ms-old visible hand is reported as awaiting coordinates', async () => {
    client.lastGesture = { x: 0.5, y: 0.5, visible: true, active: true, receivedAt: 600 };
    await tick();
    assert.match(element('gesture-diagnostic').textContent, /暂未收到新的手部坐标/);
    assert.doesNotMatch(element('gesture-diagnostic').textContent, /未发现手部/);
  });
  await t.test('fresh missing-hand message is reported as no hand', async () => {
    client._handle({ type: 'gesture', x: 0, y: 0, visible: false, active: false });
    await tick();
    assert.match(element('gesture-diagnostic').textContent, /未发现手部/);
  });
  await t.test('fresh recognized hand retains the cutting status', async () => {
    client._handle({ type: 'gesture', x: 0.5, y: 0.5, visible: true, active: true });
    await tick();
    assert.match(element('gesture-diagnostic').textContent, /出刀中/);
  });
  await t.test('backend errors take priority over stale coordinates', async () => {
    const error = '识别失败: model unavailable';
    client._handle({ type: 'status', camera_ok: true, initializing: false, error });
    client.lastGesture.receivedAt = 500;
    await tick();
    assert.equal(element('gesture-diagnostic').textContent, error);
    assert.equal(element('gesture-diagnostic').dataset.state, 'waiting');
  });
});
