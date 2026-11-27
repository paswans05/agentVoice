"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { DeviceEventRecord, MobileDevice } from "@agentvoice/shared-types";
import { ArrowLeft, ShieldOff } from "lucide-react";

import {
  fetchDeviceEvents,
  fetchMobileDevice,
  revokeMobileDevice,
  sendDeviceCommand,
} from "@/lib/api-client";

export default function MobileDeviceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [device, setDevice] = useState<MobileDevice | null>(null);
  const [events, setEvents] = useState<DeviceEventRecord[]>([]);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [d, evs] = await Promise.all([fetchMobileDevice(id), fetchDeviceEvents(id)]);
    setDevice(d);
    setEvents(evs);
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!device) {
    return <div className="p-8 text-sm text-muted-foreground">Loading device...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/telephony/devices"
            className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Devices
          </Link>
          <div>
            <h1 className="text-xl font-semibold">{device.device_name}</h1>
            <p className="text-xs text-muted-foreground font-mono">
              {device.id} · {device.platform.toUpperCase()} {device.platform_version} · Status:{" "}
              {device.device_status}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={async () => {
              await sendDeviceCommand(device.id, "PING");
              setNotice("PING command queued.");
            }}
            className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted"
          >
            Send Ping
          </button>
          {device.device_status !== "REVOKED" && (
            <button
              type="button"
              onClick={async () => {
                await revokeMobileDevice(device.id);
                setNotice("Device credential revoked.");
                await load();
              }}
              className="inline-flex items-center gap-1 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-700 dark:text-rose-300"
            >
              <ShieldOff className="h-3.5 w-3.5" />
              Revoke Device
            </button>
          )}
        </div>
      </div>

      {notice && (
        <div className="rounded-lg border border-border bg-muted/40 p-3 text-xs">{notice}</div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-4 space-y-2 text-xs">
          <div className="font-semibold text-sm">Verified Capabilities</div>
          <div>Cellular Call Initiation: {String(device.capability_profile.cellular_call_initiation)}</div>
          <div>Cellular Call State: {String(device.capability_profile.cellular_call_state)}</div>
          <div>Cellular Audio Capture: {String(device.capability_profile.cellular_audio_capture)}</div>
          <div>Cellular Audio Injection: {String(device.capability_profile.cellular_audio_injection)}</div>
          <div className="font-mono text-amber-700 dark:text-amber-300">
            Bridge: {device.capability_profile.cellular_audio_bridge_status}
          </div>
          <div>VoIP Supported: {String(device.capability_profile.voip_supported)}</div>
          <div>CallKit Supported: {String(device.capability_profile.callkit_supported)}</div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 space-y-2 text-xs">
          <div className="font-semibold text-sm">Health & Permissions</div>
          <div>Battery: {device.health.battery_percent ?? "—"}%</div>
          <div>Network: {device.health.network_type}</div>
          <div>SIM Present: {String(device.health.sim_present ?? "Unknown")}</div>
          <div>Carrier: {device.health.carrier_name ?? "—"}</div>
          <div>
            Permissions:{" "}
            {Object.entries(device.health.permissions)
              .map(([k, v]) => `${k}=${v}`)
              .join(", ") || "None reported"}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-4 space-y-2">
        <div className="font-semibold text-sm">Device Events ({events.length})</div>
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {events.map((ev) => (
            <div key={ev.event_id} className="rounded border border-border p-2 text-xs">
              <span className="font-medium">{ev.event_type}</span> ·{" "}
              <span className="text-muted-foreground">
                {new Date(ev.timestamp).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
