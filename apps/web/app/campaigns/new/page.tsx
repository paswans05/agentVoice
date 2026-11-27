"use client";

import type { CampaignType } from "@agentvoice/shared-types";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAgents } from "@/hooks/use-agents";
import { useCreateCampaign } from "@/hooks/use-campaigns";
import { useLeadGroups, useLeads } from "@/hooks/use-leads";

const STEPS = ["Info", "AI Agent", "Leads", "Schedule", "Retry", "Review"] as const;

const CAMPAIGN_TYPES: CampaignType[] = [
  "SALES",
  "LEAD_QUALIFICATION",
  "APPOINTMENT_BOOKING",
  "CUSTOMER_FOLLOW_UP",
  "PRODUCT_INFORMATION",
  "CUSTOM",
];

export default function NewCampaignPage() {
  const router = useRouter();
  const agentsQuery = useAgents({ status: "ACTIVE" });
  const leadsQuery = useLeads({ page: 1, page_size: 100 });
  const groupsQuery = useLeadGroups();
  const createMutation = useCreateCampaign();

  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");
  const [campaignType, setCampaignType] = useState<CampaignType>("SALES");
  const [agentId, setAgentId] = useState("");
  const [callingPurpose, setCallingPurpose] = useState("SALES_CALLS");
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [selectedGroupIds, setSelectedGroupIds] = useState<string[]>([]);
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("20:00");
  const [maxCalls, setMaxCalls] = useState(100);
  const [maxConcurrency, setMaxConcurrency] = useState(2);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [retryInterval, setRetryInterval] = useState(30);
  const [dryRun, setDryRun] = useState(true);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeAgents = agentsQuery.data ?? [];
  const leads = leadsQuery.data?.items ?? [];
  const groups = groupsQuery.data ?? [];

  const toggleItem = (list: string[], id: string, setter: (v: string[]) => void) => {
    setter(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  };

  const handleCreate = async () => {
    if (name.trim().length < 2) {
      setError("Campaign name must be at least 2 characters.");
      return;
    }
    if (!agentId) {
      setError("Select an ACTIVE AI agent.");
      return;
    }
    if (!confirmed) {
      setError("Please confirm the campaign summary before creating.");
      return;
    }
    setError(null);
    try {
      const created = await createMutation.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        notes: notes.trim(),
        campaign_type: campaignType,
        agent_id: agentId,
        calling_purpose: callingPurpose,
        selected_lead_ids: selectedLeadIds,
        lead_group_ids: selectedGroupIds,
        timezone,
        start_time: startTime,
        end_time: endTime,
        maximum_calls: maxCalls,
        maximum_concurrent_calls: maxConcurrency,
        maximum_attempts_per_lead: maxAttempts,
        retry_interval_minutes: retryInterval,
        dry_run: dryRun,
        telephony_provider: dryRun ? "dry_run" : "sip",
      });
      router.push(`/campaigns/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create campaign.");
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/campaigns"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Create Campaign</h1>
          <p className="text-xs text-muted-foreground">
            Guided 6-step campaign setup with consent &amp; schedule validation.
          </p>
        </div>
      </div>

      {/* Stepper */}
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {STEPS.map((label, idx) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(idx)}
            className={`rounded-lg border px-2.5 py-2 text-xs font-medium ${
              idx === step
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground hover:bg-muted"
            }`}
          >
            {idx + 1}. {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card p-6 space-y-4 text-sm">
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium">Campaign Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Q4 Hindi Product Outreach"
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Campaign Type</label>
              <select
                value={campaignType}
                onChange={(e) => setCampaignType(e.target.value as CampaignType)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              >
                {CAMPAIGN_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium">Description</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Internal Notes</label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium">Select Active AI Agent *</label>
              <select
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              >
                <option value="">— Select an ACTIVE agent —</option>
                {activeAgents.map((ag) => (
                  <option key={ag.id} value={ag.id}>
                    {ag.name} ({ag.language.primary_language} · {ag.model?.model_id || "Default LLM"})
                  </option>
                ))}
              </select>
              {activeAgents.length === 0 && (
                <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                  No ACTIVE agents found. Activate an agent in{" "}
                  <Link href="/agents" className="underline">
                    AI Agents
                  </Link>
                  .
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium">Calling Purpose (Consent Scope)</label>
              <select
                value={callingPurpose}
                onChange={(e) => setCallingPurpose(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              >
                <option value="SALES_CALLS">SALES_CALLS</option>
                <option value="PRODUCT_INFORMATION">PRODUCT_INFORMATION</option>
                <option value="APPOINTMENT_REMINDERS">APPOINTMENT_REMINDERS</option>
                <option value="SERVICE_UPDATES">SERVICE_UPDATES</option>
              </select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="text-xs text-muted-foreground">
              Selected: {selectedLeadIds.length} lead(s), {selectedGroupIds.length} group(s).
              Eligibility, consent, and suppression are re-validated before every call.
            </div>
            {groups.length > 0 && (
              <div>
                <div className="text-xs font-semibold mb-2">Lead Groups</div>
                <div className="flex flex-wrap gap-2">
                  {groups.map((g) => (
                    <label
                      key={g.id}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs"
                    >
                      <input
                        type="checkbox"
                        checked={selectedGroupIds.includes(g.id)}
                        onChange={() => toggleItem(selectedGroupIds, g.id, setSelectedGroupIds)}
                      />
                      <span>{g.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div>
              <div className="text-xs font-semibold mb-2">Individual Leads</div>
              <div className="max-h-56 space-y-1.5 overflow-y-auto rounded-lg border border-border p-3">
                {leads.map((l) => (
                  <label key={l.id} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedLeadIds.includes(l.id)}
                        onChange={() => toggleItem(selectedLeadIds, l.id, setSelectedLeadIds)}
                      />
                      <span>{l.full_name || l.phone || l.email}</span>
                    </span>
                    <span className="text-muted-foreground">
                      {l.consent_status} {l.suppressed ? "· SUPPRESSED" : ""}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium">Timezone</label>
              <input
                type="text"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Execution Mode</label>
              <label className="mt-2 flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                />
                <span>Dry-Run Mode (Local simulation only, no real calls)</span>
              </label>
            </div>
            <div>
              <label className="block text-xs font-medium">Start Time (HH:MM)</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">End Time (HH:MM)</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Max Calls</label>
              <input
                type="number"
                min={1}
                value={maxCalls}
                onChange={(e) => setMaxCalls(Number(e.target.value) || 100)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Max Concurrent Calls</label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxConcurrency}
                onChange={(e) => setMaxConcurrency(Number(e.target.value) || 2)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium">Max Attempts per Lead</label>
              <input
                type="number"
                min={1}
                max={10}
                value={maxAttempts}
                onChange={(e) => setMaxAttempts(Number(e.target.value) || 3)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Base Retry Interval (minutes)</label>
              <input
                type="number"
                min={1}
                value={retryInterval}
                onChange={(e) => setRetryInterval(Number(e.target.value) || 30)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
              />
            </div>
            <p className="sm:col-span-2 text-xs text-muted-foreground">
              Opt-outs, DO_NOT_CONTACT, revoked consent, and completed calls are never retried.
            </p>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4 text-xs">
            <h2 className="text-sm font-semibold">Campaign Summary</h2>
            <dl className="grid gap-2 sm:grid-cols-2">
              <div className="rounded border border-border p-3">
                <dt className="text-muted-foreground">Name &amp; Type</dt>
                <dd className="font-medium mt-0.5">
                  {name || "—"} · {campaignType}
                </dd>
              </div>
              <div className="rounded border border-border p-3">
                <dt className="text-muted-foreground">Mode &amp; Purpose</dt>
                <dd className="font-medium mt-0.5">
                  {dryRun ? "Dry-Run Simulation" : "Real Telephony"} · {callingPurpose}
                </dd>
              </div>
              <div className="rounded border border-border p-3">
                <dt className="text-muted-foreground">Schedule</dt>
                <dd className="font-medium mt-0.5">
                  {timezone} · {startTime}–{endTime}
                </dd>
              </div>
              <div className="rounded border border-border p-3">
                <dt className="text-muted-foreground">Targets</dt>
                <dd className="font-medium mt-0.5">
                  {selectedLeadIds.length} leads, {selectedGroupIds.length} groups
                </dd>
              </div>
            </dl>
            <label className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              <span>
                I confirm this campaign configuration and consent/suppression rules.
              </span>
            </label>
          </div>
        )}
      </div>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-4 py-2 text-xs font-medium disabled:opacity-50"
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </button>

        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
            className="inline-flex items-center gap-1 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            disabled={createMutation.isPending}
            onClick={() => void handleCreate()}
            className="rounded-lg bg-primary px-5 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {createMutation.isPending ? "Creating..." : "Create Campaign"}
          </button>
        )}
      </div>
    </div>
  );
}
