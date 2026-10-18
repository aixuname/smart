/**
 * ResultScene —— 结算场景。
 * 游戏结束后切换到此场景，DOM 结算面板由 main.js 控制展示。
 */
import { Phaser } from "../phaser.js";

export class ResultScene extends Phaser.Scene {
  constructor() {
    super("ResultScene");
  }

  create() {
    // 轻量背景星星
    const w = this.scale.width;
    const h = this.scale.height;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) this.add.particles(0, 0, "star", {
      x: { min: 0, max: w },
      y: { min: -20, max: h },
      lifespan: { min: 4000, max: 8000 },
      speedY: { min: 15, max: 50 },
      speedX: { min: -6, max: 6 },
      scale: { start: 0.2, end: 0.03 },
      alpha: { start: 0.2, end: 0 },
      tint: 0xc5e99a,
      frequency: 400,
      quantity: 1,
      maxParticles: 24,
    });

    const result = this.registry.get("lastResult") || {};
    this.game.events.emit("ui:result", result);
  }
}
