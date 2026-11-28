"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mic, Phone, ShieldAlert, Wifi } from "lucide-react";

import { sendSafariHeartbeat } from "@/services/api";
import { clearDeviceIdentity, loadDeviceIdentity } from "@/services/device";
import { connectDeviceWebSocket } from "@/services/websocket";

export default function GatewayPage() {
  const router = useRouter();
  const [deviceName, setDeviceName] = useState("iPhone Safari");
  const [wsState, setWsState] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");
  const [lastSync, setLastSync] = useState<string>("—");
  const [dialNumber, setDialNumber] = useState("");

  useEffect(() => {
    const id = loadDeviceIdentity();
    if (!id) {
      router.replace("/pair");
      return;
    }
    setDeviceName(id.deviceName);
    const disconnect = connectDeviceWebSocket(id.apiBaseUrl, id.deviceId, id.deviceToken, setWsState);

    const sync = () => {
      void sendSafariHeartbeat(id.apiBaseUrl, id.deviceId, id.deviceToken, "prompt")
        .then(() => setLastSync(new Date().toLocaleTimeString()))
        .catch(() => {});
    };
    sync();
    const timer = setInterval(sync, 25000);
    return () => {
      disconnect();
      clearInterval(timer);
    };
  }, [router]);

  const handleDialerHandoff = () => {
    const cleaned = dialNumber.trim();
    if (!cleaned) return;
    window.location.href = `tel:${cleaned}`;
  };

  return (
    <div className="mx-auto max-w-md space-y-5 p-4 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{deviceName}</h1>
          <p className="text-xs text-zinc-400">Safari Gateway · Last Heartbeat: {lastSync}</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-zinc-700 px-2.5 py-1 text-xs">
          <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          {wsState}
        </span>
      </div>

      <div className="grid gap-3">
        <Link
          href="/voice-test"
          className="flex items-center justify-between rounded-xl bg-blue-600 p-4 text-sm font-semibold text-white"
        >
          <span>Open Mic Test & AI Voice Call</span>
          <Mic className="h-5 w-5" />
        </Link>
        <Link
          href="/settings"
          className="rounded-xl border border-zinc-800 bg-zinc-900 p-3.5 text-xs text-zinc-300"
        >
          Device Settings & Disconnect
        </Link>
      </div>

      {/* Cellular Dialer Handoff */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 space-y-3">
        <div className="flex items-start gap-2 text-xs text-amber-200">
          <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
          <span>
            <strong>Cellular Dialer Handoff — AI audio bridge unavailable.</strong> Safari cannot
            provide cellular SIM call audio to the AI.
          </span>
        </div>
        <div className="flex gap-2">
          <input
            type="tel"
            value={dialNumber}
            onChange={(e) => setDialNumber(e.target.value)}
            placeholder="+919876543210"
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-white"
          />
          <button
            type="button"
            onClick={handleDialerHandoff}
            className="inline-flex items-center gap-1 rounded-lg border border-amber-500/40 px-3 py-2 text-xs font-medium text-amber-200"
          >
            <Phone className="h-3.5 w-3.5" />
            Dial
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={() => {
          clearDeviceIdentity();
          router.replace("/pair");
        }}
        className="w-full rounded-xl border border-zinc-800 py-2.5 text-xs text-zinc-400"
      >
        Unpair This Browser Session
      </button>
    </div>
  );
}
