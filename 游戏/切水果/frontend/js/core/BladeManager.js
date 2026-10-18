/**
 * BladeManager —— 刀锋管理器。
 *
 * 聚合所有 BladeInput 实例，每帧计算每个活跃刀锋的
 * "上一帧位置 → 当前帧位置"线段，供 Slicer 做碰撞判定。
 * 支持多路刀锋（为双人对战预留）。
 */
export class BladeManager {
  constructor(scene) {
    this.scene = scene;
    this.inputs = [];
    this._prev = new Map();      // inputId -> {x, y}
    this.segments = [];          // [{id,x1,y1,x2,y2}]
    this.trailPositions = [];    // 刀光拖尾轨迹点
  }

  add(input) {
    this.inputs.push(input);
    return input;
  }

  remove(id) {
    this.inputs = this.inputs.filter((i) => i.id !== id);
    this._prev.delete(id);
  }

  /**
   * 每帧更新，返回本帧刀锋线段列表。
   * @returns {Array<{id:string,x1:number,y1:number,x2:number,y2:number}>}
   */
  update() {
    this.segments = [];
    for (const input of this.inputs) {
      if (input.consumeSamples) {
        const samples = input.consumeSamples();
        if (!input.isActive()) this._prev.delete(input.id);
        for (const sample of samples) this._append(input.id, sample);
        continue;
      }
      if (!input.isActive()) {
        this._prev.delete(input.id);
        continue;
      }
      const pos = input.getPosition();
      if (!pos) {
        this._prev.delete(input.id);
        continue;
      }
      this._append(input.id, { ...pos, strokeId: input.strokeId });
    }
    return this.segments;
  }

  _append(id, sample) {
    const prev = this._prev.get(id);
    if (prev && prev.strokeId === sample.strokeId) {
      if (Math.hypot(sample.x - prev.x, sample.y - prev.y) <= 0.5) return;
      this.segments.push({ id, x1: prev.x, y1: prev.y, x2: sample.x, y2: sample.y });
    }
    this._prev.set(id, sample);
  }

  /** 活跃输入数量（用于演示模式判断无人操作） */
  getActiveCount() {
    return this.inputs.filter((i) => i.isActive()).length;
  }

  /** 清理所有输入（场景切换时） */
  clear() {
    this.inputs = [];
    this._prev.clear();
    this.segments = [];
  }
}
