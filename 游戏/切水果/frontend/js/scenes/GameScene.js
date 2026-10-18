/**
 * GameScene —— 核心玩法场景。
 * 水果/炸弹抛物线弹射、刀锋线段碰撞判定、连击计分、HUD、规则引擎。
 */
import { Phaser } from "../phaser.js";
import { BladeManager } from "../core/BladeManager.js";
import { MouseBladeInput } from "../input/MouseBladeInput.js";
import { GestureBladeInput } from "../input/GestureBladeInput.js";
import { DemoBladeInput } from "../input/DemoBladeInput.js";
import { FruitSpawner } from "../core/FruitSpawner.js";
import { Slicer } from "../core/Slicer.js";
import { ComboSystem } from "../core/ComboSystem.js";
import { Effects } from "../effects/Effects.js";
import { HandBlade } from "../effects/HandBlade.js";
import { TIP_RADIUS } from "../core/CutGeometry.js";
import { audio } from "../effects/audio.js";
import { gestureClient } from "../net/client.js";

// 水果纹理 key -> 果汁粒子颜色
const FRUIT_COLORS = {
  "fruit-red": 0xff4757,
  "fruit-green": 0x2ed573,
  "fruit-orange": 0xffa502,
  "fruit-yellow": 0xffd93d,
  "fruit-purple": 0xa55eea,
  "fruit-cyan": 0x18dcff,
};

export class GameScene extends Phaser.Scene {
  constructor() {
    super("GameScene");
  }

  init(data) {
    this.mode = data.mode || this.registry.get("mode") || "endless";
    this.inputMode = data.input || this.registry.get("input") || "gesture";
  }

  create() {
    this.physics.world.gravity.y = 1400;

    // 局内状态（无尽模式机会仅由切到炸弹消耗；漏切不扣）
    this.MAX_CHANCES = 5;
    this.score = 0;
    this.misses = 0;
    this.sliced = 0;
    this.timeLeft = 60;
    this.over = false;
    this.startTime = 0;
    this.elapsed = 0;
    this.showGuide = false;
    this.demoInput = null;
    this.lastHumanTime = 0;
    this.waitingForInput = this.inputMode === "gesture" && this.mode !== "demo";

    // 输入（手势 + 鼠标同时可用；demo 模式追加 AI 刀锋）
    // 菜单选择"鼠标操作"时禁用手势刀锋，避免挥手误切
    this.bladeManager = new BladeManager(this);
    this.mouseInput = this.bladeManager.add(new MouseBladeInput(this));
    // 镜像默认开启（摄像头画面左右相反），可在菜单中切换
    const mirror = this.registry.get("mirror");
    this.gestureInput = null;
    if (this.inputMode === "gesture") {
      this.gestureInput = new GestureBladeInput(this, gestureClient, this.registry.get("gestureOptions") || { mirrorX: mirror !== false });
      this.bladeManager.add(this.gestureInput);
    }
    if (this.mode === "demo") {
      this.demoInput = new DemoBladeInput();
      this.bladeManager.add(this.demoInput);
    }

    // 场景切换时注销手势订阅，防止 listener 累积泄漏
    this.events.once("shutdown", () => {
      this.game.events.emit("ui:guide", false);
      for (const inp of this.bladeManager.inputs) {
        if (inp && typeof inp.destroy === "function") inp.destroy();
      }
      this.bladeManager.clear();
    });

    // 生成器（demo 节奏放缓）
    const spawnOpts = this.mode === "demo"
      ? { spawnIntervalMin: 900, spawnIntervalMax: 1500, batchMax: 2, bombRatio: 0.1 }
      : {};
    this.spawner = new FruitSpawner(this, spawnOpts);

    this.combo = new ComboSystem(1800);

    // 刀光拖尾（鼠标=暖珊瑚，手势/AI=青柠绿）
    this.trailMouse = Effects.createBladeTrail(this, 0xefa88d);
    this.trailGesture = Effects.createBladeTrail(this, 0xc5e99a);
    this.handBlade = new HandBlade(this);

    this._createHUD();
    const onResize = () => {
      this.bladeManager._prev.clear();
      this.mouseInput.reset();
      this.gestureInput?.reset();
      this._layoutHUD();
    };
    this.scale.on("resize", onResize);
    this.events.once("shutdown", () => this.scale.off("resize", onResize));

    // 通知 UI 层进入游戏
    this.game.events.emit("ui:game", { mode: this.mode, input: this.inputMode });

    // 手势模式显示引导提示
    if (this.inputMode === "gesture") {
      this.showGuide = true;
      this.guideShownAt = this.elapsed;
      this.game.events.emit("ui:guide", true);
    }

    audio.start();
  }

