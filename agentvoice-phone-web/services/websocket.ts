"use client";

import { resolveApiBase } from "./api";

export function connectDeviceWebSocket(
  apiBase: string,
  deviceId: string,
  deviceToken: string,
  onStatus: (state: "connected" | "reconnecting" | "disconnected") => void,
): () => void {
  let closed = false;
  let retry = 0;
  let ws: WebSocket | null = null;
  let pingTimer: ReturnType<typeof setInterval> | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const wsBase = resolveApiBase(apiBase).replace(/^http/, "ws");

  const connect = () => {
    if (closed) return;
    ws = new WebSocket(
      `${wsBase}/api/v1/devices/ws?device_id=${encodeURIComponent(deviceId)}&token=${encodeURIComponent(deviceToken)}`,
    );
    ws.onopen = () => {
      retry = 0;
      onStatus("connected");
      if (pingTimer) clearInterval(pingTimer);
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "PING" }));
        }
      }, 20000);
    };
    ws.onclose = () => {
      if (pingTimer) clearInterval(pingTimer);
      if (closed) {
        onStatus("disconnected");
        return;
      }
      onStatus("reconnecting");
      const delay = Math.min(1000 * Math.pow(2, retry), 20000);
      retry += 1;
      retryTimer = setTimeout(connect, delay);
    };
    ws.onerror = () => ws?.close();
  };

  connect();
  return () => {
    closed = true;
    if (pingTimer) clearInterval(pingTimer);
    if (retryTimer) clearTimeout(retryTimer);
    ws?.close();
  };
}
