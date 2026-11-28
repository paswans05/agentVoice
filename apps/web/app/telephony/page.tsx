"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type {
  GsmGatewayRecord,
  InboundRouteRecord,
  OutboundRouteRecord,
  SipTrunkRecord,
  TelephonyOverview,
  TelephonyProviderRecord,
  TelephonySettings,
} from "@agentvoice/shared-types";
import {
  Activity,
  CheckCircle2,
  Cpu,
  Network,
  PhoneIncoming,
  PhoneOutgoing,
  Plus,
  RefreshCw,
  Settings,
  ShieldCheck,
  Trash2,
  Wrench,
} from "lucide-react";

import {
  createInboundRoute,
  createOutboundRoute,
  createSipTrunk,
  deleteGsmGateway,
  deleteInboundRoute,
  deleteOutboundRoute,
  deleteSipTrunk,
  deleteTelephonyProvider,
  fetchGsmGateways,
  fetchInboundRoutes,
  fetchOutboundRoutes,
  fetchSipTrunks,
  fetchTelephonyOverview,
  fetchTelephonyProviderRecords,
  fetchTelephonySettings,
  testGsmGateway,
  testSipTrunk,
  testTelephonyProvider,
  toggleTelephonyProvider,
  updateTelephonySettings,
} from "@/lib/api-client";

type TabId =
  | "overview"
  | "providers"
  | "trunks"
  | "inbound"
  | "outbound"
  | "gateways"
  | "settings"
  | "troubleshooting";

const STATUS_STYLE: Record<string, string> = {
  CONNECTED: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  REGISTERING: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
  DISCONNECTED: "bg-muted text-muted-foreground border-border",
  AUTH_FAILED: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
  NETWORK_ERROR: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
  UNAVAILABLE: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
  INCOMPLETE: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
};

