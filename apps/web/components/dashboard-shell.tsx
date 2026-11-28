"use client";

import { useState, type ReactNode } from "react";
import { useBackendHealth } from "@/hooks/use-health";
import { ClayNavbar, ClaySidebar } from "./clay/layout";

export function DashboardShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { data: health, isLoading, isError } = useBackendHealth();

  const statusTone = isLoading
    ? "neutral"
    : isError || !health
      ? "unavailable"
      : health.status === "healthy"
        ? "healthy"
        : "degraded";

  const statusLabel = isLoading
    ? "Connecting..."
    : isError || !health
      ? "API Offline"
      : `API ${health.status}`;

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <ClaySidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((v) => !v)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <ClayNavbar
          onOpenMobile={() => setMobileOpen(true)}
          statusTone={statusTone}
          statusLabel={statusLabel}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