  update(time, delta) {
    if (this.over) return;
    if (this.waitingForInput) {
      if (this.gestureInput?.getPosition() || this.mouseInput.isActive() || this.inputMode === "mouse") {
        this.waitingForInput = false;
      } else {
        this._emitTrails();
        this._updateHUD(this.elapsed);
        return;
      }
    }
    if (!this.startTime) this.startTime = time;
    this.elapsed += delta;
    time = this.elapsed;
    if (this.mode === "timed") {
      this.timeLeft = Math.max(0, 60 - this.elapsed / 1000);
      if (this.timeLeft <= 0) {
        this._updateHUD(time);
        this._gameOver();
        return;
      }
    }

    if (this.mode === "demo" && this.demoInput) this._demoControl(time, delta);

    // 1. 更新刀锋线段
    const segs = this.bladeManager.update();
    this._emitTrails();

    // 3. 切片判定
    this._checkSlices(segs, time);
    if (this.over) return;

    // 3.5 连击中断反馈
    if (this.combo.checkBreak(time)) {
      Effects.comboPopup(this, "连击中断");
      audio.miss();
    }

    // 4. 生成水果
    this.spawner.update(this.elapsed);

    // 5. 漏切判定（仅回收落地物体，不再扣机会）
    this._checkMisses();

    // 6. HUD 刷新
    this._updateHUD(time);

    // 引导提示自动消失
    if (this.showGuide && time - this.guideShownAt > 3500) {
      this.showGuide = false;
      this.game.events.emit("ui:guide", false);
    }
  }

  // ------------------------------------------------------------------
  _emitTrails() {
    const cursor = this.gestureInput?.getPosition();
    this.handBlade.update(cursor, this.gestureInput?.isActive(), this.gestureInput?.strokeId);
    for (const input of this.bladeManager.inputs) {
      if (!input.isActive()) continue;
      const p = input.getPosition();
      if (!p) continue;
      const trail = input.id === "mouse" ? this.trailMouse : this.trailGesture;
      trail.emitParticleAt(p.x, p.y);
    }
  }

  _checkSlices(segs, time) {
    const cutting = segs.map(seg => ({ ...seg, radius: TIP_RADIUS }));
    // Fresh active contact also counts: a fruit arriving at a still blade must match
    // what the player sees. Inactive, missing and expired inputs cannot contribute.
    for (const input of this.bladeManager.inputs) {
      if (!input.isActive()) continue;
      const pos = input.getPosition();
      if (!pos) continue;
      if (input.id === 'gesture') cutting.push(...this.handBlade.getCutSegments());
      else cutting.push({ x1: pos.x, y1: pos.y, x2: pos.x, y2: pos.y, radius: TIP_RADIUS });
    }
    if (!cutting.length) return;
    const circles = this.spawner.collectCircles();
    const hit = Slicer.hitTestAll(cutting, circles);
    if (!hit.size) return;
    for (const spr of hit) {
      if (this.over) break;
      if (spr.getData("sliced")) continue;
      // 已落出屏幕的水果不允许再被切到（避免对落地物体计分）
      if (spr.y > this.scale.height) continue;
      spr.setData("sliced", true);
      if (spr.getData("isBomb")) {
        this._onBomb(spr);
      } else {
        this._onFruit(spr, time);
      }
    }
  }

