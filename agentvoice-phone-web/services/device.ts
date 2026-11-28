"use client";

export interface BrowserDeviceIdentity {
  deviceId: string;
  deviceToken: string;
  deviceName: string;
  apiBaseUrl: string;
}

// Keep device credentials strictly in memory + sessionStorage (never localStorage).
let memoryIdentity: BrowserDeviceIdentity | null = null;

export function saveDeviceIdentity(identity: BrowserDeviceIdentity): void {
  memoryIdentity = identity;
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem("av_phone_device_id", identity.deviceId);
    window.sessionStorage.setItem("av_phone_device_token", identity.deviceToken);
    window.sessionStorage.setItem("av_phone_device_name", identity.deviceName);
    window.sessionStorage.setItem("av_phone_api_base", identity.apiBaseUrl);
  }
}

export function loadDeviceIdentity(): BrowserDeviceIdentity | null {
  if (memoryIdentity) return memoryIdentity;
  if (typeof window === "undefined") return null;
  const deviceId = window.sessionStorage.getItem("av_phone_device_id");
  const deviceToken = window.sessionStorage.getItem("av_phone_device_token");
  const deviceName = window.sessionStorage.getItem("av_phone_device_name") || "iPhone Safari";
  const apiBaseUrl =
    window.sessionStorage.getItem("av_phone_api_base") || window.location.origin;
  if (!deviceId || !deviceToken) return null;
  memoryIdentity = { deviceId, deviceToken, deviceName, apiBaseUrl };
  return memoryIdentity;
}

export function clearDeviceIdentity(): void {
  memoryIdentity = null;
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem("av_phone_device_id");
    window.sessionStorage.removeItem("av_phone_device_token");
    window.sessionStorage.removeItem("av_phone_device_name");
    window.sessionStorage.removeItem("av_phone_api_base");
  }
}

export function detectSafariCapabilities() {
  if (typeof window === "undefined") {
    return {
      isSecureContext: false,
      hasMediaDevices: false,
      hasWebRTC: false,
      hasWebSocket: false,
      userAgent: "",
    };
  }
  return {
    isSecureContext: window.isSecureContext,
    hasMediaDevices: Boolean(navigator.mediaDevices?.getUserMedia),
    hasWebRTC: typeof RTCPeerConnection !== "undefined",
    hasWebSocket: typeof WebSocket !== "undefined",
    userAgent: navigator.userAgent,
  };
}
