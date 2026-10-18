import { BladeInput } from "./BladeInput.js";

/**
 * DemoBladeInput —— 演示模式 AI 刀锋。
 * 由 GameScene 每帧调用 moveToward 驱动，自动切水果以吸引展台人流。
 */
export class DemoBladeInput extends BladeInput {
  constructor() {
    super("demo");
    this.pos = null;
  }

  getPosition() {
    return this.pos;
  }

  isActive() {
    return this.pos !== null;
  }

  /**
   * 朝目标点匀速移动（产生可判定的刀锋线段）
   * @param {{x:number,y:number}} target
   * @param {number} delta 毫秒
   * @param {number} speed 像素/秒
   */
  moveToward(target, delta, speed = 2600) {
    if (!this.pos) {
      this.pos = { x: target.x, y: target.y };
      return;
    }
    const dx = target.x - this.pos.x;
    const dy = target.y - this.pos.y;
    const dist = Math.hypot(dx, dy);
    const step = (speed * delta) / 1000;
    if (dist <= step || dist < 1) {
      this.pos.x = target.x;
      this.pos.y = target.y;
    } else {
      this.pos.x += (dx / dist) * step;
      this.pos.y += (dy / dist) * step;
    }
    this._emitMove(this.pos);
  }
}
