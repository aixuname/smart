/**
 * GestureClient —— 手势推流 WebSocket 客户端。
 *
 * 职责：
 *  1. 连接后端 ws://host/ws
 *  2. 断线自动重连（指数退避）
 *  3. 解析 {type:gesture|status} 消息，分发给订阅者
 *  4. 维护最近一次手势位置与后端状态（模型缺失/摄像头/帧率）
 */
export class GestureClient {
  /**
   * @param {string} url  WebSocket 地址，如 ws://127.0.0.1:8000/ws
   */
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.connected = false;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 10000;
    this.stopped = false;
    this.reconnectTimer = null;
    this._listeners = new Set();

    // 最新状态
    this.lastGesture = { x: 0, y: 0, visible: false, ts: 0 };
    this.status = { modelMissing: false, cameraOk: false, initializing: true, fps: 0 };
  }

  connect() {
    if (this.stopped || (this.ws && this.ws.readyState < 2)) return;
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectDelay = 1000;
      this._emit({ type: "connected" });
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        this._handle(msg);
      } catch (e) {
        /* 忽略非法消息 */
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.lastGesture = { x: 0, y: 0, visible: false, active: false, ts: 0 };
      this._emit({ type: "disconnected" });
      this._scheduleReconnect();
    };

    this.ws.onerror = () => {
      try { this.ws.close(); } catch (e) { /* noop */ }
    };
  }

  _handle(msg) {
    if (msg.type === "gesture") {
      if (!Number.isFinite(msg.x) || !Number.isFinite(msg.y)) return;
      this.lastGesture = { ...msg, receivedAt: performance.now() };
      this._emit(msg);
    } else if (msg.type === "status") {
      this.status = {
        modelMissing: !!msg.model_missing,
        cameraOk: !!msg.camera_ok,
        fps: msg.fps || 0,
        initializing: !!msg.initializing,
        cameraDisabled: !!msg.camera_disabled,
        error: msg.error || "",
        settings: msg.settings,
        revision: msg.revision,
        appliedRevision: msg.applied_revision,
        metrics: msg.metrics,
      };
      this._emit({ ...msg, ...this.status });
    }
  }

  _scheduleReconnect() {
    if (this.stopped || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
  }

  /** 订阅消息（connected/disconnected/gesture/status） */
  onMessage(cb) {
    this._listeners.add(cb);
    return () => this._listeners.delete(cb);
  }

  _emit(msg) {
    for (const cb of this._listeners) {
      try { cb(msg); } catch (e) { /* 订阅者异常不影响主流程 */ }
    }
  }

  get isConnected() {
    return this.connected;
  }

  /** 停止并断开（不再重连） */
  destroy() {
    this.stopped = true;
    clearTimeout(this.reconnectTimer);
    this.connected = false;
    this._listeners.clear();
    if (this.ws) {
      try { this.ws.close(); } catch (e) { /* noop */ }
    }
  }
}
