/**
 * BladeInput —— 刀锋输入抽象基类。
 *
 * 手势与鼠标都实现统一接口，由 BladeManager 聚合，天然支持多路刀锋
 * （为双人对战预留扩展点：同一接口可挂多路实例）。
 */
export class BladeInput {
  /**
   * @param {string} id 输入标识，如 "mouse" / "gesture-0"
   */
  constructor(id) {
    this.id = id;
    this._listeners = new Set();
  }

  /**
   * 当前刀锋位置（世界坐标），不可用时返回 null
   * @returns {{x:number,y:number}|null}
   */
  getPosition() {
    return null;
  }

  /**
   * 是否处于可用状态（门控，防止误触）
   * @returns {boolean}
   */
  isActive() {
    return false;
  }

  /** 订阅位置移动事件 */
  onMove(cb) {
    this._listeners.add(cb);
    return () => this._listeners.delete(cb);
  }

  _emitMove(pos) {
    for (const cb of this._listeners) {
      try { cb(pos); } catch (e) { /* noop */ }
    }
  }
}
