/** Preserve turns inside a render frame, with bounded history and stroke breaks. */
export class SampleBuffer {
  constructor(limit = 32) {
    this.limit = limit;
    this.samples = [];
    this.generation = 0;
  }

  clear() {
    this.samples = [];
    this.generation++;
  }

  push(pos, strokeId, active = true) {
    if (!active || !pos) {
      this.clear();
      return;
    }
    if (this.samples.length >= this.limit) this.clear();
    this.samples.push({ ...pos, strokeId: `${this.generation}:${strokeId}`, receivedAt: performance.now() });
  }

  take(maxAge = 250) {
    const now = performance.now();
    const items = this.samples;
    this.samples = [];
    // A stalled render loop cannot replay stale samples when it wakes up.
    if (items.length && now - items[0].receivedAt > maxAge) {
      this.generation++;
      const last = items.at(-1);
      return now - last.receivedAt <= maxAge ? [{ ...last, strokeId: `${this.generation}:resume` }] : [];
    }
    return items;
  }
}
