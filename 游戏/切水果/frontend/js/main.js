/**
 * main.js —— 游戏入口与 UI 控制器。
 * Phaser 场景 + DOM 覆盖层（主菜单/结算/排行榜）之间的桥接。
 */
import { Phaser } from "./phaser.js";
import { BootScene } from "./scenes/BootScene.js";
import { MenuScene } from "./scenes/MenuScene.js";
import { GameScene } from "./scenes/GameScene.js";
import { ResultScene } from "./scenes/ResultScene.js";
import { gestureClient } from "./net/client.js";
import { audio } from "./effects/audio.js";
import { setupGestureSettings } from "./GestureSettings.js";
import { storage, validRanks } from "./core/Storage.js";
import { setupHandFeedback } from "./HandFeedback.js";
import { setupHandGuide } from "./HandGuide.js";
import { DEFAULT_GESTURE_OPTIONS, restoreGestureOptions } from "./input/gestureMapping.js";

// ============================ Phaser ============================
const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game-container",
  transparent: true,
  backgroundColor: "#111b17",
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: "100%",
    height: "100%",
  },
  physics: {
    default: "arcade",
    arcade: { gravity: { y: 0 } },
  },
  scene: [BootScene, MenuScene, GameScene, ResultScene],
});

// 调试句柄（可访问 window.__game 检查游戏状态）
window.__game = game;

// ============================ DOM 工具 ============================
const $ = (sel) => document.querySelector(sel);
const show = (el, on) => {
  el.classList.toggle("hidden", !on);
  syncOverlayAccess();
};

function activeOverlay() {
  return ["input-config-overlay", "leaderboard-overlay", "result-overlay", "menu-overlay"]
    .map(id => document.getElementById(id)).find(el => !el.classList.contains("hidden"));
}
function syncOverlayAccess() {
  const top = activeOverlay();
  document.querySelectorAll(".overlay").forEach(el => { el.inert = el !== top; });
  $("#game-container").inert = !!top;
  $("#status-bar").inert = !!top && top.id !== "menu-overlay";
}
function focusDialog(overlay) {
  const panel = overlay.querySelector('[role="dialog"]');
  panel.tabIndex = -1;
  panel.focus({ preventScroll: true });
}

const menuOverlay = $("#menu-overlay");
const resultOverlay = $("#result-overlay");
const rankOverlay = $("#leaderboard-overlay");
const inputConfigOverlay = $("#input-config-overlay");
const guideTip = $("#guide-tip");
const statusModel = $("#status-model");
const statusFps = $("#status-fps");
const statusInputName = $("#status-input-name");

// 最近一次后端状态（用于菜单提示摄像头可用性）
let lastCameraOk = true;

// ============================ 偏好设置 ============================
let selectedMode = "endless";
let selectedInput = "gesture";
let gestureMirror = true; // 摄像头画面镜像：手与刀锋同向
let gestureOptions = { ...DEFAULT_GESTURE_OPTIONS };
let settingsPaused = false;
let settingsReturnFocus = null;
const currentGestureOptions = () => ({ ...gestureOptions, mirrorX: gestureMirror });
function applyLiveInput() {
  game.registry.set("input", selectedInput);
  game.registry.set("mirror", gestureMirror);
  game.registry.set("gestureOptions", currentGestureOptions());
  const scene = game.scene.getScene("GameScene");
  if (scene && (game.scene.isActive("GameScene") || game.scene.isPaused("GameScene"))) {
    scene.configureInput(selectedInput, currentGestureOptions());
  }
}
const gestureSettings = setupGestureSettings({
  getOptions: currentGestureOptions,
  onOptions(patch) {
    gestureOptions = { ...gestureOptions, ...patch };
    savePrefs();
    applyLiveInput();
  },
});
setupHandFeedback({ client: gestureClient, getOptions: currentGestureOptions,
  isEnabled: () => selectedInput === "gesture",
  isPlaying: () => game.scene.isActive("GameScene") });
