/**
 * FruitSpawner —— 水果/炸弹生成器。
 * 抛物线弹道 + 旋转，出屏自动回收。
 */
import { Phaser } from "../phaser.js";
import { fruitCircle } from "./CutGeometry.js";

export class FruitSpawner {
  /**
   * @param {Phaser.Scene} scene
   * @param {object} opts { bombRatio:0.15, batchMin:1, batchMax:3,
   *                       spawnIntervalMin:700, spawnIntervalMax:1100,
   *                       gravityY:1400 }
   */
  constructor(scene, opts = {}) {
    this.scene = scene;
    this.opts = Object.assign({
      bombRatio: 0.15,
      batchMin: 1,
      batchMax: 2,
      spawnIntervalMin: 900,
      spawnIntervalMax: 1300,
      gravityY: 1400,
    }, opts);

    this.group = scene.physics.add.group({
      allowGravity: true,
      maxSize: 48,
    });
    this.fruitKeys = [
      "fruit-red", "fruit-green", "fruit-orange",
      "fruit-yellow", "fruit-purple", "fruit-cyan",
    ];
    this.lastSpawn = 0;
    this.nextInterval = this._randInterval();
    this.worldW = scene.scale.width;
    this.worldH = scene.scale.height;
  }

  _randInterval() {
    return Phaser.Math.Between(this.opts.spawnIntervalMin, this.opts.spawnIntervalMax);
  }

  /**
   * 主循环调用：按节奏生成水果批次
   * @param {number} time 毫秒
   */
  update(time) {
    this.worldW = this.scene.scale.width;
    this.worldH = this.scene.scale.height;
    if (time - this.lastSpawn >= this.nextInterval) {
      this.lastSpawn = time;
      this.nextInterval = this._randInterval();
      const n = Phaser.Math.Between(this.opts.batchMin, this.opts.batchMax);
      for (let i = 0; i < n; i++) {
        const isBomb = Math.random() < this.opts.bombRatio;
        this._spawnOne(isBomb);
      }
    }
    this._recycleOffscreen();
  }

  _spawnOne(isBomb) {
    const key = isBomb ? "bomb" : Phaser.Utils.Array.GetRandom(this.fruitKeys);
    const w = this.worldW;
    const h = this.worldH;
    // 从屏幕底部边缘抛出（x 微随机避免完全重叠），视线聚焦在画面中轴
    const x = w / 2 + Phaser.Math.Between(-70, 70);
    const y = h + 8;

    let spr = this.group.getFirstDead(false);
    if (!spr) spr = this.group.create(x, y, key);
    if (!spr) return null;
    spr.setTexture(key).setAlpha(1).setAngle(0);
    spr.enableBody(true, x, y, true, true);
    spr.body.setAllowGravity(true);
    spr.setDepth(10);
    spr.setScale(Phaser.Math.FloatBetween(0.85, 1.15));
    // 抛物线初速度：水平随机漂移，垂直向上抛（大初速 → 更高弹道）
    const vx = Phaser.Math.Between(-180, 180);
    const vy = -Math.sqrt(2 * this.opts.gravityY * h * Phaser.Math.FloatBetween(0.55, 0.82));
    spr.setVelocity(vx, vy);
    spr.setAngularVelocity(Phaser.Math.Between(-240, 240));
    spr.setData("sliced", false);
    spr.setData("isBomb", isBomb);
    spr.body.setSize(48, 48, true);
    return spr;
  }

  _recycleOffscreen() {
    const w = this.worldW;
    const h = this.worldH;
    const margin = 160;
    this.group.children.iterate((spr) => {
      if (!spr || !spr.active) return;
      // 完全离开屏幕边界（上下左右任一方向）即回收，避免横向飞出的水果残留泄漏
      const offX = spr.x < -margin || spr.x > w + margin;
      const offBottom = spr.y > h + 120 && spr.body && spr.body.velocity.y > 0;
      if (offX || offBottom) {
        this.release(spr);
      }
    });
  }

  /** 供切片判定使用：收集当前所有活跃物体的碰撞圆 */
  collectCircles() {
    const circles = [];
    this.group.children.iterate((spr) => {
      if (!spr || !spr.active) return;
      circles.push(fruitCircle(spr));
    });
    return circles;
  }

  /**
   * 查找距离 pos 最近的未切片水果（演示模式 AI 目标）。
   * @param {{x:number,y:number}|null} pos
   * @returns {Phaser.GameObjects.Sprite|null}
   */
  findNearestTo(pos) {
    if (!pos) return null;
    let best = null;
    let bestDist = Infinity;
    this.group.children.iterate((spr) => {
      // 演示 AI 不主动切炸弹（避免自扣分）
      if (!spr || !spr.active || spr.getData("sliced") || spr.getData("isBomb")) return;
      const dx = spr.x - pos.x;
      const dy = spr.y - pos.y;
      const d = dx * dx + dy * dy;
      if (d < bestDist) {
        bestDist = d;
        best = spr;
      }
    });
    return best;
  }

  /**
   * 查找演示 AI 的"最佳挥刀目标"：优先屏幕上部（仍在飞行上升）的可切水果，
   * 让演示看起来更自然、更容易切中；无可用时退回最近的任何水果。
   * @param {{x:number,y:number}|null} pos 刀锋位置
   * @param {number} maxY 目标 y 上限（演示只切该高度以上的水果）
   * @returns {Phaser.GameObjects.Sprite|null}
   */
  findBestSwingTarget(pos, maxY) {
    let best = null;
    let bestDist = Infinity;
    let fallback = null;
    let fallbackDist = Infinity;
    this.group.children.iterate((spr) => {
      if (!spr || !spr.active || spr.getData("sliced") || spr.getData("isBomb")) return;
      const dx = pos ? spr.x - pos.x : 0;
      const dy = pos ? spr.y - pos.y : 0;
      const d = pos ? dx * dx + dy * dy : 0;
      // 屏幕上部（上升中）的水果优先
      if (spr.y <= maxY) {
        if (d < bestDist) { bestDist = d; best = spr; }
      } else if (d < fallbackDist) {
        fallbackDist = d; fallback = spr;
      }
    });
    return best || fallback;
  }

  /** 销毁全部物体（重开一局） */
  release(sprite) {
    if (!sprite?.active) return;
    sprite.setData("sliced", true);
    sprite.setVelocity(0, 0).setAngularVelocity(0);
    sprite.disableBody(true, true);
  }

  clear() {
    this.group.clear(true, true);
    this.lastSpawn = 0;
  }
}
