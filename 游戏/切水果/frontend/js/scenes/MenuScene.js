/** A subtle orchard backdrop; interface illustrations are local SVG assets. */
import { Phaser } from "../phaser.js";

export class MenuScene extends Phaser.Scene {
  constructor() { super("MenuScene"); }

  create() {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      this.stars = this.add.particles(0, 0, "star", {
        x: { min: 0, max: this.scale.width },
        y: { min: -20, max: this.scale.height },
        lifespan: { min: 5000, max: 8000 },
        speedY: { min: 5, max: 14 },
        speedX: { min: -3, max: 3 },
        scale: { start: 0.22, end: 0.03 },
        alpha: { start: 0.2, end: 0 },
        tint: 0xc5e99a,
        frequency: 400,
        quantity: 1,
        maxParticles: 24,
      });
    }
    this.game.events.emit("ui:menu");
  }
}