setupHandGuide({ client: gestureClient, getOptions: currentGestureOptions,
  isEnabled: () => selectedInput === "gesture",
  isPlaying: () => game.scene.isActive("GameScene") && !game.scene.getScene("GameScene").over });
function openInputSettings() {
  if (!inputConfigOverlay.classList.contains("hidden")) return;
  settingsReturnFocus = document.activeElement;
  settingsPaused = game.scene.isActive("GameScene");
  if (settingsPaused) game.scene.pause("GameScene");
  show(inputConfigOverlay, true);
  applyMenuSelection();
  renderMenuStatusTip();
  gestureSettings.open();
  $(".input-config-panel").scrollTop = 0;
  focusDialog(inputConfigOverlay);
}
function closeInputSettings() {
  const wasOpen = !inputConfigOverlay.classList.contains("hidden");
  show(inputConfigOverlay, false);
  gestureSettings.close();
  applyLiveInput();
  if (settingsPaused) game.scene.resume("GameScene");
  settingsPaused = false;
  if (wasOpen && settingsReturnFocus?.isConnected) settingsReturnFocus.focus({ preventScroll: true });
}

function restorePrefs() {
  try {
    const p = JSON.parse(storage.get("fruit_flash_pref", "{}"));
    if (["endless", "timed", "demo"].includes(p.mode)) selectedMode = p.mode;
    if (["gesture", "mouse"].includes(p.input)) selectedInput = p.input;
    if (typeof p.mirror === "boolean") gestureMirror = p.mirror;
    gestureOptions = restoreGestureOptions(p.gesture, p.mappingVersion);
  } catch (e) { /* noop */ }
}
function savePrefs() {
  try {
    storage.set("fruit_flash_pref",
      JSON.stringify({ mode: selectedMode, input: selectedInput, mirror: gestureMirror,
        gesture: gestureOptions, mappingVersion: 2 }));
  } catch (_) { /* 当前会话仍然可用 */ }
}
function applyMenuSelection() {
  document.querySelectorAll(".mode-card").forEach((el) => {
    el.classList.toggle("active", el.dataset.mode === selectedMode);
    el.setAttribute("aria-pressed", String(el.dataset.mode === selectedMode));
  });
  // 识别模式小窗内的选项
  document.querySelectorAll(".input-big-opt").forEach((el) => {
    el.classList.toggle("active", el.dataset.input === selectedInput);
    el.setAttribute("aria-pressed", String(el.dataset.input === selectedInput));
  });
  // 主菜单入口按钮显示当前识别模式
  const valueEl = $("#input-config-value");
  if (valueEl) {
    valueEl.textContent = selectedInput === "gesture" ? "手势识别" : "鼠标操作";
  }
  // 镜像开关仅在手势模式下显示
  const row = $("#input-mirror-row");
  if (row) {
    row.classList.toggle("hidden", selectedInput !== "gesture");
    $("#input-mirror").checked = gestureMirror;
  }
  $("#gesture-settings").classList.toggle("hidden", selectedInput !== "gesture");
}

// ============================ 排行榜 ============================
const RANK_KEY = "fruit_flash_rank";
const MODE_NAMES = { endless: "无尽", timed: "限时", demo: "演示" };

function getRanks() {
  try {
    return validRanks(JSON.parse(storage.get(RANK_KEY, "[]")));
  } catch (e) {
    return [];
  }
}

/** 排行榜当前筛选模式：all / endless / timed / demo */
let rankFilter = "all";

function setRankFilter(mode) {
  rankFilter = mode;
  document.querySelectorAll(".rank-tab").forEach((button) =>
    button.classList.toggle("active", button.dataset.rmode === rankFilter)
  );
}

/** 按模式过滤（null/'all' 返回全部），并降序排序 */
function ranksOf(mode) {
  const ranks = getRanks();
  if (!mode || mode === "all") return ranks.slice().sort((a, b) => b.score - a.score);
  return ranks.filter((r) => r.mode === mode).sort((a, b) => b.score - a.score);
}

