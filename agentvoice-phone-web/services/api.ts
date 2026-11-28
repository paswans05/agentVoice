"use client";

export interface AgentSummary {
  id: string;
  name: string;
  type: string;
  status: string;
}

export function resolveApiBase(override?: string): string {
  if (override && override.trim()) return override.trim().replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "http://127.0.0.1:8000";
}

export async function pairSafariDevice(
  apiBase: string,
  payload: {
    pairing_code: string;
    device_name: string;
    platform_version: string;
  },
) {
  const res = await fetch(`${resolveApiBase(apiBase)}/api/v1/devices/pair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pairing_code: payload.pairing_code,
      device_name: payload.device_name,
      platform: "ios",
      platform_version: payload.platform_version,
      app_version: "0.1.0-safari",
      capability_profile: {
        platform: "ios",
        cellular_call_initiation: false,
        cellular_call_state: false,
        cellular_audio_capture: false,
        cellular_audio_injection: false,
        cellular_audio_bridge_status: "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE",
        voip_supported: true,
        callkit_supported: false,
        webrtc_supported: typeof RTCPeerConnection !== "undefined",
        browser: "Safari",
        device_health: true,
        ai_call_ready: false,
      },
    }),
  });
  const body = await res.json();
  if (!res.ok || !body.success) {
    throw new Error(body.error?.message || body.detail || `Pairing failed (${res.status})`);
  }
  return body.data as {
    device: { id: string; device_name: string; device_status: string };
    device_token: string;
    token_expires_at: string;
  };
}

export async function sendSafariHeartbeat(
  apiBase: string,
  deviceId: string,
  deviceToken: string,
  micPermission: string,
) {
  const res = await fetch(
    `${resolveApiBase(apiBase)}/api/v1/devices/${encodeURIComponent(deviceId)}/heartbeat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Device-Token": deviceToken,
      },
      body: JSON.stringify({
        health: {
          network_type: "wifi",
          connected: typeof navigator !== "undefined" ? navigator.onLine : true,
          mic_permission: micPermission,
          page_visible: typeof document !== "undefined" ? document.visibilityState === "visible" : true,
          permissions: { microphone: micPermission === "granted" },
        },
      }),
    },
  );
  if (!res.ok) {
    throw new Error(`Heartbeat failed (${res.status})`);
  }
  return (await res.json()).data;
}

export async function listActiveAgents(apiBase: string): Promise<AgentSummary[]> {
  const res = await fetch(`${resolveApiBase(apiBase)}/api/v1/agents`);
  const body = await res.json();
  if (!res.ok || !body.success) return [];
  return (body.data as AgentSummary[]).filter((a) => a.status === "ACTIVE");
}

export async function createVoiceAndWebRTCSession(
  apiBase: string,
  deviceId: string,
  deviceToken: string,
  agentId: string,
) {
  const base = resolveApiBase(apiBase);
  const vsRes = await fetch(`${base}/api/v1/voice/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, allow_draft_preview: true }),
  });
  const vsBody = await vsRes.json();
  if (!vsRes.ok || !vsBody.success) {
    throw new Error(vsBody.error?.message || "Failed to start voice session.");
  }
  const voiceSessionId = vsBody.data.session_id as string;

  const wrtcRes = await fetch(`${base}/api/v1/webrtc/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Device-Token": deviceToken,
    },
    body: JSON.stringify({
      device_id: deviceId,
      agent_id: agentId,
      voice_session_id: voiceSessionId,
    }),
  });
  const wrtcBody = await wrtcRes.json();
  if (!wrtcRes.ok || !wrtcBody.success) {
    throw new Error(wrtcBody.error?.message || "Failed to start WebRTC session.");
  }
  return {
    voiceSessionId,
    webrtcSessionId: wrtcBody.data.id as string,
    stunUrls: (wrtcBody.data.stun_urls as string[]) || ["stun:stun.l.google.com:19302"],
  };
}

export async function terminateWebRTCSession(apiBase: string, webrtcSessionId: string) {
  await fetch(
    `${resolveApiBase(apiBase)}/api/v1/webrtc/sessions/${encodeURIComponent(webrtcSessionId)}/terminate`,
    { method: "POST" },
  );
}
