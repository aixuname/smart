// Read-only production-code probes. Run: node artifacts/audit_frontend_probe.mjs
// Browser services, rendering, audio and WebSocket transport are inert stubs.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';

globalThis.window = { Phaser: { Scene: class {}, Math: { Between: (a) => a } } };
globalThis.location = { protocol: 'http:', host: 'unused.invalid' };
globalThis.WebSocket = class { constructor() { this.readyState = 0; } close() {} };
const { GameScene } = await import('../frontend/js/scenes/GameScene.js');
const { FruitSpawner } = await import('../frontend/js/core/FruitSpawner.js');
const { Effects } = await import('../frontend/js/effects/Effects.js');
const { GestureClient } = await import('../frontend/js/net/GestureClient.js');
const { GestureBladeInput } = await import('../frontend/js/input/GestureBladeInput.js');
const { BladeManager } = await import('../frontend/js/core/BladeManager.js');
const { Slicer } = await import('../frontend/js/core/Slicer.js');
Effects.scorePopup = () => {};

function makeFruit(x, y, vy = 0) {
  const data = { sliced: false, isBomb: false };
  return {
    x, y, active: true, body: { velocity: { x: 0, y: vy } },
    getData(key) { return data[key]; },
    setData(key, value) { data[key] = value; return this; },
    setVelocity(vx, vy) { this.body.velocity = { x: vx, y: vy }; return this; },
    setAngularVelocity() { return this; },
    disableBody() { this.active = false; return this; },
  };
}

function makeScene(fruit, width = 320, height = 844) {
  const scene = Object.create(GameScene.prototype);
  Object.assign(scene, {
    scale: { width, height }, score: 20, mode: 'timed', elapsed: 0,
    over: false, waitingForInput: false, startTime: 1,
    bladeManager: { update: () => [] }, combo: { checkBreak: () => false },
    _emitTrails() {}, _checkSlices() {}, _updateHUD() {},
  });
  const spawner = Object.create(FruitSpawner.prototype);
  Object.assign(spawner, {
    scene, worldW: width, worldH: height, lastSpawn: 0, nextInterval: Infinity,
    group: { children: { iterate: (fn) => fn(fruit) } },
  });
  scene.spawner = spawner;
  return scene;
}

function runSingleFrame(yOffset, offX = false) {
  const fruit = makeFruit(offX ? 481 : 160, 844 + yOffset, 1200);
  const scene = makeScene(fruit);
  scene.update(1000, 16.67);
  return { fruitBefore: { x: offX ? 481 : 160, y: 844 + yOffset },
    scoreAfter: scene.score, activeAfter: fruit.active };
}

const normalBottom = runSingleFrame(40);
const skippedBottom = runSingleFrame(121);
const sideExit = runSingleFrame(-100, true);
assert.equal(normalBottom.scoreAfter, 15);
assert.equal(skippedBottom.scoreAfter, 20);
assert.equal(sideExit.scoreAfter, 20);
assert.equal(skippedBottom.activeAfter, false);
assert.equal(sideExit.activeAfter, false);

// Same semi-implicit 60 Hz kinematics as the default Arcade gravity step.
// Initial values are inside _spawnOne's documented actual random ranges.
function simulate(width, height, xOffset, vx, heightFraction) {
  const fruit = makeFruit(width / 2 + xOffset, height + 8,
    -Math.sqrt(2 * 1400 * height * heightFraction));
  fruit.body.velocity.x = vx;
  const scene = makeScene(fruit, width, height);
  let frame = 0;
  let beforeRelease;
  while (fruit.active && frame < 300) {
    frame++;
    fruit.body.velocity.y += 1400 / 60;
    fruit.x += fruit.body.velocity.x / 60;
    fruit.y += fruit.body.velocity.y / 60;
    beforeRelease = { x: fruit.x, y: fruit.y, vy: fruit.body.velocity.y };
    scene.update(frame * 1000 / 60, 1000 / 60);
  }
  assert.equal(fruit.active, false);
  return { viewport: [width, height], xOffset, vx, heightFraction, frame,
    seconds: frame / 60, beforeRelease, scoreAfter: scene.score,
    penaltyApplied: scene.score === 15 };
}
const normal60Hz = simulate(1280, 900, 70, 180, 0.82);
const portrait60Hz = simulate(320, 844, 70, 180, 0.82);
assert.equal(normal60Hz.penaltyApplied, true);
assert.equal(portrait60Hz.penaltyApplied, false);
assert.ok(portrait60Hz.beforeRelease.y < 844 + 30);

// Grid is diagnostic coverage, NOT a probability estimate for real gameplay.
const diagnosticGrid = [];
for (const [width, height] of [[320, 844], [390, 844], [768, 1024], [1280, 900]]) {
  let bypasses = 0;
  let cases = 0;
  for (const offset of [-70, 0, 70]) {
    for (const vx of [-180, -120, -60, 0, 60, 120, 180]) {
      for (const fraction of [0.55, 0.685, 0.82]) {
        cases++;
        if (!simulate(width, height, offset, vx, fraction).penaltyApplied) bypasses++;
      }
    }
  }
  diagnosticGrid.push({ viewport: [width, height], cases, bypasses });
}

const client = new GestureClient('ws://unused.invalid');
client.connected = true;
const input = new GestureBladeInput({ scale: { width: 1000, height: 600 } }, client, { mirrorX: false });
const manager = new BladeManager({});
manager.add(input);
const staleTs = Date.now() / 1000 - 5;
for (const [seq, x] of [[1, 0.1], [2, 0.9]]) {
  client._handle({ type: 'gesture', x, y: 0.5, visible: true, active: true,
    seq, stroke_id: 1, revision: 1, ts: staleTs });
}
const staleSegments = manager.update();
const staleHit = Slicer.hitTestAll(staleSegments,
  [{ x: 500, y: 300, r: 30, obj: 'center-fruit' }]).has('center-fruit');
assert.equal(input.isActive(), true);
assert.equal(staleSegments.length, 1);
assert.equal(staleHit, true);
const staleDelivery = {
  generationAgeMs: Math.round(Date.now() - staleTs * 1000),
  receivedAgeMs: performance.now() - client.lastGesture.receivedAt,
  active: input.isActive(), segments: staleSegments, hitsCenterFruit: staleHit,
  limitation: 'Injected late arrival establishes missing source-age rejection; does not measure transport backlog frequency.',
};
input.destroy();

const report = { generatedAt: new Date().toISOString(), productionFilesModified: false,
  safety: 'No camera, network connection, browser, or service started.',
  method: 'Imports real production methods; stubs rendering/audio/socket transport. Ballistic paths use 60 Hz kinematics.',
  recycleOrdering: { normalBottom, skippedBottom, sideExit, normal60Hz, portrait60Hz, diagnosticGrid },
  staleDelivery };
await writeFile(new URL('./audit_frontend_probe.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
