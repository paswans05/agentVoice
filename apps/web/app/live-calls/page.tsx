"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { CallSession, CallSessionStatus, LiveCallsStats, LiveCallsWsFrame } from "@agentvoice/shared-types";
import {
  Activity,
  AlertTriangle,
  Eye,
  Flag,
  PhoneCall,
  PhoneOff,
  Radio,
  Search,
  ShieldCheck,
  Wifi,
  WifiOff,
} from "lucide-react";

import { useLiveCallsWebSocket } from "@/hooks/use-live-calls";
import {
  fetchCallMonitoringSettings,
  fetchLiveCalls,
  fetchLiveCallsStats,
  flagLiveCall,
  terminateLiveCall,
} from "@/lib/api-client";

const STATUS_BADGE: Record<string, string> = {
  ACTIVE: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  ANSWERED: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  RINGING: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
  INITIATING: "bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30",
  ON_HOLD: "bg-orange-500/15 text-orange-700 dark:text-orange-300 border-orange-500/30",
  TRANSFERRING: "bg-violet-500/15 text-violet-700 dark:text-violet-300 border-violet-500/30",
  COMPLETED: "bg-muted text-muted-foreground border-border",
  TERMINATED: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
  FAILED: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
};

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function LiveCallsPage() {
  const [activeCalls, setActiveCalls] = useState<CallSession[]>([]);
  const [recentCalls, setRecentCalls] = useState<CallSession[]>([]);
  const [stats, setStats] = useState<LiveCallsStats | null>(null);
  const [recordingDefault, setRecordingDefault] = useState<boolean>(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CallSessionStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [active, all, st, cfg] = await Promise.all([
        fetchLiveCalls({
          active_only: true,
          status: statusFilter,
          search: search || undefined,
        }),
        fetchLiveCalls({ active_only: false, limit: 25 }),
        fetchLiveCallsStats(),
        fetchCallMonitoringSettings(),
      ]);
      setActiveCalls(active);
      setRecentCalls(
        all.filter((c) =>
          ["COMPLETED", "FAILED", "BUSY", "NO_ANSWER", "TERMINATED", "DISCONNECTED"].includes(
            c.status,
          ),
        ),
      );
      setStats(st);
      setRecordingDefault(cfg.recording_enabled_by_default);
      setErrorMsg(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load live calls.");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const { connectionState, lastHeartbeatAt } = useLiveCallsWebSocket({
    onFrame: useCallback(
      (frame: LiveCallsWsFrame) => {
        if (
          frame.type === "CALL_EVENT" ||
          frame.type === "TRANSCRIPT_SEGMENT" ||
          frame.type === "METRICS_UPDATED"
        ) {
          void loadAll();
        }
      },
      [loadAll],
    ),
  });

  // Live duration ticker for active calls
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const computeLiveSeconds = useCallback((call: CallSession) => {
    if (call.ended_at) return call.duration_seconds;
    const elapsed = Math.floor((Date.now() - new Date(call.started_at).getTime()) / 1000);
    return Math.max(call.duration_seconds, elapsed, 0);
  }, []);

  const handleTerminate = async (callId: string) => {
    setActionBusy(callId);
    try {
      await terminateLiveCall(callId, "Terminated from Live Calls dashboard");
      await loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to terminate call.");
    } finally {
      setActionBusy(null);
    }
  };

  const handleFlag = async (callId: string) => {
    setActionBusy(callId);
    try {
      await flagLiveCall(callId, "Flagged for supervisor review");
      await loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to flag call.");
    } finally {
      setActionBusy(null);
    }
  };

  const wsBadge = useMemo(() => {
    if (connectionState === "connected") {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          <Wifi className="h-3.5 w-3.5" />
          Live Stream Connected
        </span>
      );
    }
    if (connectionState === "connecting" || connectionState === "reconnecting") {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-300">
          <Radio className="h-3.5 w-3.5 animate-pulse" />
          {connectionState === "reconnecting" ? "Reconnecting..." : "Connecting..."}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/15 px-3 py-1 text-xs font-medium text-rose-700 dark:text-rose-300">
        <WifiOff className="h-3.5 w-3.5" />
        Disconnected
      </span>
    );
  }, [connectionState]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Live Calls</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time contact center monitoring, live transcripts, AI states, and operator controls.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {wsBadge}
          {lastHeartbeatAt && (
            <span className="text-xs text-muted-foreground">
              Heartbeat: {new Date(lastHeartbeatAt).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Privacy & Telephony Banner */}
      <div className="rounded-xl border border-border bg-card p-4 text-xs text-muted-foreground">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-medium text-foreground">
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
            <span>
              Privacy Safeguards Active: Customer numbers masked · Audio recording{" "}
              {recordingDefault ? "enabled by default" : "disabled by default"}
            </span>
          </div>
          <span>{stats?.provider_status ?? "Browser Voice Ready"}</span>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Active Calls</div>
          <div className="mt-1 text-2xl font-semibold">{stats?.active_calls ?? 0}</div>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">In Progress</div>
          <div className="mt-1 text-2xl font-semibold text-emerald-600 dark:text-emerald-400">
            {stats?.in_progress_calls ?? 0}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Ringing</div>
          <div className="mt-1 text-2xl font-semibold text-amber-600 dark:text-amber-400">
            {stats?.ringing_calls ?? 0}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Attention Required</div>
          <div className="mt-1 text-2xl font-semibold text-rose-600 dark:text-rose-400">
            {stats?.attention_required_calls ?? 0}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Recently Completed</div>
          <div className="mt-1 text-2xl font-semibold">{stats?.recently_completed_calls ?? 0}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Call ID, Agent ID, Campaign ID, or masked phone..."
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as CallSessionStatus | "")}
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        >
          <option value="">All Active Statuses</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="RINGING">RINGING</option>
          <option value="ON_HOLD">ON_HOLD</option>
          <option value="TRANSFERRING">TRANSFERRING</option>
        </select>
      </div>

      {/* Active Calls Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 font-medium">
            <PhoneCall className="h-4 w-4 text-primary" />
            <span>Active Calls ({activeCalls.length})</span>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-muted-foreground">Loading live calls...</div>
        ) : activeCalls.length === 0 ? (
          <div className="p-8 text-center space-y-2">
            <Activity className="mx-auto h-8 w-8 text-muted-foreground/60" />
            <p className="text-sm font-medium">No active calls right now</p>
            <p className="text-xs text-muted-foreground">
              Start a voice conversation in{" "}
              <Link href="/playground" className="text-primary underline">
                Voice Playground
              </Link>{" "}
              to see live session monitoring, transcripts, and AI states appear here in real time.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Call / Type</th>
                  <th className="px-4 py-3">Agent</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">AI State</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3 text-right">Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {activeCalls.map((call) => (
                  <tr key={call.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3">
                      <Link
                        href={`/live-calls/${call.id}`}
                        className="font-mono text-xs font-medium text-primary hover:underline"
                      >
                        {call.id}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {call.session_type} · {call.direction}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{call.agent_id}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {call.caller_number_masked || "Browser Mic"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
                          STATUS_BADGE[call.status] ?? "bg-muted text-foreground border-border"
                        }`}
                      >
                        {call.status}
                      </span>
                      {call.flagged_for_review && (
                        <span className="ml-1.5 inline-flex items-center gap-1 text-xs text-amber-600">
                          <AlertTriangle className="h-3 w-3" /> Flagged
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs font-medium">{call.current_agent_state}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {formatDuration(computeLiveSeconds(call))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <Link
                          href={`/live-calls/${call.id}`}
                          className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          Monitor
                        </Link>
                        <button
                          type="button"
                          disabled={actionBusy === call.id}
                          onClick={() => void handleFlag(call.id)}
                          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                          title="Flag for review"
                        >
                          <Flag className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          disabled={actionBusy === call.id}
                          onClick={() => void handleTerminate(call.id)}
                          className="inline-flex items-center gap-1 rounded-md border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-700 hover:bg-rose-500/20 dark:text-rose-300 disabled:opacity-50"
                        >
                          <PhoneOff className="h-3.5 w-3.5" />
                          End
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Completed Calls */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="border-b border-border px-4 py-3 font-medium">
          Recent Completed Calls ({recentCalls.length})
        </div>
        {recentCalls.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted-foreground">
            No completed call sessions recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5">Call ID</th>
                  <th className="px-4 py-2.5">Agent</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Duration</th>
                  <th className="px-4 py-2.5">Ended</th>
                  <th className="px-4 py-2.5 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recentCalls.map((call) => (
                  <tr key={call.id} className="hover:bg-muted/20">
                    <td className="px-4 py-2.5 font-mono text-xs">{call.id}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{call.agent_id}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${
                          STATUS_BADGE[call.status] ?? "border-border"
                        }`}
                      >
                        {call.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs">
                      {formatDuration(call.duration_seconds)}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {call.ended_at ? new Date(call.ended_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Link
                        href={`/live-calls/${call.id}`}
                        className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted"
                      >
                        Inspect
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
