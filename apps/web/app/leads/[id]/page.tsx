"use client";

import type { ConsentChannel } from "@agentvoice/shared-types";
import { ArrowLeft, Ban, CheckCircle2, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useAgents } from "@/hooks/use-agents";
import {
  useLead,
  useLeadActivities,
  useLeadAgentAssignment,
  useLeadConsent,
  useLeadConsentMutations,
  useLeadEligibility,
  useSuppressionMutations,
} from "@/hooks/use-leads";

export default function LeadDetailsPage() {
  const params = useParams<{ id: string }>();
  const leadId = params.id;

  const leadQuery = useLead(leadId);
  const consentQuery = useLeadConsent(leadId);
  const eligibilityQuery = useLeadEligibility(leadId, "PHONE");
  const activitiesQuery = useLeadActivities(leadId);
  const agentsQuery = useAgents();

  const { assign, unassign } = useLeadAgentAssignment(leadId);
  const consentMut = useLeadConsentMutations(leadId);
  const suppressionMut = useSuppressionMutations();

  const [consentChannel, setConsentChannel] = useState<ConsentChannel>("PHONE");
  const [consentPurpose, setConsentPurpose] = useState("PRODUCT_INFORMATION");

  if (leadQuery.isLoading) {
    return (
      <div className="mx-auto max-w-5xl rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Loading lead details...
      </div>
    );
  }

  if (leadQuery.isError || !leadQuery.data) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <Link href="/leads" className="inline-flex items-center gap-1.5 text-sm text-primary">
          <ArrowLeft className="h-4 w-4" />
          Back to Leads
        </Link>
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-700 dark:text-rose-300">
          Lead not found.
        </div>
      </div>
    );
  }

  const lead = leadQuery.data;
  const eligibility = eligibilityQuery.data;
  const consents = consentQuery.data ?? [];
  const activities = activitiesQuery.data ?? [];
  const agents = agentsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/leads"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                {lead.full_name || "Unnamed Lead"}
              </h1>
              <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium">
                {lead.status}
              </span>
              {lead.suppressed && (
                <span className="rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-medium text-rose-600 dark:text-rose-400">
                  SUPPRESSED
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {lead.company || "No company"} · Priority: {lead.priority} · Source: {lead.source}
            </p>
          </div>
        </div>

        {!lead.suppressed && (
          <button
            type="button"
            onClick={() =>
              void suppressionMut.add.mutateAsync({
                lead_id: lead.id,
                reason: "Operator marked Do-Not-Contact",
              })
            }
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
          >
            <Ban className="h-3.5 w-3.5" />
            Add to Suppression List
          </button>
        )}
      </div>

      {/* Contact Eligibility */}
      {eligibility && (
        <div
          className={`rounded-xl border p-4 text-sm ${
            eligibility.eligible
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200"
              : "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200"
          }`}
        >
          <div className="flex items-center gap-2 font-semibold">
            {eligibility.eligible ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <ShieldAlert className="h-4 w-4" />
            )}
            <span>
              Future Contact Eligibility (PHONE / {eligibility.purpose}):{" "}
              {eligibility.eligible ? "ELIGIBLE" : "BLOCKED"}
            </span>
          </div>
          <p className="mt-1 text-xs">{eligibility.reason}</p>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Contact Info */}
        <section className="rounded-xl border border-border bg-card p-5 space-y-2 text-xs">
          <h2 className="text-sm font-semibold">Contact Information</h2>
          <dl className="space-y-1.5 pt-1">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Email</dt>
              <dd>{lead.email || "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Phone</dt>
              <dd>{lead.phone || "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Normalized Phone</dt>
              <dd className="font-mono">{lead.normalized_phone || "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Company</dt>
              <dd>{lead.company || "—"}</dd>
            </div>
          </dl>
        </section>

        {/* Agent Assignment */}
        <section className="rounded-xl border border-border bg-card p-5 space-y-3 text-xs">
          <h2 className="text-sm font-semibold">Assigned AI Agent</h2>
          <p className="text-muted-foreground">
            Assigning an agent organizes ownership only; it does not authorize outbound calls.
          </p>
          <div className="flex gap-2">
            <select
              value={lead.assigned_agent_id ?? ""}
              onChange={(e) => {
                if (e.target.value) {
                  void assign.mutateAsync(e.target.value);
                } else {
                  void unassign.mutateAsync();
                }
              }}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-xs"
            >
              <option value="">Unassigned</option>
              {agents.map((ag) => (
                <option key={ag.id} value={ag.id}>
                  {ag.name} ({ag.status})
                </option>
              ))}
            </select>
          </div>
        </section>

        {/* Consent Management */}
        <section className="rounded-xl border border-border bg-card p-5 space-y-3 text-xs">
          <h2 className="text-sm font-semibold">Consent Management</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <select
              value={consentChannel}
              onChange={(e) => setConsentChannel(e.target.value as ConsentChannel)}
              className="rounded-lg border border-border bg-background px-2.5 py-1.5"
            >
              {(["PHONE", "SMS", "EMAIL", "WHATSAPP", "WEB"] as ConsentChannel[]).map((ch) => (
                <option key={ch} value={ch}>
                  {ch}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={consentPurpose}
              onChange={(e) => setConsentPurpose(e.target.value)}
              className="rounded-lg border border-border bg-background px-2.5 py-1.5"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                void consentMut.grant.mutateAsync({
                  channel: consentChannel,
                  purpose: consentPurpose,
                  source: "operator_ui",
                  consent_status: "GRANTED",
                })
              }
              className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-700"
            >
              Record GRANTED
            </button>
            <button
              type="button"
              onClick={() =>
                void consentMut.revoke.mutateAsync({
                  channel: consentChannel,
                  purpose: consentPurpose,
                  reason: "Operator revoked consent",
                })
              }
              className="rounded-lg border border-rose-500/30 px-3 py-1.5 font-medium text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
            >
              Revoke Consent
            </button>
          </div>

          <div className="space-y-1.5 pt-2">
            {consents.map((c) => (
              <div key={c.id} className="flex justify-between rounded border border-border p-2">
                <span>
                  {c.channel} · {c.purpose}
                </span>
                <span className="font-medium">{c.consent_status}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Activity Timeline */}
        <section className="rounded-xl border border-border bg-card p-5 space-y-3 text-xs">
          <h2 className="text-sm font-semibold">Activity Timeline</h2>
          {activities.length === 0 ? (
            <p className="text-muted-foreground">No activity recorded.</p>
          ) : (
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {activities.map((act) => (
                <div key={act.activity_id} className="rounded border border-border p-2">
                  <div className="flex justify-between font-medium">
                    <span>{act.activity_type}</span>
                    <span className="text-muted-foreground">
                      {new Date(act.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-0.5 text-muted-foreground">{act.description}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