export default function TelephonyPage() {
  const [tab, setTab] = useState<TabId>("overview");
  const [overview, setOverview] = useState<TelephonyOverview | null>(null);
  const [providers, setProviders] = useState<TelephonyProviderRecord[]>([]);
  const [trunks, setTrunks] = useState<SipTrunkRecord[]>([]);
  const [inboundRoutes, setInboundRoutes] = useState<InboundRouteRecord[]>([]);
  const [outboundRoutes, setOutboundRoutes] = useState<OutboundRouteRecord[]>([]);
  const [gateways, setGateways] = useState<GsmGatewayRecord[]>([]);
  const [settings, setSettings] = useState<TelephonySettings | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  // Quick-add form states
  const [trunkName, setTrunkName] = useState("");
  const [trunkHost, setTrunkHost] = useState("");
  const [trunkCallerId, setTrunkCallerId] = useState("");
  const [trunkProviderId, setTrunkProviderId] = useState("");

  const [inName, setInName] = useState("");
  const [inNumber, setInNumber] = useState("");
  const [inAgentId, setInAgentId] = useState("");

  const [outName, setOutName] = useState("");
  const [outProviderId, setOutProviderId] = useState("");
  const [outCallerId, setOutCallerId] = useState("");
  const [outPattern, setOutPattern] = useState("+91*");

  const loadAll = useCallback(async () => {
    try {
      const [ov, provs, trs, inR, outR, gws, cfg] = await Promise.all([
        fetchTelephonyOverview(),
        fetchTelephonyProviderRecords(),
        fetchSipTrunks(),
        fetchInboundRoutes(),
        fetchOutboundRoutes(),
        fetchGsmGateways(),
        fetchTelephonySettings(),
      ]);
      setOverview(ov);
      setProviders(provs);
      setTrunks(trs);
      setInboundRoutes(inR);
      setOutboundRoutes(outR);
      setGateways(gws);
      setSettings(cfg);
      const realProvs = provs.filter((p) => p.id !== "dry_run");
      if (realProvs.length > 0) {
        setTrunkProviderId((prev) => prev || realProvs[0].id);
        setOutProviderId((prev) => prev || realProvs[0].id);
      }
      setErrorMsg(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load telephony state.");
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const runTestProvider = async (id: string) => {
    setBusyId(id);
    setNotice(null);
    try {
      const res = await testTelephonyProvider(id);
      setNotice(String(res.message ?? "Connection test completed."));
      await loadAll();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Provider test failed.");
    } finally {
      setBusyId(null);
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "providers", label: "SIP & Asterisk Providers" },
    { id: "trunks", label: "SIP Trunks" },
    { id: "inbound", label: "Inbound Routes" },
    { id: "outbound", label: "Outbound Routes" },
    { id: "gateways", label: "GSM Gateways" },
    { id: "settings", label: "Call Settings" },
    { id: "troubleshooting", label: "Troubleshooting" },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Telephony Integration</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Authorized Asterisk ARI, PJSIP trunks, GSM gateways, inbound/outbound routing, and
            compliance controls.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadAll()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <Link
            href="/telephony/dialer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            Internal Dialer
          </Link>
          <Link
            href="/telephony/devices"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            Mobile Devices
          </Link>
          <Link
            href="/telephony/setup"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" />
            Provider Setup Wizard
          </Link>
        </div>
      </div>

      {/* Compliance & Security Banner */}
      <div className="rounded-xl border border-border bg-card p-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>
            Authorized Calling Only · Stored passwords & ARI secrets are encrypted at rest and
            never exposed · Real telephony requires verified provider connectivity
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-border bg-muted/50 p-3 text-xs text-foreground">
          {notice}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-border pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* OVERVIEW */}
      {tab === "overview" && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Real Telephony Status</div>
              <div className="mt-1 flex items-center gap-2 text-base font-semibold">
                {overview?.real_telephony_ready ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    Connected
                  </>
                ) : (
                  <>
                    <Activity className="h-4 w-4 text-amber-500" />
                    Dry-Run / Not Connected
                  </>
                )}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Connected Providers / Trunks</div>
              <div className="mt-1 text-2xl font-semibold">
                {overview?.connected_providers ?? 0} / {overview?.registered_trunks ?? 0}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Active / Available Channels</div>
              <div className="mt-1 text-2xl font-semibold">
                {overview?.active_telephony_calls ?? 0} / {overview?.available_channels ?? 0}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Active Inbound / Outbound Routes</div>
              <div className="mt-1 text-2xl font-semibold">
                {overview?.inbound_routes ?? 0} / {overview?.outbound_routes ?? 0}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4 space-y-2">
            <div className="font-medium text-sm">Recent Provider Errors</div>
            {overview?.recent_errors.length ? (
              <ul className="list-disc pl-5 text-xs text-rose-600 dark:text-rose-400 space-y-1">
                {overview.recent_errors.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">No recent provider errors reported.</p>
            )}
          </div>
        </div>
      )}

      {/* PROVIDERS */}
      {tab === "providers" && (
        <div className="space-y-3">
          {providers.map((p) => (
            <div
              key={p.id}
              className="rounded-xl border border-border bg-card p-4 flex flex-wrap items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{p.name}</span>
                  <span className="rounded bg-muted px-2 py-0.5 font-mono text-[11px]">
                    {p.provider_type}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                      STATUS_STYLE[p.status] ?? "border-border"
                    }`}
                  >
                    {p.status}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{p.message}</p>
                <div className="text-[11px] text-muted-foreground font-mono">
                  {p.host ? `${p.host}:${p.port} (${p.transport})` : "Local simulator"} · Auth:{" "}
                  {p.auth_mode || "userpass_registration"} · Caller ID:{" "}
                  {p.caller_id || "—"} · Capabilities: inbound={String(p.capabilities.inbound)},
                  outbound={String(p.capabilities.outbound)}, hold={String(p.capabilities.hold)},
                  transfer={String(p.capabilities.transfer)}, dtmf={String(p.capabilities.dtmf)}
                  {p.credential_rotated_at ? ` · Rotated: ${p.credential_rotated_at.slice(0, 10)}` : ""}
                </div>
              </div>
              {p.id !== "dry_run" && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void toggleTelephonyProvider(p.id, !p.enabled).then(loadAll)}
                    className="rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                  >
                    {p.enabled ? "Disable" : "Enable"}
                  </button>
                  <button
                    type="button"
                    disabled={busyId === p.id}
                    onClick={() => void runTestProvider(p.id)}
                    className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
                  >
                    Test Connection
                  </button>
                  <button
                    type="button"
                    onClick={() => void deleteTelephonyProvider(p.id).then(loadAll)}
                    className="rounded-lg border border-rose-500/30 p-1.5 text-rose-600 hover:bg-rose-500/10"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* SIP TRUNKS */}
      {tab === "trunks" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!trunkName || !trunkHost || !trunkCallerId || !trunkProviderId) return;
              await createSipTrunk({
                name: trunkName,
                provider_id: trunkProviderId,
                host: trunkHost,
                caller_id: trunkCallerId,
              });
              setTrunkName("");
              setTrunkHost("");
              setTrunkCallerId("");
              await loadAll();
            }}
            className="rounded-xl border border-border bg-card p-4 grid gap-3 sm:grid-cols-5 items-end"
          >
            <div>
              <label className="text-xs text-muted-foreground">Trunk Name</label>
              <input
                value={trunkName}
                onChange={(e) => setTrunkName(e.target.value)}
                placeholder="Primary India SIP"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Provider</label>
              <select
                value={trunkProviderId}
                onChange={(e) => setTrunkProviderId(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              >
                <option value="">Select provider...</option>
                {providers
                  .filter((p) => p.id !== "dry_run")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">SIP Host</label>
              <input
                value={trunkHost}
                onChange={(e) => setTrunkHost(e.target.value)}
                placeholder="sip.carrier.example"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Caller ID</label>
              <input
                value={trunkCallerId}
                onChange={(e) => setTrunkCallerId(e.target.value)}
                placeholder="+911140001234"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"
            >
              Add SIP Trunk
            </button>
          </form>

          <div className="space-y-2">
            {trunks.length === 0 ? (
              <p className="text-xs text-muted-foreground">No SIP trunks configured yet.</p>
            ) : (
              trunks.map((t) => (
                <div
                  key={t.id}
                  className="rounded-xl border border-border bg-card p-4 flex items-center justify-between gap-3"
                >
                  <div>
                    <div className="flex items-center gap-2 font-medium text-sm">
                      <Network className="h-4 w-4 text-primary" />
                      <span>{t.name}</span>
                      <span className="rounded-full border px-2 py-0.5 text-[11px]">{t.status}</span>
                      {t.options_status && (
                        <span className="rounded bg-muted px-2 py-0.5 font-mono text-[10px]">
                          OPTIONS: {t.options_status}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono mt-1">
                      {t.host}:{t.port} ({t.transport} · {t.auth_mode || "userpass_registration"}) ·
                      Caller ID: {t.caller_id} · Codecs: {t.codecs.join(", ")}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => void testSipTrunk(t.id).then(loadAll)}
                      className="rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted"
                    >
                      Test
                    </button>
                    <button
                      type="button"
                      onClick={() => void deleteSipTrunk(t.id).then(loadAll)}
                      className="rounded-md border border-rose-500/30 p-1 text-rose-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* INBOUND ROUTES */}
      {tab === "inbound" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!inName || !inNumber || !inAgentId) return;
              await createInboundRoute({
                name: inName,
                phone_number: inNumber,
                agent_id: inAgentId,
              });
              setInName("");
              setInNumber("");
              setInAgentId("");
              await loadAll();
            }}
            className="rounded-xl border border-border bg-card p-4 grid gap-3 sm:grid-cols-4 items-end"
          >
            <div>
              <label className="text-xs text-muted-foreground">Route Name</label>
              <input
                value={inName}
                onChange={(e) => setInName(e.target.value)}
                placeholder="Support DID"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Phone Number / DID</label>
              <input
                value={inNumber}
                onChange={(e) => setInNumber(e.target.value)}
                placeholder="+911140001234"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Target Agent ID</label>
              <input
                value={inAgentId}
                onChange={(e) => setInAgentId(e.target.value)}
                placeholder="agent_..."
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"
            >
              Add Inbound Route
            </button>
          </form>

          <div className="space-y-2">
            {inboundRoutes.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-border bg-card p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <PhoneIncoming className="h-4 w-4 text-primary" />
                  <div>
                    <div className="text-sm font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">
                      DID: {r.phone_number} → Agent: {r.agent_id} ({r.working_hours_start}–
                      {r.working_hours_end} {r.working_hours_timezone})
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void deleteInboundRoute(r.id).then(loadAll)}
                  className="rounded-md border border-rose-500/30 p-1.5 text-rose-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* OUTBOUND ROUTES */}
      {tab === "outbound" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!outName || !outProviderId || !outCallerId) return;
              await createOutboundRoute({
                name: outName,
                provider_id: outProviderId,
                caller_id: outCallerId,
                destination_pattern: outPattern,
              });
              setOutName("");
              setOutCallerId("");
              await loadAll();
            }}
            className="rounded-xl border border-border bg-card p-4 grid gap-3 sm:grid-cols-5 items-end"
          >
            <div>
              <label className="text-xs text-muted-foreground">Route Name</label>
              <input
                value={outName}
                onChange={(e) => setOutName(e.target.value)}
                placeholder="India Outbound"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Provider</label>
              <select
                value={outProviderId}
                onChange={(e) => setOutProviderId(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              >
                <option value="">Select provider...</option>
                {providers
                  .filter((p) => p.id !== "dry_run")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Caller ID</label>
              <input
                value={outCallerId}
                onChange={(e) => setOutCallerId(e.target.value)}
                placeholder="+911140001234"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Destination Pattern</label>
              <input
                value={outPattern}
                onChange={(e) => setOutPattern(e.target.value)}
                placeholder="+91*"
                className="mt-1 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"
            >
              Add Outbound Route
            </button>
          </form>

          <div className="space-y-2">
            {outboundRoutes.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-border bg-card p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <PhoneOutgoing className="h-4 w-4 text-primary" />
                  <div>
                    <div className="text-sm font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">
                      Pattern: {r.destination_pattern} · Caller ID: {r.caller_id} · Provider:{" "}
                      {r.provider_id}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void deleteOutboundRoute(r.id).then(loadAll)}
                  className="rounded-md border border-rose-500/30 p-1.5 text-rose-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GSM GATEWAYS */}
      {tab === "gateways" && (
        <div className="space-y-3">
          {gateways.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-6 text-xs text-muted-foreground">
              No authorized GSM gateways configured. Add one via the{" "}
              <Link href="/telephony/setup" className="text-primary underline">
                Provider Setup Wizard
              </Link>
              . Physical GSM hardware requires local verification.
            </div>
          ) : (
            gateways.map((g) => (
              <div
                key={g.id}
                className="rounded-xl border border-border bg-card p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <Cpu className="h-4 w-4 text-primary" />
                  <div>
                    <div className="text-sm font-medium">
                      {g.name} ({g.vendor})
                    </div>
                    <div className="text-xs text-muted-foreground font-mono">
                      Mode: {g.mode} · Channels: {g.active_channels}/{g.max_channels} · Hardware
                      Verified: {String(g.hardware_verified)} · Status: {g.status}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void testGsmGateway(g.id).then(loadAll)}
                    className="rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted"
                  >
                    Test Hardware
                  </button>
                  <button
                    type="button"
                    onClick={() => void deleteGsmGateway(g.id).then(loadAll)}
                    className="rounded-md border border-rose-500/30 p-1 text-rose-600"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* CALL SETTINGS */}
      {tab === "settings" && settings && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-4 max-w-2xl">
          <div className="flex items-center gap-2 font-medium">
            <Settings className="h-4 w-4 text-primary" />
            <span>Global Telephony & Compliance Settings</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 text-xs">
            <label className="space-y-1">
              <span>Max Concurrent Calls</span>
              <input
                type="number"
                value={settings.max_concurrent_calls}
                onChange={(e) =>
                  setSettings({ ...settings, max_concurrent_calls: Number(e.target.value) })
                }
                className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
              />
            </label>
            <label className="space-y-1">
              <span>Audio Buffer (ms)</span>
              <input
                type="number"
                value={settings.audio_buffer_ms}
                onChange={(e) =>
                  setSettings({ ...settings, audio_buffer_ms: Number(e.target.value) })
                }
                className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
              />
            </label>
          </div>
          <div className="space-y-2 text-xs">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.enforce_trai_dlt_compliance}
                onChange={(e) =>
                  setSettings({ ...settings, enforce_trai_dlt_compliance: e.target.checked })
                }
              />
              Enforce TRAI / DLT commercial communication policy checks
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.require_caller_id_authorization}
                onChange={(e) =>
                  setSettings({ ...settings, require_caller_id_authorization: e.target.checked })
                }
              />
              Require authorized Caller ID on outbound calls
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.block_open_sip_relay}
                onChange={(e) =>
                  setSettings({ ...settings, block_open_sip_relay: e.target.checked })
                }
              />
              Block open SIP relay / arbitrary external URI dialing
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.webhook_signature_required}
                onChange={(e) =>
                  setSettings({ ...settings, webhook_signature_required: e.target.checked })
                }
              />
              Require HMAC-SHA256 webhook signatures on provider events
            </label>
          </div>
          <button
            type="button"
            onClick={async () => {
              const saved = await updateTelephonySettings(settings);
              setSettings(saved);
              setNotice("Telephony settings saved.");
            }}
            className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
          >
            Save Settings
          </button>
        </div>
      )}

      {/* TROUBLESHOOTING */}
      {tab === "troubleshooting" && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-3 text-xs">
          <div className="flex items-center gap-2 font-medium text-sm">
            <Wrench className="h-4 w-4 text-primary" />
            <span>Telephony Troubleshooting Checklist</span>
          </div>
          <ul className="list-disc pl-5 space-y-1.5 text-muted-foreground">
            <li>
              <strong>Asterisk ARI 401/403</strong>: Verify ARI username/password in{" "}
              <code>ari.conf</code> and ensure HTTP/TLS ARI port (8088/8089) is reachable from the
              agentVoice backend on a private network.
            </li>
            <li>
              <strong>No Inbound Answer</strong>: Ensure an enabled Inbound Route matches the
              dialed DID and its assigned AI Agent is <code>ACTIVE</code> within configured working
              hours.
            </li>
            <li>
              <strong>Outbound Blocked</strong>: Verify lead consent (<code>GRANTED</code>),
              suppression status, allowed destination patterns, and authorized Caller ID.
            </li>
            <li>
              <strong>Audio / Codec Mismatch</strong>: Confirm carrier supports G.711 μ-law (
              <code>PCMU</code>) or A-law (<code>PCMA</code>) at 8 kHz; agentVoice converts
              automatically to 16 kHz PCM for local STT/TTS.
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
