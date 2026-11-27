"use client";

import { Megaphone, Plus, Radio, Trash2 } from "lucide-react";
import Link from "next/link";
import {
  useCampaignOverview,
  useCampaigns,
  useDeleteCampaign,
  useTelephonyProviders,
} from "@/hooks/use-campaigns";

export default function CampaignsPage() {
  const campaignsQuery = useCampaigns();
  const overviewQuery = useCampaignOverview();
  const providersQuery = useTelephonyProviders();
  const deleteMutation = useDeleteCampaign();

  const campaigns = campaignsQuery.data ?? [];
  const overview = overviewQuery.data;
  const realConfigured = (providersQuery.data ?? []).some(
    (p) => p.supports_real_calls && p.configured,
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Campaigns</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Schedule, validate, and run outbound voice campaigns with consent and suppression
            enforcement.
          </p>
        </div>
        <Link
          href="/campaigns/new"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          Create Campaign
        </Link>
      </div>

      {/* Telephony Readiness Banner */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-800 dark:text-amber-200">
        <div className="flex items-center gap-2 font-semibold">
          <Radio className="h-4 w-4" />
          <span>
            Telephony Status:{" "}
            {realConfigured
              ? "Authorized Real Telephony Configured"
              : "Dry-Run Mode Ready (Real SIP/Asterisk requires Phase 9)"}
          </span>
        </div>
        <p className="mt-1">
          Dry-run campaigns simulate execution and enforce all consent, suppression, and schedule
          checks locally without placing real phone calls.
        </p>
      </div>

      {/* Dashboard Stats */}
      <div className="grid gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {[
          { label: "Total", value: overview?.total_campaigns ?? 0 },
          { label: "Draft", value: overview?.draft_campaigns ?? 0 },
          { label: "Scheduled", value: overview?.scheduled_campaigns ?? 0 },
          { label: "Running", value: overview?.running_campaigns ?? 0 },
          { label: "Paused", value: overview?.paused_campaigns ?? 0 },
          { label: "Completed", value: overview?.completed_campaigns ?? 0 },
          { label: "Failed", value: overview?.failed_campaigns ?? 0 },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-border bg-card p-3.5">
            <div className="text-[11px] text-muted-foreground">{s.label}</div>
            <div className="mt-1 text-xl font-semibold">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Campaigns Table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="p-3">Campaign</th>
              <th className="p-3">Type</th>
              <th className="p-3">Mode</th>
              <th className="p-3">Leads</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {campaignsQuery.isLoading ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-xs text-muted-foreground">
                  Loading campaigns...
                </td>
              </tr>
            ) : campaigns.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-10 text-center">
                  <Megaphone className="mx-auto h-8 w-8 text-primary" />
                  <p className="mt-2 text-sm font-medium">No campaigns yet</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Create a campaign to select an active agent, eligible leads, and calling
                    schedule.
                  </p>
                </td>
              </tr>
            ) : (
              campaigns.map((camp) => (
                <tr key={camp.id} className="hover:bg-muted/20">
                  <td className="p-3">
                    <Link
                      href={`/campaigns/${camp.id}`}
                      className="font-medium hover:text-primary"
                    >
                      {camp.name}
                    </Link>
                    <div className="text-xs text-muted-foreground">
                      {camp.timezone} · {camp.start_time}–{camp.end_time}
                    </div>
                  </td>
                  <td className="p-3 text-xs">{camp.campaign_type}</td>
                  <td className="p-3 text-xs">
                    <span className="rounded bg-muted px-2 py-0.5 text-[11px] font-medium">
                      {camp.dry_run ? "DRY-RUN" : camp.telephony_provider.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-3 text-xs">
                    {camp.selected_lead_ids.length} lead(s) · {camp.lead_group_ids.length} group(s)
                  </td>
                  <td className="p-3 text-xs">
                    <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-[11px] font-medium">
                      {camp.status}
                    </span>
                  </td>
                  <td className="p-3 text-right text-xs">
                    <Link
                      href={`/campaigns/${camp.id}`}
                      className="mr-3 text-primary hover:underline"
                    >
                      Open
                    </Link>
                    {camp.status !== "RUNNING" && (
                      <button
                        type="button"
                        onClick={() => void deleteMutation.mutateAsync(camp.id)}
                        aria-label={`Delete ${camp.name}`}
                        className="text-rose-600 hover:text-rose-700 dark:text-rose-400"
                      >
                        <Trash2 className="inline h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
