/**
 * ComboSystem —— 连击计分系统。
 * 短时间窗口内连续切片形成连击，每累计 3 连击提升 1 倍加成（上限 5 倍）。
 */
export class ComboSystem {
  /**
   * @param {number} windowMs 连击时间窗口（毫秒）
   */
  constructor(windowMs = 1800) {
    this.windowMs = windowMs;
    this.count = 0;      // 当前连击数
    this.max = 0;        // 本局最高连击
    this.lastSliceTime = 0;
  }

  /**
   * 记录一次成功切片。
   * @param {number} time 当前时间（毫秒）
   * @returns {number} 更新后的连击数
   */
  onSlice(time) {
    if (this.count > 0 && time - this.lastSliceTime <= this.windowMs) {
      this.count += 1;
    } else {
      this.count = 1;
    }
    this.lastSliceTime = time;
    if (this.count > this.max) this.max = this.count;
    return this.count;
  }

  /**
   * 检测连击是否因超时中断（count>=2 且超过窗口无新切片）。
   * 每帧调用一次；首次检测到中断时返回 true，用于触发提示。
   * @param {number} time 当前时间（毫秒）
   * @returns {boolean} 是否刚发生中断
   */
  checkBreak(time) {
    if (this.count >= 2 && this.lastSliceTime > 0 && time - this.lastSliceTime > this.windowMs) {
      this.count = 0;
      this.lastSliceTime = 0;
      return true;
    }
    return false;
  }

  /** 当前倍率：每 3 连击 +1，上限 5 倍 */
  multiplier() {
    return 1 + Math.min(4, Math.floor(this.count / 3));
  }

  /** 重置（新一局） */
  reset() {
    this.count = 0;
    this.max = 0;
    this.lastSliceTime = 0;
  }
}
