import test from 'node:test';
import assert from 'node:assert/strict';

test('tracking point selection applies without a second save button', async (t) => {
  const originals = new Map();
  const replace = (name, value) => {
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
  const element = id => {
    if (!elements.has(id)) {
      const listeners = new Map();
      elements.set(id, {
        value: '', textContent: '', style: {}, dataset: {}, tagName: 'INPUT', listeners,
        addEventListener: (event, callback) => listeners.set(event, callback),
        dispatchEvent() {}, removeAttribute() {},
        classList: { contains: () => false, remove() {} },
        parentElement: { style: {}, classList: { remove() {} },
          querySelector: () => ({ querySelector: () => ({}) }) },
      });
    }
    return elements.get(id);
  };
  replace('location', { protocol: 'http:', host: 'unused' });
  replace('document', { getElementById: element, hidden: true });
  replace('WebSocket', class { constructor() { this.readyState = 0; } close() {} });
  let tick;
  t.mock.method(globalThis, 'setInterval', callback => { tick = callback; return 1; });
  const api = { camera_id: 0, target_fps: 30, smooth_alpha: 0.5, blade_point_index: -1,
    activation: 'always', pinch_threshold: 0.4, filter: 'one_euro', min_detection_confidence: 0.35 };
  const posts = [];
  let revision = 0;
  let hold = null;
  let fail = false;
  t.mock.method(globalThis, 'fetch', async (url, options = {}) => {
    assert.equal(url, '/api/settings');
    if (options.method !== 'POST') return { ok: true, json: async () => ({ ...api }) };
    const patch = JSON.parse(options.body);
    posts.push(patch);
    if (hold) await hold;
    if (fail) return { ok: false, json: async () => ({ error: '保存失败' }) };
    Object.assign(api, patch);
    return { ok: true, json: async () => ({ settings: { ...api }, revision: ++revision }) };
  });
  const { gestureClient: client } = await import('../frontend/js/net/client.js');
  const { setupGestureSettings } = await import('../frontend/js/GestureSettings.js');
  t.after(() => client.destroy());
  const settings = setupGestureSettings({
    getOptions: () => ({ mirrorX: true, sensitivity: 1, sensitivityY: 1, offsetX: 0, offsetY: 0 }),
    onOptions() {},
  });
  client.connected = true;
  client._handle({ type: 'status', camera_ok: true, initializing: false, revision: 0,
    applied_revision: 0, settings: { ...api } });
  await settings.open();
  const select = value => {
    element('gesture-point').value = String(value);
    const change = element('gesture-point').listeners.get('change');
    assert.equal(typeof change, 'function', 'selecting a tracking point must submit it immediately');
    return change();
  };

  await t.test('index selection saves only its point and waits for worker acknowledgement', async () => {
    element('gesture-detection').value = '0.25'; // Keep unrelated unsaved controls as drafts.
    await select(8);
    assert.deepEqual(posts.at(-1), { blade_point_index: 8 });
    assert.equal(api.min_detection_confidence, 0.35);
    assert.match(element('gesture-point-status').textContent, /等待.*应用/);
    client._handle({ type: 'gesture', x: 0.3, y: 0.2, visible: true, active: true, revision });
    await tick();
    assert.match(element('gesture-point-status').textContent, /当前追踪：食指指尖/);
  });

  await t.test('rapid selection changes are serialized and the last selection wins', async () => {
    let release;
    hold = new Promise(resolve => { release = resolve; });
    const before = posts.length;
    const first = select(12);
    const last = select(-1);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(posts.length, before + 1, 'only one settings request may be in flight');
    hold = null; release();
    await Promise.all([first, last]);
    assert.deepEqual(posts.slice(before), [{ blade_point_index: 12 }, { blade_point_index: -1 }]);
    assert.equal(api.blade_point_index, -1);
    assert.equal(Number(element('gesture-point').value), -1);
  });

  await t.test('closing immediately keeps the save and reopening waits for its result', async () => {
    let release;
    hold = new Promise(resolve => { release = resolve; });
    const saving = select(12);
    settings.close();
    const reopening = settings.open();
    await new Promise(resolve => setImmediate(resolve));
    hold = null; release();
    await Promise.all([saving, reopening]);
    assert.equal(api.blade_point_index, 12);
    assert.equal(Number(element('gesture-point').value), 12);
  });

  await t.test('failed selection returns to the saved point and can be retried', async () => {
    fail = true;
    await select(8);
    assert.equal(api.blade_point_index, 12);
    assert.equal(Number(element('gesture-point').value), 12);
    assert.match(element('gesture-save-status').textContent, /失败/);
    fail = false;
    await select(8);
    assert.equal(api.blade_point_index, 8);
    assert.equal(element('btn-gesture-apply').disabled, false);
  });
});