/** 保存成绩，返回 {idx, ...entry}（idx=-1 表示未进该模式前十） */
function saveRank(name, score, mode) {
  const ranks = getRanks();
  const entry = { name, score, mode, date: Date.now() };
  ranks.push(entry);
  const trimmed = ["endless", "timed", "demo"].flatMap(m => ranks.filter(r => r.mode === m).sort((a, b) => b.score - a.score).slice(0, 10));
  storage.set(RANK_KEY, JSON.stringify(trimmed));
  const modeList = ranksOf(mode).slice(0, 10);
  const idx = modeList.findIndex(
    (r) => r.date === entry.date && r.score === entry.score && r.name === entry.name
  );
  return Object.assign(entry, { idx });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/**
 * 渲染排行榜列表
 * @param {string} sel 容器选择器
 * @param {number} highlightIdx 高亮行下标（null 不显示）
 */
function renderRankList(sel, highlightIdx) {
  const container = $(sel);
  const ranks = ranksOf(rankFilter).slice(0, 10);
  if (!ranks.length) {
    container.innerHTML = '<div class="rank-empty">暂无纪录，快来创造第一个纪录吧！</div>';
    return;
  }
  const medals = ["🥇", "🥈", "🥉"];
  container.innerHTML = ranks.map((r, i) => {
    const cls = [
      "rank-row",
      i === 0 ? "top1" : i === 1 ? "top2" : i === 2 ? "top3" : "",
      i === highlightIdx ? "current" : "",
    ].join(" ");
    return `<div class="${cls}">
      <div class="rank-idx">${medals[i] || i + 1}</div>
      <div class="rank-name">${escapeHtml(r.name)}</div>
      <div class="rank-score">${r.score}</div>
      <div class="rank-mode">${MODE_NAMES[r.mode] || r.mode || ""}</div>
    </div>`;
  }).join("");
}

// ============================ 结算面板 ============================
function animateNumber(el, target, dur = 800) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = target; return; }
  const start = performance.now();
  function tick(now) {
    const t = Math.min(1, (now - start) / dur);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(target * eased);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function fillResult(data) {
  animateNumber($("#result-score"), data.score || 0);
  $("#result-combo").textContent = data.maxCombo || 0;
  $("#result-sliced").textContent = data.sliced || 0;
  $("#result-miss").textContent = data.misses || 0;
  const nameInput = $("#nickname-input");
  nameInput.disabled = false;
  nameInput.value = storage.get("fruit_flash_name", "");
  const btn = $("#btn-save-rank");
  btn.disabled = false;
  btn.textContent = "保存成绩";
  renderRankList("#rank-list", null);
}

// ============================ 场景事件 -> DOM ============================
game.events.on("ui:menu", () => {
  document.body.dataset.screen = "menu";
  show($("#btn-live-config"), false);
  show($("#btn-live-menu"), false);
  gestureSettings.close();
  show(menuOverlay, true);
  show(resultOverlay, false);
  show(rankOverlay, false);
  show(inputConfigOverlay, false);
  applyMenuSelection();
  renderMenuStatusTip();
});
game.events.on("ui:game", () => {
  document.body.dataset.screen = "game";
  show($("#btn-live-config"), true);
  show($("#btn-live-menu"), true);
  show(inputConfigOverlay, false);
  gestureSettings.close();
  show(menuOverlay, false);
  show(resultOverlay, false);
  show(rankOverlay, false);
});
game.events.on("ui:result", (data) => {
  document.body.dataset.screen = "result";
  show($("#btn-live-config"), false);
  show($("#btn-live-menu"), false);
  if (data && typeof data.score === "number") {
    fillResult(data);
    show(resultOverlay, true);
    focusDialog(resultOverlay);
  }
});
game.events.on("ui:guide", (on) => show(guideTip, on));

// ============================ 菜单交互 ============================
document.querySelectorAll(".mode-card").forEach((el) => {
  el.addEventListener("click", () => {
    selectedMode = el.dataset.mode;
    savePrefs();
    applyMenuSelection();
  });
});
// 识别模式小窗
$("#btn-input-config").addEventListener("click", () => {
  audio.unlock();
  audio.button();
  openInputSettings();
});
$("#btn-input-done").addEventListener("click", () => {
  audio.button();
  closeInputSettings();
});
inputConfigOverlay.addEventListener("click", (e) => {
  if (e.target === inputConfigOverlay) closeInputSettings();
});
document.querySelectorAll(".input-big-opt").forEach((el) => {
  el.addEventListener("click", () => {
    audio.unlock();
    audio.button();
    selectedInput = el.dataset.input;
    savePrefs();
    applyMenuSelection();
    renderMenuStatusTip();
    refreshStatusInputName(); // 状态条"输入方式"跟随切换
    applyLiveInput();
  });
});
$("#input-mirror").addEventListener("change", () => {
  gestureMirror = $("#input-mirror").checked;
  savePrefs();
  applyLiveInput();
  gestureSettings.renderMapping();
});
$("#btn-input-close").addEventListener("click", () => {
  audio.button();
  closeInputSettings();
});

$("#btn-start").addEventListener("click", () => {
  audio.unlock();
  audio.button();
  game.registry.set("mode", selectedMode);
  game.registry.set("input", selectedInput);
  game.registry.set("mirror", gestureMirror);
  game.registry.set("gestureOptions", currentGestureOptions());
  game.scene.stop("MenuScene");
  game.scene.stop("ResultScene");
  game.scene.start("GameScene", { mode: selectedMode, input: selectedInput });
});

$("#btn-rank").addEventListener("click", () => {
  audio.unlock();
  audio.button();
  renderRankList("#leaderboard-list", null);
  show(rankOverlay, true);
  focusDialog(rankOverlay);
});

// 排行榜模式筛选 Tab
document.querySelectorAll(".rank-tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    audio.unlock();
    audio.button();
    setRankFilter(btn.dataset.rmode || "all");
    renderRankList("#leaderboard-list", null);
    renderRankList("#rank-list", null);
  });
});
$("#btn-rank-back").addEventListener("click", () => {
  audio.button();
  show(rankOverlay, false);
  $("#btn-rank").focus({ preventScroll: true });
});

