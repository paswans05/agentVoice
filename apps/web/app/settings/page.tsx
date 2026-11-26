"use client";

import { APP_CONFIG } from "@agentvoice/config";
import { ThemeToggle } from "@/components/theme-toggle";
import { useBackendHealth, useSystemStatus } from "@/hooks/use-health";
import { API_BASE_URL } from "@/lib/api-client";

export default function SettingsPage() {
  const { data: health } = useBackendHealth();
  const { data: status } = useSystemStatus();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Runtime, storage, and appearance settings for {APP_CONFIG.name}.
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-medium">Appearance</h2>
            <p className="text-sm text-muted-foreground">
              Switch between light and dark dashboard themes.
            </p>
          </div>
          <ThemeToggle />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-base font-medium">System &amp; Storage Configuration</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex flex-col gap-1 border-b border-border pb-2 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Backend API URL</dt>
            <dd className="font-mono text-xs sm:text-sm">{API_BASE_URL}</dd>
          </div>
          <div className="flex flex-col gap-1 border-b border-border pb-2 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Storage Backend</dt>
            <dd className="font-medium uppercase">{health?.storage.backend ?? "json"}</dd>
          </div>
          <div className="flex flex-col gap-1 border-b border-border pb-2 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Data Directory</dt>
            <dd className="font-mono text-xs sm:text-sm break-all">
              {health?.storage.data_dir ?? "—"}
            </dd>
          </div>
          <div className="flex flex-col gap-1 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Environment</dt>
            <dd className="font-medium capitalize">{status?.environment ?? "—"}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
