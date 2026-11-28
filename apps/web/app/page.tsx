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
import Link from "next/link";
import {
  ClayBadge,
  ClayButton,
  ClayCard,
  ClayChartContainer,
  ClayProgress,
  ClayStatCard,
} from "@/components/clay";
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
        <ClayButton
          type="button"
          onClick={refetchAll}
          disabled={healthQuery.isFetching || statusQuery.isFetching}
          className="self-start"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              healthQuery.isFetching || statusQuery.isFetching ? "animate-spin" : ""
            }`}
          />
          Refresh Status
        </ClayButton>
      </div>

      {isError && (
        <ClayCard accent="coral" className="text-sm text-[#B64450] dark:text-[#F08C95]">
          <div className="font-semibold">Unable to reach FastAPI backend</div>
          <p className="mt-1 text-xs opacity-90">
            Expected backend at <code>{API_BASE_URL}</code>. Start the API server and click
            Refresh Status.
          </p>
        </ClayCard>
      )}

      {/* Clay KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <ClayStatCard
          label="Backend API"
          accent="lavender"
          icon={<Server className="h-4 w-4" />}
          value={
            isLoading ? (
              <span className="text-base text-muted-foreground">Checking...</span>
            ) : health ? (
              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
                  STATUS_TONE_CLASSES[health.status]
                }`}
              >
                {health.status}
              </span>
            ) : (
              <ClayBadge tone="danger">Unavailable</ClayBadge>
            )
          }
          sublabel={health ? `Uptime: ${health.uptime_seconds}s` : "Awaiting connection"}
        />

        <ClayStatCard
          label="Storage Engine"
          accent="mint"
          icon={<Database className="h-4 w-4" />}
          value={<span className="uppercase">{health?.storage.backend ?? "—"}</span>}
          sublabel={
            health
              ? health.storage.writable
                ? "Local storage writable"
                : "Storage read-only"
              : "No database required"
          }
        />

        <ClayStatCard
          label="CPU Usage"
          accent="sky"
          icon={<Cpu className="h-4 w-4" />}
          value={
            status?.resources.cpu_percent !== null && status?.resources.cpu_percent !== undefined
              ? `${status.resources.cpu_percent}%`
              : "—"
          }
          sublabel={status?.resources.platform ?? "Host platform"}
        />

        <ClayStatCard
          label="Memory Usage"
          accent="peach"
          icon={<HardDrive className="h-4 w-4" />}
          value={
            status?.resources.memory_percent !== null &&
            status?.resources.memory_percent !== undefined
              ? `${status.resources.memory_percent}%`
              : "—"
          }
          sublabel={
            status?.resources.memory_used_mb != null && status?.resources.memory_total_mb != null
              ? `${status.resources.memory_used_mb} / ${status.resources.memory_total_mb} MB`
              : "System RAM"
          }
        />
      </div>

      {/* Resource Gauges & Platform Guarantees */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ClayChartContainer
          title="Runtime Resource Utilization"
          subtitle="Real-time host CPU & RAM telemetry"
          actions={
            <Link
              href="/analytics"
              className="text-xs font-medium text-primary hover:underline"
            >
              View Analytics →
            </Link>
          }
        >
          <div className="space-y-4">
            <ClayProgress
              label="CPU Load"
              value={status?.resources.cpu_percent ?? 0}
              tone="info"
            />
            <ClayProgress
              label="Memory Utilization"
              value={status?.resources.memory_percent ?? 0}
              tone="primary"
            />
          </div>
        </ClayChartContainer>

        <ClayCard className="space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Local-First Architecture</span>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between border-b border-border/50 pb-2">
              <dt className="text-muted-foreground">External AI API Keys Required</dt>
              <dd>
                <ClayBadge tone="success">
                  {status ? (status.external_ai_required ? "Yes" : "No") : "No"}
                </ClayBadge>
              </dd>
            </div>
            <div className="flex items-center justify-between border-b border-border/50 pb-2">
              <dt className="text-muted-foreground">Offline Mode Ready</dt>
              <dd>
                <ClayBadge tone={status?.offline_ready ? "success" : "neutral"}>
                  {status ? (status.offline_ready ? "Yes" : "No") : "—"}
                </ClayBadge>
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Python Runtime</dt>
              <dd className="font-mono text-xs font-medium">
                {status?.resources.python_version ?? "—"}
              </dd>
            </div>
          </dl>
        </ClayCard>
      </div>

      <ClayCard accent="lavender">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Activity className="h-4 w-4 text-primary" />
              <span>Platform Status & Quick Actions</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Active Milestone:{" "}
              <strong className="text-foreground">
                Phase {status?.phases.current_phase ?? 10} —{" "}
                {status?.phases.phase_name ?? "Telephony & WebRTC Ready"}
              </strong>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/agents/new">
              <ClayButton variant="primary" size="sm">Create Agent</ClayButton>
            </Link>
            <Link href="/telephony/dialer">
              <ClayButton variant="success" size="sm">Open Dialer</ClayButton>
            </Link>
          </div>
        </div>
      </ClayCard>
    </div>
  );
}
