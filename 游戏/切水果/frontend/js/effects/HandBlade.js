import { TIP_RADIUS, BLADE_LENGTH, BLADE_HALF_WIDTH, SILVER_BLADE_POINTS, handBladeContacts } from '../core/CutGeometry.js';

/** The visible tip and silver edge share their dimensions with contact detection. */
export class HandBlade {
  constructor(scene) {
    this.sprite = scene.add.graphics().setDepth(45).setVisible(false);
    const g = this.sprite;
    g.fillStyle(0xc5e99a, 0.15);
    g.fillCircle(0, 0, TIP_RADIUS + 1);
    g.lineStyle(2, 0xc5e99a, 0.8);
    g.strokeCircle(0, 0, 9);
    // Draw once; only transform the object while tracking.
    const polygon = (color, points) => {
      g.fillStyle(color, 1);
      g.fillPoints(points.map(([x, y]) => ({ x, y })), true);
    };
    polygon(0xf2f3df, SILVER_BLADE_POINTS);
    polygon(0x9bab87, [[0, 0], [-23, BLADE_HALF_WIDTH], [-BLADE_LENGTH, 5], [-BLADE_LENGTH, 0]]);
    g.fillStyle(0xefba91, 1);
    g.fillRoundedRect(-40, -10, 5, 20, 2);
    g.fillStyle(0x314431, 1);
    g.fillRoundedRect(-60, -5, 20, 10, 3);
    g.lineStyle(2, 0x8fa37b, 1);
    for (let x = -56; x < -42; x += 5) g.lineBetween(x, -4, x, 4);
    this.last = null;
    this.strokeId = null;
    this.rotation = -Math.PI / 4;
    this.active = false;
  }

  update(pos, active, strokeId) {
    this.active = !!pos && active;
    this.sprite.setVisible(!!pos);
    if (!pos) {
      this.last = null;
      return;
    }
    if (this.last && this.strokeId === strokeId) {
      const dx = pos.x - this.last.x;
      const dy = pos.y - this.last.y;
      if (Math.hypot(dx, dy) > 1) {
        const angle = Math.atan2(dy, dx);
        const difference = Math.atan2(Math.sin(angle - this.rotation), Math.cos(angle - this.rotation));
        this.rotation += difference * 0.4;
      }
    }
    this.sprite.setPosition(pos.x, pos.y).setRotation(this.rotation).setAlpha(active ? 1 : 0.45);
    this.last = { ...pos };
    this.strokeId = strokeId;
  }

  getCutSegments() {
    return this.active && this.last ? handBladeContacts(this.last, this.rotation) : [];
  }
}
