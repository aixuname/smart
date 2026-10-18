import { BladeInput } from "./BladeInput.js";
import { SampleBuffer } from "./SampleBuffer.js";

/**
 * MouseBladeInput —— 鼠标刀锋输入。
 * 鼠标在游戏区域内移动即产生刀锋轨迹（无需按下，上手零门槛）。
 */
export class MouseBladeInput extends BladeInput {
  constructor(scene) {
    super("mouse");
    this.scene = scene;
    this.pos = null;
    this.lastMove = -Infinity;
    this.strokeId = 0;
    this.samples = new SampleBuffer();

    this._onMove = (pointer) => {
      if (performance.now() - this.lastMove > 250) this.strokeId++;
      this.lastMove = performance.now();
      this.pos = { x: pointer.worldX, y: pointer.worldY };
      this.samples.push(this.pos, this.strokeId);
      this._emitMove(this.pos);
    };
    this._onOut = () => {
      this.reset();
    };

    scene.input.on("pointermove", this._onMove);
    scene.input.on("gameout", this._onOut);
  }

  /** 场景切换时解除输入监听器，防止泄漏 */
  destroy() {
    if (this.scene && this.scene.input) {
      this.scene.input.off("pointermove", this._onMove);
      this.scene.input.off("gameout", this._onOut);
    }
    this.pos = null;
  }

  getPosition() {
    return this.pos;
  }

  reset() {
    this.pos = null;
    this.strokeId++;
    this.samples.clear();
  }

  consumeSamples() {
    if (!this.isActive()) this.samples.clear();
    return this.samples.take();
  }

  isActive() {
    return this.pos !== null && performance.now() - this.lastMove < 250;
  }
}