  _onFruit(spr, time) {
    const comboCount = this.combo.onSlice(time);
    const mult = this.combo.multiplier();
    const pts = 10 * mult;
    this.score += pts;
    this.sliced += 1;

    const color = FRUIT_COLORS[spr.texture.key] || 0x08d9d6;
    Effects.juiceBurst(this, spr.x, spr.y, color);
    Effects.scorePopup(this, spr.x, spr.y - 24, `+${pts}`, "#FFD93D", 26);

    if (comboCount > 1 && comboCount % 3 === 0) {
      Effects.comboPopup(this, `COMBO x${comboCount}`);
      audio.combo(comboCount);
    } else {
      audio.slice();
    }
    this.spawner.release(spr);
  }

  _onBomb(spr) {
    const { x, y } = spr;
    Effects.bombBurst(this, spr.x, spr.y);
    Effects.shake(this, 16, 300);
    this.cameras.main.flash(280, 255, 60, 60, false); // 全屏红闪，增强冲击力
    audio.bomb();
    this.spawner.release(spr);

    if (this.mode === "endless") {
      this.misses += 1;
      Effects.scorePopup(this, this.scale.width / 2, this.scale.height * 0.35, "BOOM!", "#FF4D4D", 40);
      if (this.misses >= this.MAX_CHANCES) this._gameOver();
    } else {
      this.score = Math.max(0, this.score - 10);
      this.misses += 1; // 统计切到炸弹次数（供结算展示）
      Effects.scorePopup(this, x, y - 24, "-10", "#FF4D4D", 24);
    }
  }

  _checkMisses() {
    const h = this.scale.height;
    this.spawner.group.children.iterate((spr) => {
      if (!spr || !spr.active) return;
      if (spr.getData("sliced")) return;
      if (spr.y > h + 30 && spr.body.velocity.y > 0) {
        spr.setData("sliced", true); // 防重复计数
        // 限时模式：漏切扣 5 分，营造紧迫感（无尽模式漏切不惩罚）
        if (this.mode === "timed" && !spr.getData("isBomb")) {
          this.score = Math.max(0, this.score - 5);
          Effects.scorePopup(this, spr.x, spr.y - 20, "-5", "#FF4D4D", 20);
          audio.miss();
        }
        this.spawner.release(spr);
      }
    });
  }

  _demoControl(time, delta) {
    if (this.mouseInput.isActive() || this.gestureInput?.isActive()) {
      this.lastHumanTime = time;
      this.demoInput.pos = null;
      return;
    }
    if (time - (this.lastHumanTime || -Infinity) < 2000) return;
    // 优先切屏幕上部（仍在上升）的水果，演示更自然、更易切中
    let target = this.spawner.findBestSwingTarget(this.demoInput.getPosition(), this.scale.height * 0.68);
    if (!target) {
      target = {
        x: this.scale.width * Phaser.Math.FloatBetween(0.25, 0.75),
        y: this.scale.height * Phaser.Math.FloatBetween(0.25, 0.55),
      };
    }
    this.demoInput.moveToward(target, delta, 2600);
  }

  // ------------------------------------------------------------------
  _createHUD() {
    const font = '"PingFang SC","Microsoft YaHei",sans-serif';
    this.hudPanel = this.add.graphics().setDepth(39);
    this.hudScoreLabel = this.add.text(44, 38, "得分 / SCORE", {
      fontFamily: font, fontSize: "11px", color: "#a5b59a",
    }).setDepth(40);
    this.hudScore = this.add.text(42, 57, "0", {
      fontFamily: font, fontSize: "44px", fontStyle: "bold",
      color: "#f3f1e7",
    }).setDepth(40);

    this.hudCombo = this.add.text(34, 0, "", {
      fontFamily: font, fontSize: "25px", fontStyle: "bold",
      color: "#c5e99a", stroke: "#111b17", strokeThickness: 3,
    }).setOrigin(0, 1).setDepth(40);

    this.hudStateLabel = this.add.text(0, 38, this.mode === "endless" ? "剩余机会" : this.mode === "timed" ? "倒计时 / TIME" : "放松，欣赏这一局", {
      fontFamily: font, fontSize: "11px", color: "#a5b59a",
    }).setOrigin(1, 0).setDepth(40);
    this.hudState = this.add.text(0, 63, "", {
      fontFamily: font, fontSize: "26px", fontStyle: "bold",
      color: "#c5e99a",
    }).setOrigin(1, 0).setDepth(40);

    this.hudInput = this.add.text(0, 0, "", {
      fontFamily: font, fontSize: "12px", color: "#a5b59a",
    }).setOrigin(0.5).setDepth(40);
    this._layoutHUD();
  }

