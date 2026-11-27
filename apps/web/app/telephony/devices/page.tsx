"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { MobileDevice } from "@agentvoice/shared-types";
import {
  ArrowLeft,
  Battery,
  Eye,
  Plus,
  RefreshCw,
  ShieldAlert,
  Smartphone,
  Wifi,
} from "lucide-react";

import { fetchMobileDevices, revokeMobileDevice } from "@/lib/api-client";

export default function MobileDevicesPage() {
  const [devices, setDevices] = useState<MobileDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadDevices = useCallback(async () => {
    try {
      setDevices(await fetchMobileDevices());
      setErrorMsg(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load mobile devices.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDevices();
  }, [loadDevices]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/telephony"
            className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Telephony
          </Link>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Mobile Devices</h1>
            <p className="text-xs text-muted-foreground">
              Android Device Gateways & iPhone Companions. Cellular audio is never misrepresented as
              AI-call-ready.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadDevices()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <Link
            href="/telephony/devices/wizard"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Mobile Device
          </Link>
        </div>
      </div>

      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2">
        <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
        <span>
          <strong>Capability Honesty:</strong> Pairing a device or initiating a cellular call does not
          enable cellular AI voice conversations. Actual AI-to-customer calls require an authorized
          SIP/Asterisk TelephonyProvider or AgentVoice VoIP endpoint.
        </span>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-sm text-muted-foreground">Loading devices...</div>
      ) : devices.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
          <Smartphone className="mx-auto h-8 w-8 text-muted-foreground/60" />
          <div className="text-sm font-medium">No mobile devices paired</div>
          <p className="text-xs text-muted-foreground">
            Use the 6-step Mobile Device Configuration Wizard to pair an Android or iPhone device.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {devices.map((d) => (
            <div
              key={d.id}
              className="rounded-xl border border-border bg-card p-4 flex flex-wrap items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Smartphone className="h-4 w-4 text-primary" />
                  <span className="font-semibold text-sm">{d.device_name}</span>
                  <span className="rounded bg-muted px-2 py-0.5 font-mono text-[11px]">
                    {d.platform.toUpperCase()} {d.platform_version}
                  </span>
                  <span className="rounded border px-2 py-0.5 text-[11px] font-medium">
                    {d.device_status}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Battery className="h-3.5 w-3.5" />
                    {d.health.battery_percent != null ? `${d.health.battery_percent}%` : "—"}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Wifi className="h-3.5 w-3.5" />
                    {d.health.network_type}
                  </span>
                  <span>
                    SIM: {d.health.sim_present === true ? "Present" : d.health.sim_present === false ? "Absent" : "Unknown"}
                  </span>
                  <span className="font-mono text-[11px]">
                    {d.capability_profile.cellular_audio_bridge_status}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/telephony/devices/${d.id}`}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Inspect
                </Link>
                {d.device_status !== "REVOKED" && (
                  <button
                    type="button"
                    onClick={() => void revokeMobileDevice(d.id).then(loadDevices)}
                    className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-700 dark:text-rose-300"
                  >
                    Revoke
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