// ============================ 结算交互 ============================
$("#btn-save-rank").addEventListener("click", () => {
  const name = $("#nickname-input").value.trim() || "匿名水果忍者";
  storage.set("fruit_flash_name", name);
  const result = game.registry.get("lastResult") || {};
  const entry = saveRank(name, result.score || 0, result.mode || selectedMode);
  setRankFilter(result.mode || selectedMode);
  if (entry.idx >= 0) {
    audio.rankUp();
    renderRankList("#rank-list", entry.idx);
  } else {
    audio.button();
    renderRankList("#rank-list", null);
    $("#btn-save-rank").textContent = "未进前十，加油！";
  }
  $("#nickname-input").disabled = true;
  $("#btn-save-rank").disabled = true;
  if (entry.idx >= 0) $("#btn-save-rank").textContent = "已上榜";
  if (!storage.persistent) $("#btn-save-rank").textContent = "已保存到本次会话";
});

$("#btn-retry").addEventListener("click", () => {
  audio.unlock();
  audio.button();
  game.scene.stop("ResultScene");
  game.scene.start("GameScene", { mode: selectedMode, input: selectedInput });
});

$("#btn-menu").addEventListener("click", () => {
  audio.button();
  game.scene.stop("ResultScene");
  game.scene.stop("GameScene");
  game.scene.start("MenuScene");
});

$("#btn-live-config").addEventListener("click", openInputSettings);
$("#btn-check-tracking").addEventListener("click", openInputSettings);
$("#btn-use-mouse").addEventListener("click", () => {
  selectedInput = "mouse";
  savePrefs();
  applyMenuSelection();
  refreshStatusInputName();
  applyLiveInput();
});
$("#btn-live-menu").addEventListener("click", () => {
  closeInputSettings();
  game.scene.stop("GameScene");
  game.scene.start("MenuScene");
});

