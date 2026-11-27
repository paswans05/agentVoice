"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { LiveCallsWsFrame } from "@agentvoice/shared-types";

import { getLiveCallsWebSocketUrl } from "@/lib/api-client";

export type WsConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface UseLiveCallsWsOptions {
  callIds?: string[];
  campaignId?: string;
  agentId?: string;
  onFrame?: (frame: LiveCallsWsFrame) => void;
  enabled?: boolean;
}

export function useLiveCallsWebSocket(options: UseLiveCallsWsOptions = {}) {
  const { callIds, campaignId, agentId, onFrame, enabled = true } = options;
  const [connectionState, setConnectionState] = useState<WsConnectionState>("disconnected");
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState<string | null>(null);
  const onFrameRef = useRef(onFrame);
  onFrameRef.current = onFrame;

  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmountedRef = useRef(false);

  const sendSubscribe = useCallback(
    (ws: WebSocket) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      if (callIds?.length || campaignId || agentId) {
        ws.send(
          JSON.stringify({
            type: "SUBSCRIBE",
            call_ids: callIds,
            campaign_id: campaignId,
            agent_id: agentId,
          }),
        );
      }
    },
    [callIds, campaignId, agentId],
  );

  useEffect(() => {
    unmountedRef.current = false;
    if (!enabled) {
      setConnectionState("disconnected");
      return;
    }

    const connect = () => {
      if (unmountedRef.current) return;
      setConnectionState(retryCountRef.current > 0 ? "reconnecting" : "connecting");

      const ws = new WebSocket(getLiveCallsWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmountedRef.current) {
          ws.close();
          return;
        }
        retryCountRef.current = 0;
        setConnectionState("connected");
        sendSubscribe(ws);

        if (pingTimerRef.current) clearInterval(pingTimerRef.current);
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "PING" }));
          }
        }, 20000);
      };

      ws.onmessage = (event) => {
        try {
          const frame = JSON.parse(event.data) as LiveCallsWsFrame;
          if (frame.type === "PONG" || frame.type === "CONNECTED") {
            setLastHeartbeatAt(new Date().toISOString());
          }
          onFrameRef.current?.(frame);
        } catch {
          // Ignore malformed frame
        }
      };

      ws.onclose = () => {
        if (pingTimerRef.current) {
          clearInterval(pingTimerRef.current);
          pingTimerRef.current = null;
        }
        if (unmountedRef.current) {
          setConnectionState("disconnected");
          return;
        }
        setConnectionState("reconnecting");
        const baseDelay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
        const jitter = Math.floor(Math.random() * 400);
        retryCountRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, baseDelay + jitter);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled, sendSubscribe]);

  return { connectionState, lastHeartbeatAt };
}
