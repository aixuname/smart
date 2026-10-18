import { gestureScreenPosition } from "./input/gestureMapping.js";

export function trackingFeedback(client, now = performance.now()) {
  const g = client.lastGesture;
  const s = client.status;
  const fresh = Number.isFinite(g.receivedAt) && now - g.receivedAt <= 300;
  if (client.isConnected && fresh && g.visible && Number.isFinite(g.x) && Number.isFinite(g.y)) {
    return { tracked: true, active: g.active !== false, gesture: g,
      title: g.active !== false ? "手掌已识别 · 跟手出刀" : "手掌已识别 · 等待出刀动作",
      detail: "移动手掌，绿色光圈就是刀锋的位置。" };
  }
  if (!client.isConnected) return { title: "手势服务未连接", detail: "正在重连。可先使用鼠标，或重新启动游戏服务。" };
  if (s.cameraDisabled) return { title: "摄像头未开启", detail: "请正常启动游戏以启用摄像头，或选择鼠标操作。" };
  if (s.initializing) return { title: "正在准备手部识别", detail: "模型加载完成后，请把整只手放入摄像头画面。" };
  if (s.modelMissing || s.error || !s.cameraOk) return { title: "摄像头或识别暂不可用", detail: s.error || "打开识别设置，检查摄像头或点击重连。" };
  if (!fresh) return { title: "暂未收到新的手部坐标", detail: "打开识别设置查看画面，必要时重连摄像头。" };
  return { title: "尚未识别到手掌", detail: "把整只手放入画面并张开手指；出现绿色跟手光圈后即可开切。" };
}

export function setupHandFeedback({ client, getOptions, isEnabled, isPlaying }) {
  const cursor = document.getElementById("hand-cursor");
  const notice = document.getElementById("hand-tracking-notice");
  const status = document.getElementById("status-hand");
  const title = document.getElementById("tracking-notice-title");
  const detail = document.getElementById("tracking-notice-detail");
  let lostSince = null;
  let lastStatus = "";
  function update(now) {
    const enabled = isEnabled();
    const feedback = trackingFeedback(client, now);
    const tracked = enabled && !document.hidden && feedback.tracked;
    cursor.classList.toggle("hidden", !tracked);
    status.classList.toggle("hidden", !enabled);
    if (tracked) {
      const p = gestureScreenPosition(feedback.gesture, getOptions(), innerWidth, innerHeight);
      // The tip uses the exact same mapping as the game's collision input.
      cursor.style.transform = `translate3d(${p.x}px, ${p.y}px, 0)`;
      cursor.classList.toggle("cursor-idle", !feedback.active);
      cursor.classList.toggle("cursor-left", p.x > innerWidth * 0.72);
      cursor.classList.toggle("cursor-top", p.y > innerHeight * 0.8);
      cursor.querySelector("span").textContent = feedback.active ? "刀锋位置" : "移动中 · 未出刀";
      lostSince = null;
    } else if (lostSince === null) lostSince = now;
    const text = enabled ? feedback.title : "";
    if (text !== lastStatus) {
      status.textContent = text;
      status.dataset.tracked = String(!!tracked);
      title.textContent = feedback.title;
      detail.textContent = feedback.detail;
      lastStatus = text;
    }
    const missing = enabled && isPlaying() && !tracked && now - lostSince > 650;
    notice.classList.toggle("hidden", !missing);
    requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}
