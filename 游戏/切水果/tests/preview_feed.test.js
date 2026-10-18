import test from 'node:test';
import assert from 'node:assert/strict';
import { PreviewFeed } from '../frontend/js/net/PreviewFeed.js';

const flush = () => new Promise(setImmediate);
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function harness(t, options = {}) {
  let now = 0, nextTimer = 0, nextUrl = 0;
  const timers = new Map(), requests = [], decodes = [], states = [], frames = [], revoked = [];
  const image = {
    src: '',
    removeAttribute(name) { if (name === 'src') this.src = ''; },
    decode() {
      const pending = deferred();
      decodes.push(pending);
      return pending.promise;
    },
  };
  t.mock.method(globalThis, 'setTimeout', (callback, delay) => {
    const id = ++nextTimer;
    timers.set(id, { callback, due: now + delay });
    return id;
  });
  t.mock.method(globalThis, 'clearTimeout', (id) => timers.delete(id));
  t.mock.method(globalThis, 'fetch', (url, init) => {
    const pending = deferred();
    requests.push({ url, init, ...pending });
    // Deliberately allow late responses after abort to exercise stale work guards.
    return pending.promise;
  });
  t.mock.method(URL, 'createObjectURL', () => `blob:preview-${++nextUrl}`);
  t.mock.method(URL, 'revokeObjectURL', (url) => revoked.push(url));
  const feed = new PreviewFeed(image, { ...options, onState: (ready, gesture) => {
    states.push(ready);
    frames.push({ ready, gesture });
  } });
  t.after(() => feed.destroy());
  async function tick(ms) {
    const end = now + ms;
    while (true) {
      const next = [...timers].filter(([, timer]) => timer.due <= end)
        .sort((a, b) => a[1].due - b[1].due)[0];
      if (!next) break;
      const [id, timer] = next;
      timers.delete(id);
      now = timer.due;
      timer.callback();
      await flush();
    }
    now = end;
    await flush();
  }
  async function respond(index, { ok = true, blob = new Blob(['jpeg']), gesture } = {}) {
    const headers = new Headers(gesture === undefined ? {} : { 'X-Preview-Gesture': gesture });
    requests[index].resolve({ ok, headers, blob: async () => blob });
    await flush();
  }
  return { feed, image, requests, decodes, states, frames, revoked, timers, tick, respond };
}

test('preview fetches only when active and reports ready only after image decoding', async (t) => {
  const h = harness(t);
  await h.tick(500);
  assert.equal(h.requests.length, 0);
  h.feed.setActive(true);
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].url, '/api/preview.jpg');
  assert.equal(h.requests[0].init.cache, 'no-store');
  assert.ok(h.requests[0].init.signal instanceof AbortSignal);
  await h.respond(0);
  assert.equal(h.image.src, 'blob:preview-1');
  assert.equal(h.states.includes(true), false);
  h.decodes[0].resolve();
  await flush();
  assert.equal(h.states.at(-1), true);
});

test('slow preview work stays serialized and polls again after the configured interval', async (t) => {
  const h = harness(t, { interval: 250 });
  h.feed.setActive(true);
  h.feed.setActive(true);
  await h.tick(900);
  assert.equal(h.requests.length, 1);
  await h.respond(0);
  await h.tick(500);
  assert.equal(h.requests.length, 1);
  h.decodes[0].resolve();
  await flush();
  await h.tick(249);
  assert.equal(h.requests.length, 1);
  await h.tick(1);
  assert.equal(h.requests.length, 2);
  await h.respond(1);
  h.decodes[1].resolve();
  await flush();
  assert.equal(h.image.src, 'blob:preview-2');
  assert.deepEqual(h.revoked, ['blob:preview-1']);
});

test('stopping aborts a pending fetch and a late response cannot restore the image', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  h.feed.setActive(false);
  assert.equal(h.requests[0].init.signal.aborted, true);
  assert.equal(h.image.src, '');
  assert.equal(h.states.at(-1), false);
  assert.equal(h.timers.size, 0);
  await h.respond(0);
  await h.tick(5000);
  assert.equal(h.image.src, '');
  assert.equal(h.requests.length, 1);
  assert.equal(h.states.includes(true), false);
});

