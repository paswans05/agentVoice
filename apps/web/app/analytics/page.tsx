"use client";

import { BarChart3 } from "lucide-react";
import { useCampaignOverview } from "@/hooks/use-campaigns";

export default function AnalyticsPage() {
  const overviewQuery = useCampaignOverview();
  const data = overviewQuery.data;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Real campaign metrics separated strictly from dry-run simulation counts.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Total Campaigns</span>
            <BarChart3 className="h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-semibold">{data?.total_campaigns ?? 0}</div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="text-xs text-muted-foreground">Completed Campaigns</div>
          <div className="mt-2 text-2xl font-semibold">{data?.completed_campaigns ?? 0}</div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="text-xs text-muted-foreground">Real Calls Placed</div>
          <div className="mt-2 text-2xl font-semibold">{data?.total_real_calls ?? 0}</div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="text-xs text-muted-foreground">Dry-Run Simulated Calls</div>
          <div className="mt-2 text-2xl font-semibold">{data?.total_dry_run_calls ?? 0}</div>
        </div>
      </div>
    </div>
  );
}