  _layoutHUD() {
    const w = this.scale.width, h = this.scale.height;
    this.hudCardWidth = w < 600 ? Math.min(145, (w - 64) / 2) : 176;
    this.hudPanel.clear().fillStyle(0x1b2920, 0.88).lineStyle(1, 0xc5e99a, 0.15);
    for (const x of [24, w - 24 - this.hudCardWidth]) {
      this.hudPanel.fillRoundedRect(x, 24, this.hudCardWidth, 88, 14);
      this.hudPanel.strokeRoundedRect(x, 24, this.hudCardWidth, 88, 14);
    }
    this.hudStateLabel.setPosition(w - 42, 39);
    this.hudState.setPosition(w - 42, 63);
    this.hudCombo.setPosition(34, h - (w < 600 ? 142 : 95));
    this.hudInput.setPosition(w / 2, h - (w < 600 ? 105 : 78));
  }

  _updateHUD(time) {
    this.hudScore.setText(String(this.score));
    this.hudScore.setScale(Math.min(1, (this.hudCardWidth - 32) / Math.max(1, this.hudScore.width)));

    if (this.combo.count >= 2) {
      const mult = this.combo.multiplier();
      this.hudCombo.setText(mult > 1
        ? `COMBO x${this.combo.count}  ×${mult}`
        : `COMBO x${this.combo.count}`);
    } else {
      this.hudCombo.setText("");
    }

    if (this.mode === "endless") {
      const left = Math.max(0, this.MAX_CHANCES - this.misses);
      this.hudState.setText(`${String(left).padStart(2, "0")} / 05`);
    } else if (this.mode === "timed") {
      const sec = Math.ceil(this.timeLeft);
      this.hudState.setText(`${sec}s`);
      this.hudState.setColor(sec <= 10 ? "#f39e8a" : "#c5e99a");
    } else {
      this.hudState.setText("演示模式");
    }

    let activeLabel = "鼠标操作";
    if (this.inputMode === "gesture") {
      activeLabel = this.gestureInput?.isActive() ? "手势出刀" : this.gestureInput?.getPosition()
        ? "手部已识别 · 等待出刀动作" : this.waitingForInput ? "等待识别手掌 · 准备好后自动开始" : "等待手部 · 可直接移动鼠标";
    }
    this.hudInput.setText(`当前输入：${activeLabel}`);
  }

  // ------------------------------------------------------------------
  configureInput(inputMode, options) {
    this.inputMode = inputMode;
    if (this.gestureInput) {
      this.gestureInput.destroy();
      this.bladeManager.remove("gesture");
      this.gestureInput = null;
    }
    if (inputMode === "gesture") {
      this.gestureInput = this.bladeManager.add(new GestureBladeInput(this, gestureClient, options));
    }
    this.bladeManager._prev.clear();
    this.mouseInput.reset();
  }

  _gameOver() {
    if (this.over) return;
    this.over = true;
    audio.gameOver();
    Effects.shake(this, 12, 400);
    this.cameras.main.fadeOut(420, 10, 15, 30); // 结束渐隐，增强仪式感

    this.registry.set("lastResult", {
      score: this.score,
      maxCombo: this.combo.max,
      sliced: this.sliced,
      misses: this.misses,
      mode: this.mode,
    });

    // 结算面板由 ResultScene 统一触发展示
    this.time.delayedCall(560, () => {
      this.scene.start("ResultScene");
    });
  }
}