// ============================ 状态条 ============================
function renderMenuStatusTip() {
  const tip = $("#menu-tip");
  if (selectedInput === "gesture") {
    if (!gestureClient.isConnected) {
      tip.textContent = "手势服务不可用（请先启动后端或切换鼠标操作）";
      tip.classList.remove("hidden");
    } else if (gestureClient.status.modelMissing || gestureClient.status.cameraDisabled) {
      tip.textContent = gestureClient.status.error || "手势不可用，鼠标仍可使用";
      tip.classList.remove("hidden");
    } else if (lastCameraOk === false) {
      tip.textContent = "摄像头不可用（请检查摄像头连接，或切换鼠标操作）";
      tip.classList.remove("hidden");
    } else {
      tip.classList.add("hidden");
    }
  } else {
    tip.classList.add("hidden");
  }
}

gestureClient.onMessage((msg) => {
  if (msg.type === "connected") {
    statusModel.textContent = "手势服务：已连接";
    statusModel.className = "status-model-ok";
    renderMenuStatusTip(); // 连接恢复时刷新菜单提示（避免残留"不可用"警告）
  } else if (msg.type === "disconnected") {
    statusModel.textContent = "手势服务：未连接";
    statusModel.className = "status-model-missing";
    renderMenuStatusTip();
  } else if (msg.type === "status") {
    if (typeof msg.cameraOk === "boolean") {
      lastCameraOk = msg.cameraOk;
      renderMenuStatusTip();
    }
    if (msg.initializing) {
      statusModel.textContent = "手势：初始化中";
      statusModel.className = "status-model-missing";
    } else if (msg.modelMissing || !msg.cameraOk || msg.cameraDisabled || msg.error) {
      statusModel.textContent = msg.modelMissing ? "模型不可用 · 鼠标可用" : "摄像头/识别不可用 · 鼠标可用";
      statusModel.className = "status-model-missing";
    } else {
      statusModel.textContent = "手势服务：已连接";
      statusModel.className = "status-model-ok";
    }
    statusFps.textContent = `手势FPS ${msg.fps || 0}`;
    statusModel.title = msg.error || "";
  }
});

// 输入方式指示（跟随 GestureBladeInput 活跃状态，由 GameScene 的 HUD 显示，
// 这里仅静态展示菜单中选择的输入方式）
function refreshStatusInputName() {
  statusInputName.textContent = selectedInput === "gesture" ? "手势" : "鼠标";
}
document.addEventListener("keydown", (e) => {
  const overlay = activeOverlay();
  if (e.key === "Tab" && overlay) {
    const controls = [...overlay.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, [tabindex="0"]')]
      .filter(el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden");
    const first = controls[0], last = controls.at(-1);
    if (first && ((!e.shiftKey && (document.activeElement === last || !controls.includes(document.activeElement))) ||
        (e.shiftKey && (document.activeElement === first || !controls.includes(document.activeElement))))) {
      e.preventDefault();
      (e.shiftKey ? last : first).focus();
    }
    return;
  }
  if (e.key === "Escape") {
    if (!inputConfigOverlay.classList.contains("hidden")) closeInputSettings();
    else if (!rankOverlay.classList.contains("hidden")) $("#btn-rank-back").click();
    else if (game.scene.isActive("GameScene")) openInputSettings();
    return;
  }
  if (["BUTTON", "INPUT", "SELECT", "TEXTAREA", "SUMMARY"].includes(e.target.tagName)) return;
  if (e.key === "Enter") {
    if (!inputConfigOverlay.classList.contains("hidden")) {
      $("#btn-input-done").click();
    } else if (!menuOverlay.classList.contains("hidden")) {
      $("#btn-start").click();
    }
  }
});

document.addEventListener("visibilitychange", () => {
  if (document.hidden && game.scene.isActive("GameScene")) openInputSettings();
});

// ============================ 启动 ============================
restorePrefs();
document.body.dataset.screen = "menu";
syncOverlayAccess();
applyMenuSelection();
refreshStatusInputName();
