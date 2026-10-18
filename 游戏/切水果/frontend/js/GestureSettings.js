import { gestureClient } from "./net/client.js";
import { HandCalibration } from "./input/Calibration.js";
import { DEFAULT_GESTURE_OPTIONS } from "./input/gestureMapping.js";

export function setupGestureSettings({ getOptions, onOptions }) {
  const $ = (id) => document.getElementById(id);
  const fields = { camera_id: "camera", target_fps: "fps", smooth_alpha: "smooth",
    blade_point_index: "point", activation: "activation", pinch_threshold: "pinch", filter: "filter",
    min_detection_confidence: "detection" };
  let opened = false;
  let saving = 0;
  let loading = false;
  let loaded = false;
  let saveQueue = Promise.resolve();
  let savedPoint = -1;
  let pointRevision = null;
  let previewBusy = false;
  let imageUrl = null;
  const output = $("gesture-save-status");
  const preview = $("gesture-preview");
  const calibration = new HandCalibration();
  const calibrationOutput = $("gesture-calibration-status");
  let openGeneration = 0;
  let requestController = null;
  const pointLabel = value => ({ '-1': '手掌中心', 0: '手腕', 8: '食指指尖', 12: '中指指尖' })[value] || `关键点 ${value}`;

  function renderPointStatus() {
    const s = gestureClient.status;
    const g = gestureClient.lastGesture;
    const applied = gestureClient.isConnected && (
      (pointRevision !== null && g.revision >= pointRevision) ||
      (s.settings?.blade_point_index === savedPoint && s.appliedRevision === s.revision));
    $("gesture-point-status").textContent = loading ? "正在读取追踪位置…"
      : saving ? `正在切换到${pointLabel($("gesture-point").value)}…`
      : !loaded ? "暂时无法确认追踪位置，请重新打开设置。"
      : applied ? `当前追踪：${pointLabel(savedPoint)} · 移动光圈所在位置来控制刀锋。`
      : `已保存：${pointLabel(savedPoint)}，等待识别线程应用…`;
    $("btn-gesture-apply").disabled = loading || saving > 0 || !loaded;
    $("gesture-point").disabled = loading || !loaded;
  }
  preview.onload = () => {
    if (preview.naturalWidth && preview.naturalHeight) {
      preview.parentElement.style.aspectRatio = `${preview.naturalWidth} / ${preview.naturalHeight}`;
    }
  };

  function renderMapping() {
    const options = getOptions();
    for (const key of ["sensitivity", "sensitivityY", "offsetX", "offsetY"]) {
      $("gesture-" + key).value = options[key];
      $("gesture-" + key + "-value").textContent = Number(options[key]).toFixed(2);
    }
    preview.style.transform = options.mirrorX ? "scaleX(-1)" : "none";
    const area = $("gesture-workarea");
    const size = 100 / options.sensitivity;
    const height = 100 / options.sensitivityY;
    Object.assign(area.style, { width: size + "%", height: height + "%",
      left: (50 + options.offsetX * 100 - size / 2) + "%",
      top: (50 + options.offsetY * 100 - height / 2) + "%" });
  }

  for (const key of ["sensitivity", "sensitivityY", "offsetX", "offsetY"]) {
    $("gesture-" + key).addEventListener("input", () => {
      onOptions({ [key]: Number($("gesture-" + key).value) });
      renderMapping();
    });
  }
  for (const key of ["smooth", "pinch"]) {
    $("gesture-" + key).addEventListener("input", () => {
      $("gesture-" + key + "-value").textContent = Number($("gesture-" + key).value).toFixed(2);
    });
  }
  $("btn-gesture-center").onclick = () => {
    onOptions({ ...DEFAULT_GESTURE_OPTIONS });
    renderMapping();
  };
  $("btn-gesture-calibrate").onclick = () => {
    if (calibration.stage) {
      calibration.cancel();
      calibrationOutput.textContent = "已取消，原来的操作范围保持不变。";
      $("btn-gesture-calibrate").textContent = "标定操作范围";
    } else {
      calibration.start();
      calibrationMirror = getOptions().mirrorX;
      $("btn-gesture-calibrate").textContent = "取消标定";
    }
  };
  let calibrationMirror = true;
  $("btn-gesture-preset-save").onclick = () => {
    try {
      localStorage.setItem("fruit_flash_mapping", JSON.stringify(getOptions()));
      calibrationOutput.textContent = "个人映射已保存。";
    } catch (_) { calibrationOutput.textContent = "浏览器无法保存，请检查存储空间或隐私设置。"; }
  };
  $("btn-gesture-preset-load").onclick = () => {
    try {
      const saved = JSON.parse(localStorage.getItem("fruit_flash_mapping"));
      if (!saved) throw new Error("暂无已保存的个人映射。");
      const ranges = { sensitivity: [1, 5], sensitivityY: [1, 5], offsetX: [-0.4, 0.4], offsetY: [-0.4, 0.4] };
      const patch = {};
      for (const [key, [min, max]] of Object.entries(ranges)) {
        if (!Number.isFinite(saved[key]) || saved[key] < min || saved[key] > max) throw new Error("保存的映射无效，请重新标定。");
        patch[key] = saved[key];
      }
      onOptions(patch);
      renderMapping();
      calibrationOutput.textContent = "已载入个人映射，请确认镜像方向与保存时一致。";
    } catch (e) { calibrationOutput.textContent = e.message; }
  };

  async function request(url, body) {
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(5000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "请求失败");
    return data;
  }
  function saveSettings(settings) {
    saving++;
    renderPointStatus();
    // Serialize auto-save and the full form so rapid choices cannot arrive out
    // of order. Keep saving after closing the panel; reopening awaits this queue.
    saveQueue = saveQueue.then(async () => {
      output.textContent = "正在应用…";
      try {
        const data = await request("/api/settings", settings);
        savedPoint = data.settings.blade_point_index;
        pointRevision = data.revision;
        output.textContent = "设置已保存，正在交给识别线程应用。";
        onOptions({});
      } catch (e) {
        output.textContent = "应用失败：" + e.message;
        if (saving === 1) $("gesture-point").value = savedPoint;
      } finally {
        saving--;
        renderPointStatus();
      }
    });
    return saveQueue;
  }
  $("gesture-point").addEventListener("change", () => {
    if (!loaded) return;
    if (calibration.stage) {
      calibration.cancel();
      calibrationOutput.textContent = "追踪位置已改变，请重新标定操作范围。";
      $("btn-gesture-calibrate").textContent = "标定操作范围";
    }
    return saveSettings({ blade_point_index: Number($("gesture-point").value) });
  });
  $("btn-gesture-apply").onclick = () => {
    if (loading || saving || !loaded) return;
    const settings = {};
    for (const [key, id] of Object.entries(fields)) {
      const value = $("gesture-" + id).value;
      settings[key] = ["activation", "filter"].includes(key) ? value : Number(value);
    }
    return saveSettings(settings);
  };
  $("btn-gesture-retry").onclick = async () => {
    try {
      const data = await request("/api/retry", {});
      output.textContent = data.camera_disabled ? "当前使用 --no-camera 启动，请正常重启以启用手势。" : "已请求重连，请留意识别状态。";
    } catch (e) { output.textContent = "重连失败：" + e.message; }
  };

  async function tick() {
    if (!opened) return;
    renderPointStatus();
    const s = gestureClient.status;
    const stages = s.metrics?.stages_ms || {};
    const labels = { capture: "采集", inference: "推理", preview: "预览", processing: "处理总计", dispatch: "等待发送" };
    $("gesture-metrics").textContent = Object.entries(stages).map(([name, value]) =>
      `${labels[name] || name}: ${value.p50} / ${value.p95} ms`).join("；") || "等待采集数据…";
    const g = gestureClient.lastGesture;
    if (calibration.stage) {
      if (getOptions().mirrorX !== calibrationMirror) calibration.fail("镜像方向已改变，请重新标定。");
      else calibration.update(g, performance.now(), calibrationMirror);
      calibrationOutput.textContent = calibration.message();
      if (!calibration.stage) {
        $("btn-gesture-calibrate").textContent = "标定操作范围";
        if (calibration.result) { onOptions(calibration.result); renderMapping(); }
      }
    }
    const fresh = performance.now() - g.receivedAt < 400;
    const cameraReady = gestureClient.isConnected && s.cameraOk && !s.cameraDisabled && !s.error;
    const placeholder = preview.parentElement.querySelector(".preview-placeholder");
    placeholder.querySelector("span").textContent = s.initializing ? "正在准备摄像头" : cameraReady ? "把手放进画面" : "等待摄像头画面";
    placeholder.querySelector("small").textContent = s.initializing ? "画面即将显示，请稍候" : cameraReady ? `刀锋跟随${pointLabel(savedPoint)}，以光圈为准` : "连接设备，或先用鼠标体验";
    $("gesture-diagnostic").dataset.state = cameraReady ? "ok" : "waiting";
    $("gesture-diagnostic").textContent = !gestureClient.isConnected ? "手势服务未连接，正在重试；可使用鼠标。"
      : s.cameraDisabled ? "摄像头已禁用（--no-camera）"
      : s.initializing ? "正在加载手部模型，请稍候…"
      : s.error || (!s.cameraOk ? "等待摄像头画面…"
        : !fresh ? `暂未收到新的手部坐标 · ${s.fps} FPS` : g.visible
        ? `${g.active ? "出刀中" : "手已识别，等待出刀动作"} · ${s.fps} FPS${g.pinch_ratio != null ? " · 捏合比 " + g.pinch_ratio : ""}`
        : `未发现手部，请将整只手放入画面 · ${s.fps} FPS`);
    if (previewBusy || document.hidden || $("gesture-settings").classList.contains("hidden")) return;
    const generation = openGeneration;
    previewBusy = true;
    requestController = new AbortController();
    const timeout = setTimeout(() => requestController?.abort(), 2000);
    try {
      const response = await fetch("/api/preview.jpg", { cache: "no-store", signal: requestController.signal });
      if (!response.ok) { preview.style.visibility = "hidden"; return; }
      const blob = await response.blob();
      if (!opened || generation !== openGeneration) return;
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      imageUrl = URL.createObjectURL(blob);
      preview.src = imageUrl;
      preview.style.visibility = "visible";
    } catch (_) { preview.style.visibility = "hidden"; }
    finally {
      clearTimeout(timeout); previewBusy = false; requestController = null;
      preview.parentElement.classList.toggle("has-preview", preview.style.visibility === "visible");
    }
  }
  setInterval(tick, 150);
  return {
    renderMapping,
    async open() {
      opened = true;
      const generation = ++openGeneration;
      output.textContent = "";
      loading = true;
      loaded = false;
      renderPointStatus();
      renderMapping();
      try {
        await saveQueue;
        if (!opened || generation !== openGeneration) return;
        const response = await fetch("/api/settings", { signal: AbortSignal.timeout(5000) });
        if (!response.ok) throw new Error("无法读取识别设置");
        const settings = { min_detection_confidence: 0.35, ...await response.json() };
        if (!opened || generation !== openGeneration) return;
        if (savedPoint !== settings.blade_point_index) pointRevision = null;
        savedPoint = settings.blade_point_index;
        loaded = true;
        for (const [key, id] of Object.entries(fields)) {
          const el = $("gesture-" + id);
          if (el.tagName === "SELECT" && !Array.from(el.options).some(o => o.value === String(settings[key]))) {
            el.add(new Option(String(settings[key]), String(settings[key])));
          }
          el.value = settings[key];
        }
        for (const key of ["smooth", "pinch"]) $("gesture-" + key).dispatchEvent(new Event("input"));
      } catch (e) {
        if (opened && generation === openGeneration) output.textContent = e.message;
      } finally {
        if (generation === openGeneration) { loading = false; renderPointStatus(); }
      }
      tick();
    },
    close() {
      opened = false;
      openGeneration++;
      requestController?.abort();
      calibration.cancel();
      $("btn-gesture-calibrate").textContent = "标定操作范围";
      preview.removeAttribute("src");
      preview.style.visibility = "hidden";
      preview.parentElement.classList.remove("has-preview");
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      imageUrl = null;
    },
  };
}
