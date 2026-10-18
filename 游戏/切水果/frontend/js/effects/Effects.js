/**
 * Effects —— 视觉特效工具集：果汁粒子、分数弹跳、震屏、刀光拖尾。
 */
import { Phaser } from "../phaser.js";

export class Effects {
  /**
   * 果汁粒子飞溅（水果被切开）
   * @param {Phaser.Scene} scene
   * @param {number} x
   * @param {number} y
   * @param {number} color 十六进制颜色
   */
  static juiceBurst(scene, x, y, color) {
    if (!scene._juiceEmitters) scene._juiceEmitters = new Map();
    const existing = scene._juiceEmitters.get(color);
    if (existing?.scene) { existing.explode(16, x, y); return existing; }
    const e = scene.add.particles(0, 0, "juice", {
      speed: { min: 120, max: 340 },
      angle: { min: 0, max: 360 },
      scale: { start: 0.7, end: 0 },
      lifespan: { min: 300, max: 720 },
      gravityY: 900,
      tint: color,
      blendMode: Phaser.BlendModes.ADD,
      quantity: 16,
      emitting: false,
      maxParticles: 96,
    });
    e.setDepth(30);
    e.explode(16, x, y);
    scene._juiceEmitters.set(color, e);
    return e;
  }

  /**
   * 炸弹爆炸（大范围红色粒子 + 火光）
   */
  static bombBurst(scene, x, y) {
    if (scene._bombEmitter?.scene) { scene._bombEmitter.explode(40, x, y); return; }
    const e = scene.add.particles(0, 0, "juice", {
      speed: { min: 160, max: 480 },
      angle: { min: 0, max: 360 },
      scale: { start: 1.1, end: 0 },
      lifespan: { min: 350, max: 900 },
      gravityY: 600,
      tint: [0xff4757, 0xffa502, 0xffd93d],
      blendMode: Phaser.BlendModes.ADD,
      quantity: 40,
      emitting: false,
      maxParticles: 80,
    });
    e.setDepth(30);
    e.explode(40, x, y);
    scene._bombEmitter = e;
  }

  /**
   * 得分文字弹跳（上浮淡出）
   */
  static scorePopup(scene, x, y, text, color = "#FFD93D", size = 26) {
    const t = scene.add.text(x, y, text, {
      fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif',
      fontSize: `${size}px`,
      fontStyle: "bold",
      color,
      stroke: "#000000",
      strokeThickness: 5,
    }).setOrigin(0.5).setDepth(50);
    t.setScale(0.4);
    scene.tweens.add({
      targets: t,
      scale: 1,
      duration: 120,
      ease: "Back.easeOut",
    });
    scene.tweens.add({
      targets: t,
      y: y - 64,
      alpha: 0,
      duration: 750,
      delay: 150,
      ease: "Cubic.easeOut",
      onComplete: () => t.destroy(),
    });
    return t;
  }

  /**
   * 连击大字反馈（居中放大弹出）
   */
  static comboPopup(scene, text) {
    const t = scene.add.text(scene.scale.width / 2, scene.scale.height * 0.35, text, {
      fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif',
      fontSize: "54px",
      fontStyle: "bold",
      color: "#FFD93D",
      stroke: "#000000",
      strokeThickness: 8,
    }).setOrigin(0.5).setDepth(50);
    t.setAlpha(0).setScale(0.2);
    scene.tweens.add({
      targets: t,
      alpha: 1, scale: 1,
      duration: 220,
      ease: "Back.easeOut",
    });
    scene.tweens.add({
      targets: t,
      alpha: 0, scale: 1.25,
      duration: 420,
      delay: 420,
      ease: "Cubic.easeIn",
      onComplete: () => t.destroy(),
    });
  }

  /** 屏幕震动 */
  static shake(scene, intensity = 10, duration = 200) {
    scene.cameras.main.shake(duration, 0.004 * intensity);
  }

  /**
   * 创建刀光拖尾发射器（GameScene 每帧调用 emitParticleAt）
   */
  static createBladeTrail(scene, color = 0x08d9d6) {
    const e = scene.add.particles(0, 0, "blade-glow", {
      lifespan: { min: 120, max: 240 },
      speed: { min: 0, max: 24 },
      scale: { start: 0.55, end: 0 },
      alpha: { start: 0.9, end: 0 },
      tint: color,
      blendMode: Phaser.BlendModes.ADD,
      frequency: -1,
      emitting: false,
      maxParticles: 64,
    });
    e.setDepth(20);
    return e;
  }
}
