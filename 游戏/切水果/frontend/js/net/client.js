/**
 * 全局手势客户端单例。
 * 通过后端同源托管时直接使用 location.host；file:// 打开时回退 127.0.0.1:8000。
 */
import { GestureClient } from "./GestureClient.js";

function buildWsUrl() {
  const proto = location.protocol === "https:" ? "wss://" : "ws://";
  if (location.protocol !== "file:" && location.host) {
    return `${proto}${location.host}/ws`;
  }
  return `${proto}127.0.0.1:8000/ws`;
}

export const gestureClient = new GestureClient(buildWsUrl());
gestureClient.connect();
