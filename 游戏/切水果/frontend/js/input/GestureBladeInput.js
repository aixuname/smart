import { BladeInput } from "./BladeInput.js";
import { gestureScreenPosition } from "./gestureMapping.js";
import { SampleBuffer } from "./SampleBuffer.js";

export class GestureBladeInput extends BladeInput {
  constructor(scene, client, opts = {}) {
    super("gesture");
    this.scene = scene;
    this.client = client;
    this.opts = opts;
    this.pos = null;
    this.lastReceived = -Infinity;
    this.strokeId = 0;
    this.active = false;
    this.samples = new SampleBuffer();
    this._unsub = client.onMessage((msg) => {
      if (msg.type === "disconnected" || (msg.type === "status" &&
          (!msg.cameraOk || msg.modelMissing || msg.initializing))) {
        this.reset();
      }
      if (msg.type !== "gesture") return;
      if (Number.isInteger(msg.seq)) {
        if (this.lastSequence !== undefined && msg.seq !== this.lastSequence + 1) this.strokeId++;
        this.lastSequence = msg.seq;
      }
      if (performance.now() - this.lastReceived > 300) this.strokeId++;
      this.lastReceived = performance.now();
      const key = `${msg.revision}:${msg.stroke_id}`;
      if (key !== this.remoteStroke) this.strokeId++;
      this.remoteStroke = key;
      this.active = !!msg.visible && msg.active !== false;
      this.pos = msg.visible ? { x: msg.x, y: msg.y } : null;
      this.samples.push(this.pos, this.strokeId, this.active);
    });
  }

  reset() {
    this.samples.clear();
    this.pos = null;
    this.active = false;
    this.strokeId++;
  }

  setOptions(opts) {
    this.opts = opts;
    this.reset();
  }

  getPosition() {
    if (!this.pos || !this.client.isConnected || performance.now() - this.lastReceived > 300) return null;
    return gestureScreenPosition(this.pos, this.opts, this.scene.scale.width, this.scene.scale.height);
  }

  isActive() {
    return this.active && this.getPosition() !== null;
  }

  consumeSamples() {
    if (!this.isActive()) {
      this.samples.clear();
      return [];
    }
    return this.samples.take().map(sample => {
      const p = gestureScreenPosition(sample, this.opts, this.scene.scale.width, this.scene.scale.height);
      return { ...p, strokeId: sample.strokeId };
    });
  }

  destroy() {
    this._unsub?.();
    this._unsub = null;
    this.reset();
  }
}
