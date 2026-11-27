"use client";

import { ArrowLeft, CheckCircle2, Pause, Play, Square, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import {
  useCampaign,
  useCampaignAnalytics,
  useCampaignCalls,
  useCampaignControls,
  useCampaignEligibility,
  useCampaignJobs,
  useCampaignProgress,
} from "@/hooks/use-campaigns";

export default function CampaignDetailsPage() {
  const params = useParams<{ id: string }>();
  const campaignId = params.id;

  const campaignQuery = useCampaign(campaignId);
  const eligQuery = useCampaignEligibility(campaignId);
  const progressQuery = useCampaignProgress(campaignId);
  const jobsQuery = useCampaignJobs(campaignId);
  const callsQuery = useCampaignCalls(campaignId);
  const analyticsQuery = useCampaignAnalytics(campaignId);
  const controls = useCampaignControls(campaignId);

  const [tab, setTab] = useState<"overview" | "leads" | "execution" | "calls" | "analytics">(
    "overview",
  );
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (campaignQuery.isLoading) {
    return (
      <div className="mx-auto max-w-5xl rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Loading campaign...
      </div>
    );
  }

  if (campaignQuery.isError || !campaignQuery.data) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <Link href="/campaigns" className="inline-flex items-center gap-1.5 text-sm text-primary">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </Link>
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-700 dark:text-rose-300">
          Campaign not found.
        </div>
      </div>
    );
  }

  const camp = campaignQuery.data;
  const elig = eligQuery.data;
  const prog = progressQuery.data;
  const jobs = jobsQuery.data ?? [];
  const calls = callsQuery.data ?? [];
  const analytics = analyticsQuery.data;

  const runControl = async (fn: () => Promise<unknown>, msg: string) => {
    setError(null);
    setFeedback(null);
    try {
      await fn();
      setFeedback(msg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed.");
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/campaigns"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{camp.name}</h1>
              <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium">
                {camp.status}
              </span>
              {camp.dry_run && (
                <span className="rounded bg-primary/15 px-2 py-0.5 text-[11px] font-medium text-primary">
                  DRY-RUN
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {camp.campaign_type} · {camp.timezone} {camp.start_time}–{camp.end_time}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <button
            type="button"
            onClick={() =>
              void runControl(
                () => controls.activate.mutateAsync({ runInline: true, bypassWindow: camp.dry_run }),
                camp.dry_run ? "Dry-run campaign executed." : "Campaign started.",
              )
            }
            disabled={camp.status === "RUNNING" || camp.status === "COMPLETED"}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            {camp.dry_run ? "Run Dry-Run" : "Start Campaign"}
          </button>
          <button
            type="button"
            onClick={() => void runControl(() => controls.pause.mutateAsync(), "Campaign paused.")}
            disabled={camp.status !== "RUNNING"}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 font-medium hover:bg-muted disabled:opacity-50"
          >
            <Pause className="h-3.5 w-3.5" />
            Pause
          </button>
          <button
            type="button"
            onClick={() => void runControl(() => controls.stop.mutateAsync(), "Campaign stopped.")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 font-medium text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
          {camp.status === "DRAFT" && (
            <button
              type="button"
              onClick={() =>
                void runControl(() => controls.cancel.mutateAsync(), "Campaign cancelled.")
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 font-medium hover:bg-muted"
            >
              <XCircle className="h-3.5 w-3.5" />
              Cancel
            </button>
          )}
        </div>
      </div>

      {feedback && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-sm text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4" />
          <span>{feedback}</span>
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-2 text-xs">
        {(["overview", "leads", "execution", "calls", "analytics"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 font-medium capitalize ${
              tab === t ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid gap-4 md:grid-cols-2 text-xs">
          <div className="rounded-xl border border-border bg-card p-5 space-y-2">
            <h2 className="text-sm font-semibold">Configuration</h2>
            <p className="text-muted-foreground">{camp.description || "No description."}</p>
            <dl className="space-y-1.5 pt-2">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Calling Purpose</dt>
                <dd>{camp.calling_purpose}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Provider</dt>
                <dd>{camp.telephony_provider}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Max Concurrency</dt>
                <dd>{camp.maximum_concurrent_calls}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Max Attempts</dt>
                <dd>{camp.maximum_attempts_per_lead}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-xl border border-border bg-card p-5 space-y-2">
            <h2 className="text-sm font-semibold">Eligibility Summary</h2>
            <dl className="space-y-1.5 pt-2">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Selected</dt>
                <dd className="font-semibold">{elig?.total_selected ?? 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Eligible</dt>
                <dd className="font-semibold text-emerald-600">{elig?.eligible_count ?? 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Suppressed</dt>
                <dd>{elig?.suppressed_count ?? 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Unknown Consent</dt>
                <dd>{elig?.unknown_consent_count ?? 0}</dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {tab === "leads" && (
        <div className="rounded-xl border border-border bg-card p-5 text-xs space-y-2">
          <h2 className="text-sm font-semibold">Selected Leads Eligibility</h2>
          <p className="text-muted-foreground">
            Eligible: {elig?.eligible_count ?? 0} / {elig?.total_selected ?? 0}
          </p>
        </div>
      )}

      {tab === "execution" && (
        <div className="space-y-4 text-xs">
          {prog && (
            <div className="grid gap-3 sm:grid-cols-5">
              <div className="rounded-lg border border-border bg-card p-3">
                <div className="text-muted-foreground">Total Jobs</div>
                <div className="text-lg font-semibold">{prog.total_jobs}</div>
              </div>
              <div className="rounded-lg border border-border bg-card p-3">
                <div className="text-muted-foreground">Completed</div>
                <div className="text-lg font-semibold">{prog.completed_jobs}</div>
              </div>
              <div className="rounded-lg border border-border bg-card p-3">
                <div className="text-muted-foreground">Skipped/DNC</div>
                <div className="text-lg font-semibold">{prog.skipped_jobs}</div>
              </div>
              <div className="rounded-lg border border-border bg-card p-3">
                <div className="text-muted-foreground">Retry Scheduled</div>
                <div className="text-lg font-semibold">{prog.retry_scheduled_jobs}</div>
              </div>
              <div className="rounded-lg border border-border bg-card p-3">
                <div className="text-muted-foreground">Failed</div>
                <div className="text-lg font-semibold">{prog.failed_jobs}</div>
              </div>
            </div>
          )}

          <div className="divide-y divide-border rounded-xl border border-border bg-card">
            {jobs.length === 0 ? (
              <p className="p-6 text-center text-muted-foreground">No jobs queued yet.</p>
            ) : (
              jobs.map((j) => (
                <div key={j.id} className="flex justify-between p-3">
                  <span>
                    Lead <code>{j.lead_id}</code> (Attempt {j.attempt_number})
                  </span>
                  <span className="font-medium">
                    {j.status} {j.error_message ? `· ${j.error_message}` : ""}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {tab === "calls" && (
        <div className="divide-y divide-border rounded-xl border border-border bg-card text-xs">
          {calls.length === 0 ? (
            <p className="p-6 text-center text-muted-foreground">No call records yet.</p>
          ) : (
            calls.map((c) => (
              <div key={c.call_id} className="flex flex-wrap justify-between gap-2 p-3">
                <div>
                  <span className="font-medium">{c.outcome}</span>{" "}
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">
                    {c.is_dry_run ? "DRY-RUN" : "REAL"}
                  </span>
                  <div className="text-muted-foreground">{c.summary}</div>
                </div>
                <span className="text-muted-foreground">
                  {new Date(c.started_at).toLocaleString()}
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "analytics" && analytics && (
        <div className="grid gap-3 sm:grid-cols-4 text-xs">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-muted-foreground">Real Calls Initiated</div>
            <div className="mt-1 text-xl font-semibold">{analytics.real_calls_initiated}</div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-muted-foreground">Dry-Run Simulated</div>
            <div className="mt-1 text-xl font-semibold">{analytics.dry_run_calls_simulated}</div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-muted-foreground">Interested</div>
            <div className="mt-1 text-xl font-semibold">{analytics.interested_count}</div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-muted-foreground">Completion Rate</div>
            <div className="mt-1 text-xl font-semibold">{analytics.completion_rate_percent}%</div>
          </div>
        </div>
      )}
    </div>
  );
}
