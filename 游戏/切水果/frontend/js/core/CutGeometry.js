// Pixel dimensions shared by the visible silver blade and its cutting volume.
export const TIP_RADIUS = 14;
export const BLADE_LENGTH = 35;
export const BLADE_HALF_WIDTH = 8;
export const SILVER_BLADE_POINTS = Object.freeze([
  [0, 0], [-23, -BLADE_HALF_WIDTH], [-BLADE_LENGTH, -5],
  [-BLADE_LENGTH, 5], [-23, BLADE_HALF_WIDTH],
]);

export function handBladeContacts(pos, rotation) {
  return [
    { x1: pos.x, y1: pos.y, x2: pos.x, y2: pos.y, radius: TIP_RADIUS },
    { polygon: SILVER_BLADE_POINTS.map(([x, y]) => ({
      x: pos.x + x * Math.cos(rotation) - y * Math.sin(rotation),
      y: pos.y + x * Math.sin(rotation) + y * Math.cos(rotation),
    })) },
  ];
}

export function fruitCircle(sprite) {
  const bomb = sprite.getData('isBomb');
  // BootScene draws fruit at (32,32), r30; bomb body at (32,36), r28 in 64px textures.
  const offset = bomb ? 4 * sprite.scaleY : 0;
  return { x: sprite.x - Math.sin(sprite.rotation) * offset,
    y: sprite.y + Math.cos(sprite.rotation) * offset,
    r: Math.max(sprite.displayWidth, sprite.displayHeight) * (bomb ? 28 : 30) / 64,
    obj: sprite };
}
