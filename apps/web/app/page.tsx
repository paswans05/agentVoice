"use client";

import { STATUS_TONE_CLASSES } from "@agentvoice/ui";
import {
  Activity,
  Cpu,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useBackendHealth, useSystemStatus } from "@/hooks/use-health";
import { API_BASE_URL } from "@/lib/api-client";

export default function OverviewPage() {
  const healthQuery = useBackendHealth();
  const statusQuery = useSystemStatus();

  const isLoading = healthQuery.isLoading || statusQuery.isLoading;
  const isError = healthQuery.isError || statusQuery.isError;
  const health = healthQuery.data;
  const status = statusQuery.data;

  const refetchAll = () => {
    void healthQuery.refetch();
    void statusQuery.refetch();
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live local infrastructure status for agentVoice.
          </p>
        </div>
        <button
          type="button"
          onClick={refetchAll}
          disabled={healthQuery.isFetching || statusQuery.isFetching}
          className="inline-flex items-center gap-2 self-start rounded-lg border border-border bg-card px-3.5 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              healthQuery.isFetching || statusQuery.isFetching ? "animate-spin" : ""
            }`}
          />
          Refresh Status
        </button>
      </div>

      {isError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-300">
          <div className="font-medium">Unable to reach FastAPI backend</div>
          <p className="mt-1 text-xs opacity-90">
            Expected backend at <code>{API_BASE_URL}</code>. Start the API server and click
            Refresh Status.
          </p>
        </div>
      )}

      {/* Status Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Backend API</span>
            <Server className="h-4 w-4" />
          </div>
          <div className="mt-3 flex items-center gap-2">
            {isLoading ? (
              <span className="text-lg font-semibold text-muted-foreground">Checking...</span>
            ) : health ? (
              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
                  STATUS_TONE_CLASSES[health.status]
                }`}
              >
                {health.status}
              </span>
            ) : (
              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_TONE_CLASSES.unavailable}`}
              >
                Unavailable
              </span>
            )}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {health ? `Uptime: ${health.uptime_seconds}s` : "Awaiting connection"}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Storage Engine</span>
            <Database className="h-4 w-4" />
          </div>
          <div className="mt-3 text-xl font-semibold uppercase">
            {health?.storage.backend ?? "—"}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {health
              ? health.storage.writable
                ? "Local storage writable"
                : "Storage read-only"
              : "No database required"}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>CPU Usage</span>
            <Cpu className="h-4 w-4" />
          </div>
          <div className="mt-3 text-xl font-semibold">
            {status?.resources.cpu_percent !== null && status?.resources.cpu_percent !== undefined
              ? `${status.resources.cpu_percent}%`
              : "—"}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {status?.resources.platform ?? "Host platform"}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Memory Usage</span>
            <HardDrive className="h-4 w-4" />
          </div>
          <div className="mt-3 text-xl font-semibold">
            {status?.resources.memory_percent !== null &&
            status?.resources.memory_percent !== undefined
              ? `${status.resources.memory_percent}%`
              : "—"}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {status?.resources.memory_used_mb != null && status?.resources.memory_total_mb != null
              ? `${status.resources.memory_used_mb} / ${status.resources.memory_total_mb} MB`
              : "System RAM"}
          </p>
        </div>
      </div>

      {/* Platform Guarantees & Phase Info */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-2 text-sm font-medium">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Local-First Architecture</span>
          </div>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <dt className="text-muted-foreground">External AI API Keys Required</dt>
              <dd className="font-medium">
                {status ? (status.external_ai_required ? "Yes" : "No") : "No"}
              </dd>
            </div>
            <div className="flex items-center justify-between border-b border-border pb-2">
              <dt className="text-muted-foreground">Offline Mode Ready</dt>
              <dd className="font-medium">
                {status ? (status.offline_ready ? "Yes" : "No") : "—"}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Python Runtime</dt>
              <dd className="font-medium">{status?.resources.python_version ?? "—"}</dd>
            </div>
          </dl>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Activity className="h-4 w-4 text-primary" />
            <span>Development Roadmap Status</span>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Current milestone:{" "}
            <strong className="text-foreground">
              Phase {status?.phases.current_phase ?? 1} —{" "}
              {status?.phases.phase_name ?? "Foundation"}
            </strong>
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Next up: <strong>Phase 2 — Agent Management</strong> (create, configure, and persist
            local AI voice agents in JSON storage).
          </p>
        </div>
      </div>
    </div>
  );
}
