/**
 * BootScene —— 预生成全部程序化纹理，随后进入主菜单。
 * 零图片资源：水果/炸弹/星星/粒子等全部用 Graphics 程序绘制。
 */
import { Phaser } from "../phaser.js";

export class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }

  create() {
    this._createFruitTextures();
    this._createBombTexture();
    this._createStarTexture();
    this._createBladeTexture();
    this.scene.start("MenuScene");
  }

  /** 程序绘制球形水果纹理 */
  _createFruitTextures() {
    // key -> [主色, 深色, 高光色]
    const fruits = {
      "fruit-red": [0xff4757, 0xb33939, 0xffd1d8],     // 苹果/西瓜
      "fruit-green": [0x2ed573, 0x1e8449, 0xd2f5e3],    // 猕猴桃/青瓜
      "fruit-orange": [0xffa502, 0xd35400, 0xffe7b8],   // 橙子
      "fruit-yellow": [0xffd93d, 0xc9a400, 0xfff4c4],   // 柠檬
      "fruit-purple": [0xa55eea, 0x6c5ce7, 0xe5d3ff],   // 葡萄
      "fruit-cyan": [0x18dcff, 0x0aa5b0, 0xd6f7ff],     // 蜜瓜
    };
    for (const [key, [main, dark, light]] of Object.entries(fruits)) {
      const g = this.make.graphics({ add: false });
      g.fillStyle(main, 1);
      g.fillCircle(32, 32, 30);
      // 下半部暗部
      g.fillStyle(dark, 0.55);
      g.fillCircle(40, 46, 20);
      // 高光
      g.fillStyle(0xffffff, 0.55);
      g.fillCircle(24, 21, 9);
      g.fillStyle(0xffffff, 0.25);
      g.fillCircle(19, 15, 4);
      // 果柄
      g.fillStyle(0x5d4037, 1);
      g.fillRect(29, 2, 6, 10);
      g.generateTexture(key, 64, 64);
      g.destroy();
    }
  }

  /** 程序绘制炸弹纹理 */
  _createBombTexture() {
    const g = this.make.graphics({ add: false });
    // 弹体
    g.fillStyle(0x22222e, 1);
    g.fillCircle(32, 36, 28);
    g.fillStyle(0x11111a, 1);
    g.fillCircle(44, 46, 14);
    g.fillStyle(0xffffff, 0.25);
    g.fillCircle(26, 28, 6);
    // 引线（折线）
    g.lineStyle(4, 0x8b5e3c, 1);
    g.beginPath();
    g.moveTo(32, 10);
    g.lineTo(40, 2);
    g.lineTo(48, 8);
    g.strokePath();
    // 火花
    g.fillStyle(0xffd93d, 1);
    g.fillCircle(48, 8, 6);
    g.fillStyle(0xffa502, 1);
    g.fillCircle(48, 8, 3);
    g.fillStyle(0xff4757, 1);
    g.fillCircle(48, 8, 1.5);
    g.generateTexture("bomb", 64, 64);
    g.destroy();
  }

  /** 小星星纹理（背景粒子） */
  _createStarTexture() {
    const g = this.make.graphics({ add: false });
    g.fillStyle(0xffffff, 1);
    g.fillCircle(8, 8, 4);
    g.fillStyle(0xffffff, 0.5);
    g.fillCircle(8, 8, 7);
    g.generateTexture("star", 16, 16);
    g.destroy();
  }

  /** 刀光粒子纹理（圆形光点） */
  _createBladeTexture() {
    const g = this.make.graphics({ add: false });
    g.fillStyle(0xffffff, 1);
    g.fillCircle(8, 8, 8);
    g.fillStyle(0xffffff, 0.45);
    g.fillCircle(8, 8, 12);
    g.generateTexture("blade-glow", 16, 16);
    g.destroy();

    const g2 = this.make.graphics({ add: false });
    g2.fillStyle(0xffffff, 1);
    g2.fillCircle(6, 6, 6);
    g2.fillStyle(0xffffff, 0.5);
    g2.fillCircle(6, 6, 10);
    g2.generateTexture("juice", 12, 12);
    g2.destroy();
  }
}
