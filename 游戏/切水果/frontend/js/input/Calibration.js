export function mappingFromCorners(first, second) {
  const width = second.x - first.x;
  const height = second.y - first.y;
  if (![first.x, first.y, second.x, second.y].every(Number.isFinite) ||
      first.x < 0 || first.y < 0 || second.x > 1 || second.y > 1 || width < 0.2 || height < 0.2) {
    throw new Error("标定范围太小或方向相反，请按左上角、右下角的顺序重试。");
  }
  return { sensitivity: 1 / width, sensitivityY: 1 / height,
    offsetX: (first.x + second.x) / 2 - 0.5, offsetY: (first.y + second.y) / 2 - 0.5 };
}

export class HandCalibration {
  start(now = performance.now()) {
    this.stage = 1;
    this.deadline = now + 3500;
    this.samples = [];
    this.lastReceived = -Infinity;
    this.result = null;
    this.error = "";
  }

  cancel() { this.stage = 0; }

  update(gesture, now = performance.now(), mirror = true) {
    if (!this.stage) return;
    if (gesture?.visible && now - gesture.receivedAt < 300 && gesture.receivedAt !== this.lastReceived) {
      this.lastReceived = gesture.receivedAt;
      this.samples.push({ x: mirror ? 1 - gesture.x : gesture.x, y: gesture.y, time: now });
    }
    this.samples = this.samples.filter(p => now - p.time < 900);
    if (now < this.deadline) return;
    if (this.samples.length < 5) return this.fail("没有持续识别到手，请保持整只手在画面中后重试。");
    const average = { x: 0, y: 0 };
    for (const p of this.samples) { average.x += p.x / this.samples.length; average.y += p.y / this.samples.length; }
    if (this.samples.some(p => Math.hypot(p.x - average.x, p.y - average.y) > 0.045)) {
      return this.fail("手部移动过大，请在每个角落保持稳定后重试。");
    }
    if (this.stage === 1) {
      this.first = average;
      this.stage = 2;
      this.deadline = now + 3500;
      this.samples = [];
    } else {
      try { this.result = mappingFromCorners(this.first, average); }
      catch (e) { this.error = e.message; }
      this.stage = 0;
    }
  }

  fail(message) { this.error = message; this.stage = 0; }

  message(now = performance.now()) {
    if (!this.stage) return this.error || (this.result ? "标定完成，已保存操作范围。" : "");
    return `将手放在舒适范围的${this.stage === 1 ? "左上角" : "右下角"}并保持稳定 · ${Math.max(0, Math.ceil((this.deadline - now) / 1000))} 秒`;
  }
}
