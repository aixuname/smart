/**
 * Slicer —— 刀锋-物体碰撞判定工具。
 * 将刀锋视为有宽度的挥动线段或当前位置，与物体圆形碰撞体做相交检测，
 * 可避免高速挥刀穿透水果的问题。
 */
export class Slicer {
  /**
   * 线段与圆是否相交
   * @param {{x1:number,y1:number,x2:number,y2:number}} seg 刀锋线段
   * @param {number} cx 圆心 x
   * @param {number} cy 圆心 y
   * @param {number} r 半径
   * @returns {boolean}
   */
  static segHitsCircle(seg, cx, cy, r) {
    const dx = seg.x2 - seg.x1;
    const dy = seg.y2 - seg.y1;
    const len2 = dx * dx + dy * dy;
    if (len2 < 1e-6) {
      // 点刀锋：直接距离判断
      return (seg.x1 - cx) * (seg.x1 - cx) + (seg.y1 - cy) * (seg.y1 - cy) <= r * r;
    }
    // 投影参数 t
    let t = ((cx - seg.x1) * dx + (cy - seg.y1) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    const px = seg.x1 + t * dx;
    const py = seg.y1 + t * dy;
    return (px - cx) * (px - cx) + (py - cy) * (py - cy) <= r * r;
  }

  /** Exact convex silver-blade outline; the handle never joins the cutting surface. */
  static polygonHitsCircle(points, cx, cy, r) {
    let positive = false;
    let negative = false;
    for (let i = 0; i < points.length; i++) {
      const a = points[i], b = points[(i + 1) % points.length];
      if (this.segHitsCircle({ x1: a.x, y1: a.y, x2: b.x, y2: b.y }, cx, cy, r)) return true;
      const cross = (b.x - a.x) * (cy - a.y) - (b.y - a.y) * (cx - a.x);
      if (cross > 0) positive = true;
      if (cross < 0) negative = true;
    }
    return points.length >= 3 && !(positive && negative);
  }

  /**
   * 线段是否命中多个圆（批量判定，返回命中集合）
   * @param {Array} segments 刀锋线段数组
   * @param {Array<{x,y,r,obj}>} circles 圆形碰撞体数组
   * @returns {Set} 命中的 obj 集合
   */
  static hitTestAll(segments, circles) {
    const hit = new Set();
    for (const seg of segments) {
      for (const c of circles) {
        if (hit.has(c.obj)) continue;
        const bladeRadius = Number.isFinite(seg.radius) ? Math.max(0, seg.radius) : 0;
        const touched = seg.polygon ? this.polygonHitsCircle(seg.polygon, c.x, c.y, c.r) :
          this.segHitsCircle(seg, c.x, c.y, c.r + bladeRadius);
        if (touched) {
          hit.add(c.obj);
        }
      }
    }
    return hit;
  }
}
