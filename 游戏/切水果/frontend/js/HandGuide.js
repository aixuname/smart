import { gestureScreenPosition } from './input/gestureMapping.js';
import { trackingFeedback } from './HandFeedback.js';
import { PreviewFeed } from './net/PreviewFeed.js';

export function guideGeometry(frame, live, options, rect, width, height) {
  const sx = options.sensitivity ?? 1;
  const sy = options.sensitivityY ?? sx;
  const area = { left: 0.5 + (options.offsetX || 0) - 0.5 / sx,
    top: 0.5 + (options.offsetY || 0) - 0.5 / sy, width: 1 / sx, height: 1 / sy };
  const x = options.mirrorX !== false ? 1 - frame.x : frame.x;
  const liveX = options.mirrorX !== false ? 1 - live.x : live.x;
  return {
    hand: { x: rect.left + x * rect.width, y: rect.top + frame.y * rect.height },
    blade: gestureScreenPosition(live, options, width, height),
    area,
    outside: liveX < area.left || liveX > area.left + area.width ||
      live.y < area.top || live.y > area.top + area.height,
  };
}

export function guideInstructions(settings = {}, options = {}) {
  const point = settings.blade_point_index ?? -1;
  const target = ({ '-1': '手掌整体', 0: '手腕', 8: '食指指尖', 12: '中指指尖' })[point] || '手部光圈';
  return {
    motion: `左右、上下移动${target}`,
    cut: settings.activation === 'pinch' ? '拇指与食指捏合时出刀。' :
      settings.activation === 'index' ? '伸直食指时出刀。' : '不用握拳或捏合，移动即可切水果。',
    direction: options.mirrorX !== false ? '镜像 · 手与刀左右同向' : '原画面 · 手与刀左右反向',
  };
}

export function setupHandGuide({ client, getOptions, isEnabled, isPlaying }) {
  const $ = id => document.getElementById(id);
  const panel = $('hand-guide');
  const body = $('hand-guide-body');
  const toggle = $('btn-hand-guide-toggle');
  const image = $('hand-guide-preview');
  const frame = $('hand-guide-frame');
  const marker = $('hand-guide-marker');
  const area = $('hand-guide-area');
  const connection = $('hand-guide-connection');
  const line = connection.querySelector('line');
  const lineWindow = $('hand-guide-line-window');
  const lineToggle = $('hand-guide-line-toggle');
  const hint = $('hand-guide-hint');
  const cutHint = $('hand-guide-cut');
  const direction = $('hand-guide-direction');
  const placeholder = $('hand-guide-placeholder');
  let collapsed = false;
  let ready = false;
  let previewGesture = null;
  let previewAt = -Infinity;
  let animation;
  const feed = new PreviewFeed(image, { interval: 150, onState(value, gesture) {
    ready = value;
    previewGesture = gesture;
    previewAt = performance.now();
    frame.classList.toggle('has-preview', value);
    if (value && image.naturalWidth && image.naturalHeight) {
      frame.style.aspectRatio = `${image.naturalWidth} / ${image.naturalHeight}`;
    }
  } });

  function setCollapsed() {
    collapsed = !collapsed;
    toggle.textContent = collapsed ? '展开预览' : '收起';
    toggle.setAttribute('aria-expanded', String(!collapsed));
    body.classList.toggle('hidden', collapsed);
    panel.classList.toggle('collapsed', collapsed);
    if (collapsed) {
      feed.setActive(false);
      connection.classList.add('hidden');
    }
  }
  toggle.addEventListener('click', setCollapsed);
  function suspendWhenHidden() {
    // Background tabs may stop rAF entirely, while fetch timers keep running.
    if (!document.hidden) return;
    feed.setActive(false);
    panel.classList.add('hidden');
    connection.classList.add('hidden');
    marker.classList.add('hidden');
  }
  document.addEventListener('visibilitychange', suspendWhenHidden);
  const setText = (el, text) => { if (el.textContent !== text) el.textContent = text; };
  function update(now) {
    const active = isEnabled() && isPlaying() && !document.hidden;
    panel.classList.toggle('hidden', !active);
    feed.setActive(active && !collapsed && client.isConnected && !client.status.cameraDisabled);
    connection.classList.add('hidden');
    marker.classList.add('hidden');
    if (active && !collapsed) {
      const options = getOptions();
      const instructions = guideInstructions(client.status.settings, options);
      const feedback = trackingFeedback(client, now);
      image.style.transform = options.mirrorX !== false ? 'scaleX(-1)' : 'none';
      setText(direction, instructions.direction);
      setText(cutHint, instructions.cut);
      setText(placeholder, feedback.tracked ? '预览暂不可用' : feedback.title);
      setText(hint, feedback.tracked ? `${instructions.motion}，让刀锋划过水果。` : '把整只手放进预览，张开手指。');
      // Anchor to the decoded photograph, not a newer WebSocket sample: both green rings
      // must stay on the hand they describe, even when preview and inference rates differ.
      const hasAnchor = ready && now - previewAt <= 600 && previewGesture?.visible &&
        Number.isFinite(previewGesture.x) && Number.isFinite(previewGesture.y);
      const geometry = guideGeometry(hasAnchor ? previewGesture : { x: 0, y: 0 },
        feedback.gesture || { x: 0.5, y: 0.5 }, options, frame.getBoundingClientRect(), innerWidth, innerHeight);
      for (const key of ['left', 'top', 'width', 'height']) area.style[key] = `${geometry.area[key] * 100}%`;
      const tracked = feedback.tracked && hasAnchor;
      panel.classList.toggle('guide-idle', tracked && !feedback.active);
      connection.classList.toggle('guide-idle', tracked && !feedback.active);
      if (tracked) {
        const rect = frame.getBoundingClientRect();
        marker.style.left = `${geometry.hand.x - rect.left}px`;
        marker.style.top = `${geometry.hand.y - rect.top}px`;
        marker.classList.remove('hidden');
        setText(marker.querySelector('span'), feedback.active ? '手' : '待机');
        if (geometry.outside) setText(hint, '手已到操作框外，向框内移动。');
        if (lineToggle.checked) {
          // Show the link over the photograph and game, while leaving the guide text clear.
          const bounds = panel.getBoundingClientRect();
          const rectangle = r => `M${r.left},${r.top}h${r.width}v${r.height}h${-r.width}Z`;
          lineWindow.setAttribute('d', rectangle({ left: 0, top: 0, width: innerWidth, height: innerHeight }) +
            rectangle(bounds) + rectangle(rect));
          line.setAttribute('x1', geometry.hand.x);
          line.setAttribute('y1', geometry.hand.y);
          line.setAttribute('x2', geometry.blade.x);
          line.setAttribute('y2', geometry.blade.y);
          connection.classList.remove('hidden');
        }
      }
    }
    animation = requestAnimationFrame(update);
  }
  animation = requestAnimationFrame(update);
  return { destroy() {
    cancelAnimationFrame(animation);
    feed.destroy();
    toggle.removeEventListener('click', setCollapsed);
    document.removeEventListener('visibilitychange', suspendWhenHidden);
    panel.classList.add('hidden');
    connection.classList.add('hidden');
  } };
}
