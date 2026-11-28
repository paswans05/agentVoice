"use client";

import { BarChart3, CheckCircle2, PhoneCall, TestTube2 } from "lucide-react";
import { ClayChartContainer, ClayProgress, ClayStatCard } from "@/components/clay";
import { useCampaignOverview } from "@/hooks/use-campaigns";

export default function AnalyticsPage() {
  const overviewQuery = useCampaignOverview();
  const data = overviewQuery.data;

  const totalCampaigns = data?.total_campaigns ?? 0;
  const completedCampaigns = data?.completed_campaigns ?? 0;
  const realCalls = data?.total_real_calls ?? 0;
  const dryRunCalls = data?.total_dry_run_calls ?? 0;
  const totalCalls = Math.max(1, realCalls + dryRunCalls);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Real campaign metrics separated strictly from dry-run simulation counts.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <ClayStatCard
          label="Total Campaigns"
          accent="lavender"
          icon={<BarChart3 className="h-4 w-4" />}
          value={totalCampaigns}
        />
        <ClayStatCard
          label="Completed Campaigns"
          accent="mint"
          icon={<CheckCircle2 className="h-4 w-4" />}
          value={completedCampaigns}
        />
        <ClayStatCard
          label="Real Calls Placed"
          accent="sky"
          icon={<PhoneCall className="h-4 w-4" />}
          value={realCalls}
        />
        <ClayStatCard
          label="Dry-Run Simulated Calls"
          accent="peach"
          icon={<TestTube2 className="h-4 w-4" />}
          value={dryRunCalls}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ClayChartContainer
          title="Call Execution Breakdown"
          subtitle="Authorized Real Calls vs Dry-Run Simulations"
        >
          <div className="space-y-4">
            <ClayProgress
              label={`Real Calls (${realCalls})`}
              value={realCalls}
              max={totalCalls}
              tone="success"
            />
            <ClayProgress
              label={`Dry-Run Simulations (${dryRunCalls})`}
              value={dryRunCalls}
              max={totalCalls}
              tone="warning"
            />
          </div>
        </ClayChartContainer>

        <ClayChartContainer
          title="Campaign Completion Rate"
          subtitle="Completed vs Total Configured Campaigns"
        >
          <div className="space-y-4">
            <ClayProgress
              label={`Completed (${completedCampaigns} / ${totalCampaigns})`}
              value={completedCampaigns}
              max={Math.max(1, totalCampaigns)}
              tone="primary"
            />
          </div>
        </ClayChartContainer>
      </div>
    </div>
  );
}
