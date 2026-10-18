export const DEFAULT_GESTURE_OPTIONS = Object.freeze({
  sensitivity: 1, sensitivityY: 1, offsetX: 0, offsetY: 0,
});

export function restoreGestureOptions(saved = {}, version = 1) {
  const result = { ...DEFAULT_GESTURE_OPTIONS };
  if (!saved || typeof saved !== 'object') return result;
  for (const [key, min, max] of [["sensitivity", 1, 5], ["sensitivityY", 1, 5],
    ["offsetX", -0.4, 0.4], ["offsetY", -0.4, 0.4]]) {
    if (Number.isFinite(saved[key])) result[key] = Math.max(min, Math.min(max, saved[key]));
  }
  if (!Number.isFinite(saved.sensitivityY)) result.sensitivityY = result.sensitivity;
  // Older defaults cropped away the outer 14% on every side. Preserve custom calibration.
  if (version < 2 && result.sensitivity === 1.4 && result.sensitivityY === 1.4 &&
      result.offsetX === 0 && result.offsetY === 0) return { ...DEFAULT_GESTURE_OPTIONS };
  return result;
}

export function mapGesture(point, opts = {}) {
  const clamp = (v) => Math.max(0, Math.min(1, v));
  const sensitivity = opts.sensitivity ?? DEFAULT_GESTURE_OPTIONS.sensitivity;
  const x = opts.mirrorX !== false ? 1 - point.x : point.x;
  return {
    x: clamp((x - 0.5 - (opts.offsetX || 0)) * sensitivity + 0.5),
    y: clamp((point.y - 0.5 - (opts.offsetY || 0)) * (opts.sensitivityY ?? sensitivity) + 0.5),
  };
}

export function gestureScreenPosition(point, opts, width, height) {
  const p = mapGesture(point, opts);
  // The visible tip and collision input share this inset; never draw the tip outside the canvas.
  const insetX = Math.min(24, width / 2);
  const insetY = Math.min(24, height / 2);
  return { x: Math.max(insetX, Math.min(width - insetX, p.x * width)),
    y: Math.max(insetY, Math.min(height - insetY, p.y * height)) };
}
