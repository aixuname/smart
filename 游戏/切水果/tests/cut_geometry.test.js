import test from 'node:test';
import assert from 'node:assert/strict';
import { Slicer } from '../frontend/js/core/Slicer.js';
import { handBladeContacts, fruitCircle } from '../frontend/js/core/CutGeometry.js';

test('a visible blade ring grazing a fruit cuts, but a separated blade does not', () => {
  const fruit = {};
  const circles = [{ x: 500, y: 490, r: 30, obj: fruit }];
  const swipe = { x1: 400, y1: 450, x2: 600, y2: 450, radius: 14 };
  assert.equal(Slicer.hitTestAll([swipe], circles).has(fruit), true);
  assert.equal(Slicer.hitTestAll([{ ...swipe, y1: 445, y2: 445 }], circles).size, 0);
});

test('blade thickness works for short contact samples and never grants a negative radius', () => {
  const fruit = {};
  const circles = [{ x: 0, y: 0, r: 30, obj: fruit }];
  assert.equal(Slicer.hitTestAll([{ x1: 40, y1: 0, x2: 40, y2: 0, radius: 14 }], circles).has(fruit), true);
  assert.equal(Slicer.hitTestAll([{ x1: 40, y1: 0, x2: 40, y2: 0, radius: -100 }], circles).size, 0);
});

test('silver blade follows its visible rotation and excludes the handle', () => {
  for (const angle of [0, Math.PI / 2, Math.PI, -Math.PI / 4]) {
    const tip = { x: 600, y: 400 };
    const contacts = handBladeContacts(tip, angle);
    const at = distance => ({ x: tip.x - Math.cos(angle) * distance,
      y: tip.y - Math.sin(angle) * distance, r: 30, obj: {} });
    const silverOverlap = at(60);
    const handleOnly = at(80);
    assert.equal(Slicer.hitTestAll(contacts, [silverOverlap]).has(silverOverlap.obj), true);
    assert.equal(Slicer.hitTestAll(contacts, [handleOnly]).size, 0);
    const nearHandle = { ...at(70), r: 28 };
    assert.equal(Slicer.hitTestAll(contacts, [nearHandle]).size, 0, 'silver blade must stop at its flat back edge');
    const beside = { x: tip.x + Math.sin(angle) * 50, y: tip.y - Math.cos(angle) * 50, r: 30, obj: {} };
    assert.equal(Slicer.hitTestAll(contacts, [beside]).size, 0, 'no large all-direction cutting radius');
  }
});

test('fruit scales with visible flesh while a rotated bomb keeps its actual body center', () => {
  const fruit = { x: 100, y: 200, displayWidth: 73.6, displayHeight: 73.6,
    scaleY: 1.15, rotation: Math.PI / 2, getData: () => false };
  assert.equal(fruitCircle(fruit).r, 34.5);
  const bomb = { ...fruit, displayWidth: 64, displayHeight: 64, scaleY: 1, getData: () => true };
  const circle = fruitCircle(bomb);
  assert.equal(circle.r, 28);
  assert.equal(circle.x, 96);
  assert.equal(circle.y, 200);
});

test('circle contact detects silver corners and contained centers without filling empty space', () => {
  const blade = handBladeContacts({ x: 0, y: 0 }, 0)[1];
  const circle = (x, y, r) => ({ x, y, r, obj: {} });
  assert.equal(Slicer.hitTestAll([blade], [circle(-20, 0, 1)]).size, 1);
  assert.equal(Slicer.hitTestAll([blade], [circle(-35, -7, 2)]).size, 1);
  assert.equal(Slicer.hitTestAll([blade], [circle(-35, -10, 2)]).size, 0);
});