test('restarting during decoding isolates the old session from the new image and polling', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  await h.respond(0, { gesture: '{"x":0.1,"y":0.2,"seq":1}' });
  h.feed.setActive(false);
  assert.deepEqual(h.revoked, ['blob:preview-1']);
  h.feed.setActive(true);
  await h.respond(1, { gesture: '{"x":0.8,"y":0.4,"seq":2}' });
  h.decodes[1].resolve();
  await flush();
  const states = [...h.states];
  const frames = [...h.frames];
  assert.deepEqual(h.frames.at(-1), { ready: true, gesture: { x: 0.8, y: 0.4, seq: 2 } });
  h.decodes[0].resolve();
  await flush();
  assert.equal(h.image.src, 'blob:preview-2');
  assert.deepEqual(h.states, states);
  assert.deepEqual(h.frames, frames);
  await h.tick(150);
  assert.equal(h.requests.length, 3);
  assert.equal(h.requests[2].init.signal.aborted, false);
});

test('gesture metadata changes only when its matching preview image has decoded', async (t) => {
  const h = harness(t);
  const first = { x: 0.15, y: 0.7, visible: true, active: true, seq: 10, revision: 1 };
  const second = { x: 0.75, y: 0.3, visible: true, active: false, seq: 11, revision: 2 };
  h.feed.setActive(true);
  await h.respond(0, { gesture: JSON.stringify(first) });
  assert.equal(h.frames.length, 0);
  h.decodes[0].resolve();
  await flush();
  assert.deepEqual(h.frames.at(-1), { ready: true, gesture: first });
  await h.tick(150);
  await h.respond(1, { gesture: JSON.stringify(second) });
  assert.deepEqual(h.frames.at(-1), { ready: true, gesture: first });
  h.decodes[1].resolve();
  await flush();
  assert.deepEqual(h.frames.at(-1), { ready: true, gesture: second });
  h.feed.setActive(false);
  assert.deepEqual(h.frames.at(-1), { ready: false, gesture: null });
});

test('missing or malformed preview metadata leaves a decoded image usable without a marker', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  for (const [index, gesture] of [undefined, '{invalid', 'null'].entries()) {
    await h.respond(index, { gesture });
    h.decodes[index].resolve();
    await flush();
    assert.deepEqual(h.frames.at(-1), { ready: true, gesture: null });
    assert.ok(h.image.src.startsWith('blob:'));
    await h.tick(150);
  }
  h.requests[3].reject(new Error('offline'));
  await flush();
  assert.deepEqual(h.frames.at(-1), { ready: false, gesture: null });
});

test('a stalled request times out at two seconds and later responses cannot replace a retry', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  await h.tick(1999);
  assert.equal(h.requests[0].init.signal.aborted, false);
  await h.tick(1);
  assert.equal(h.requests[0].init.signal.aborted, true);
  assert.equal(h.states.at(-1), false);
  await h.tick(150);
  assert.equal(h.requests.length, 2);
  await h.respond(1);
  h.decodes[0].resolve();
  await flush();
  await h.respond(0);
  assert.equal(h.image.src, 'blob:preview-1');
  assert.equal(h.states.at(-1), true);
  assert.equal(h.decodes.length, 1);
});

test('a stalled image decode also times out and releases its object URL', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  await h.respond(0);
  await h.tick(2000);
  assert.equal(h.image.src, '');
  assert.equal(h.states.at(-1), false);
  assert.deepEqual(h.revoked, ['blob:preview-1']);
  await h.tick(150);
  assert.equal(h.requests.length, 2);
  h.decodes[0].resolve();
  await flush();
  assert.equal(h.states.includes(true), false);
});

test('HTTP and decode failures report unavailable, release images, and keep retrying', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  await h.respond(0, { ok: false });
  assert.equal(h.states.at(-1), false);
  assert.equal(h.image.src, '');
  await h.tick(150);
  await h.respond(1);
  h.decodes[0].reject(new Error('invalid image'));
  await flush();
  assert.equal(h.states.at(-1), false);
  assert.equal(h.image.src, '');
  assert.deepEqual(h.revoked, ['blob:preview-1']);
  await h.tick(150);
  await h.respond(2);
  h.decodes[1].resolve();
  await flush();
  assert.equal(h.states.at(-1), true);
});

test('destroy clears the visible image and scheduled poll and cannot be reactivated', async (t) => {
  const h = harness(t);
  h.feed.setActive(true);
  await h.respond(0);
  h.decodes[0].resolve();
  await flush();
  h.feed.destroy();
  h.feed.destroy();
  h.feed.setActive(true);
  assert.equal(h.image.src, '');
  assert.equal(h.states.at(-1), false);
  assert.deepEqual(h.revoked, ['blob:preview-1']);
  assert.equal(h.timers.size, 0);
  await h.tick(5000);
  assert.equal(h.requests.length, 1);
});
