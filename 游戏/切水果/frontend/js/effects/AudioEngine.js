/**
 * AudioEngine —— Web Audio 程序合成音效（零版权资源）。
 * 切水果/炸弹/连击/结束/按钮音效全部由振荡器实时合成。
 */
export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  /** 用户交互后解锁音频上下文（浏览器自动播放策略要求） */
  unlock() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  }

  _tone(freq, dur, opts = {}) {
    if (!this.enabled || !this.ctx) return;
    const { type = "sine", gain = 0.18, slideTo = null, delay = 0 } = opts;
    const t0 = this.ctx.currentTime + delay;
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (slideTo) {
      osc.frequency.exponentialRampToValueAtTime(slideTo, t0 + dur);
    }
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(gain, t0 + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g).connect(this.ctx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.05);
  }

  /** 切水果：短促"啵"声 */
  slice() {
    this._tone(420, 0.09, { type: "triangle", gain: 0.22, slideTo: 880 });
  }

  /** 连击反馈：上行琶音 */
  combo(level) {
    const base = 520 + level * 90;
    this._tone(base, 0.08, { type: "square", gain: 0.1, slideTo: base * 1.5 });
    this._tone(base * 1.5, 0.1, { type: "square", gain: 0.08, delay: 0.07, slideTo: base * 2 });
  }

  /** 炸弹爆炸：低频轰鸣 */
  bomb() {
    this._tone(160, 0.5, { type: "sawtooth", gain: 0.3, slideTo: 40 });
    this._tone(80, 0.6, { type: "square", gain: 0.22, slideTo: 30 });
  }

  /** 漏切：低鸣提示 */
  miss() {
    this._tone(200, 0.22, { type: "sawtooth", gain: 0.12, slideTo: 140 });
  }

  /** 游戏结束：下行旋律 */
  gameOver() {
    this._tone(440, 0.18, { type: "triangle", gain: 0.2 });
    this._tone(330, 0.18, { type: "triangle", gain: 0.18, delay: 0.16 });
    this._tone(220, 0.32, { type: "triangle", gain: 0.2, delay: 0.32, slideTo: 180 });
  }

  /** 按钮点击 */
  button() {
    this._tone(660, 0.06, { type: "square", gain: 0.08, slideTo: 880 });
  }

  /** 游戏开始：上行旋律 */
  start() {
    this._tone(392, 0.1, { type: "triangle", gain: 0.16 });
    this._tone(523, 0.1, { type: "triangle", gain: 0.16, delay: 0.1 });
    this._tone(659, 0.18, { type: "triangle", gain: 0.16, delay: 0.2 });
  }

  /** 排行榜上榜 */
  rankUp() {
    this._tone(523, 0.12, { type: "sine", gain: 0.16 });
    this._tone(659, 0.12, { type: "sine", gain: 0.16, delay: 0.1 });
    this._tone(784, 0.12, { type: "sine", gain: 0.16, delay: 0.2 });
    this._tone(1046, 0.25, { type: "sine", gain: 0.16, delay: 0.3 });
  }
}
