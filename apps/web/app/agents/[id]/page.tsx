"use client";

import { ArrowLeft, Copy, Edit, MessageSquare, Power, PowerOff, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  AGENT_TYPE_LABELS,
  AgentAvatar,
  AgentStatusBadge,
  formatAgentDate,
} from "@/components/agents/agent-badges";
import { DeleteAgentDialog } from "@/components/agents/delete-agent-dialog";
import {
  useActivateAgent,
  useAgent,
  useDeactivateAgent,
  useDeleteAgent,
  useDuplicateAgent,
} from "@/hooks/use-agents";

export default function AgentDetailsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const agentId = params.id;

  const agentQuery = useAgent(agentId);
  const activateMutation = useActivateAgent();
  const deactivateMutation = useDeactivateAgent();
  const duplicateMutation = useDuplicateAgent();
  const deleteMutation = useDeleteAgent();

  const [showDelete, setShowDelete] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null,
  );

  if (agentQuery.isLoading) {
    return (
      <div className="mx-auto max-w-4xl rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Loading agent details...
      </div>
    );
  }

  if (agentQuery.isError || !agentQuery.data) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Link href="/agents" className="inline-flex items-center gap-1.5 text-sm text-primary">
          <ArrowLeft className="h-4 w-4" />
          Back to AI Agents
        </Link>
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-700 dark:text-rose-300">
          {agentQuery.error instanceof Error ? agentQuery.error.message : "Agent not found."}
        </div>
      </div>
    );
  }

  const agent = agentQuery.data;

  const handleToggleActive = async () => {
    setFeedback(null);
    try {
      if (agent.status === "ACTIVE") {
        await deactivateMutation.mutateAsync(agent.id);
        setFeedback({ type: "success", text: "Agent deactivated." });
      } else {
        await activateMutation.mutateAsync(agent.id);
        setFeedback({ type: "success", text: "Agent activated." });
      }
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to change status.",
      });
    }
  };

  const handleDuplicate = async () => {
    setFeedback(null);
    try {
      const copy = await duplicateMutation.mutateAsync(agent.id);
      router.push(`/agents/${copy.id}`);
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to duplicate agent.",
      });
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(agent.id);
      router.push("/agents");
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to delete agent.",
      });
      setShowDelete(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/agents"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
            aria-label="Back to agents"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <AgentAvatar avatar={agent.avatar} className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-semibold tracking-tight">{agent.name}</h1>
              <AgentStatusBadge status={agent.status} />
            </div>
            <p className="text-xs text-muted-foreground">
              {AGENT_TYPE_LABELS[agent.type]} · Version {agent.version}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/agents/${agent.id}/playground`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-primary/10 px-3 py-2 text-xs font-medium text-primary hover:bg-primary/20"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Test in Playground
          </Link>
          <Link
            href={`/agents/${agent.id}/edit`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <Edit className="h-3.5 w-3.5" />
            Edit
          </Link>
          <button
            type="button"
            onClick={() => void handleDuplicate()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <Copy className="h-3.5 w-3.5" />
            Duplicate
          </button>
          <button
            type="button"
            onClick={() => void handleToggleActive()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90"
          >
            {agent.status === "ACTIVE" ? (
              <>
                <PowerOff className="h-3.5 w-3.5" />
                Deactivate
              </>
            ) : (
              <>
                <Power className="h-3.5 w-3.5" />
                Activate
              </>
            )}
          </button>
          <button
            type="button"
            onClick={() => setShowDelete(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      </div>

      {feedback && (
        <div
          role="status"
          className={`rounded-xl border p-3.5 text-sm ${
            feedback.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
              : "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300"
          }`}
        >
          {feedback.text}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-border bg-card p-5 space-y-2">
          <h2 className="text-sm font-semibold">General Information</h2>
          <p className="text-sm text-muted-foreground">
            {agent.description || "No description provided."}
          </p>
          <dl className="pt-2 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Agent ID</dt>
              <dd className="font-mono">{agent.id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Created</dt>
              <dd>{formatAgentDate(agent.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Last Updated</dt>
              <dd>{formatAgentDate(agent.updated_at)}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-border bg-card p-5 space-y-2">
          <h2 className="text-sm font-semibold">Personality</h2>
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Tone</dt>
              <dd className="font-medium">{agent.personality.tone}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Traits</dt>
              <dd className="text-right font-medium">
                {agent.personality.traits.join(", ") || "—"}
              </dd>
            </div>
          </dl>
          {agent.personality.custom_instructions && (
            <p className="pt-2 text-xs text-muted-foreground">
              {agent.personality.custom_instructions}
            </p>
          )}
        </section>

        <section className="rounded-xl border border-border bg-card p-5 space-y-2">
          <h2 className="text-sm font-semibold">Language</h2>
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Primary Language</dt>
              <dd className="font-medium">{agent.language.primary_language}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Supported Languages</dt>
              <dd className="font-medium">{agent.language.supported_languages.join(", ")}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Hinglish Mode</dt>
              <dd className="font-medium">
                {agent.language.hinglish_enabled ? "Enabled" : "Disabled"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Response Mode</dt>
              <dd className="font-medium">{agent.language.response_mode}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-border bg-card p-5 space-y-2">
          <h2 className="text-sm font-semibold">Voice Preferences</h2>
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Provider</dt>
              <dd className="font-medium">{agent.voice.provider}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Voice ID</dt>
              <dd className="font-mono">{agent.voice.voice_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Speed</dt>
              <dd className="font-medium">{agent.voice.speed.toFixed(2)}x</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Pitch</dt>
              <dd className="font-medium">{agent.voice.pitch.toFixed(2)}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-border bg-card p-5 space-y-2 md:col-span-2">
          <h2 className="text-sm font-semibold">Local AI Model</h2>
          <dl className="grid gap-2 text-xs sm:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">Provider</dt>
              <dd className="font-medium">{agent.model?.provider ?? "ollama"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Model ID</dt>
              <dd className="font-mono">{agent.model?.model_id || "Default"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Temperature</dt>
              <dd className="font-medium">{(agent.model?.temperature ?? 0.7).toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Max Tokens</dt>
              <dd className="font-medium">{agent.model?.max_tokens ?? 512}</dd>
            </div>
          </dl>
        </section>
      </div>

      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold">Instructions</h2>
        <div>
          <div className="text-xs font-medium text-muted-foreground">System Prompt</div>
          <p className="mt-1 whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-sm">
            {agent.instructions.system_prompt || "No system prompt configured."}
          </p>
        </div>
        <div>
          <div className="text-xs font-medium text-muted-foreground">Opening Greeting</div>
          <p className="mt-1 whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-sm">
            {agent.instructions.greeting || "No greeting configured."}
          </p>
        </div>
        {agent.instructions.additional_rules.length > 0 && (
          <div>
            <div className="text-xs font-medium text-muted-foreground">Additional Rules</div>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
              {agent.instructions.additional_rules.map((rule, idx) => (
                <li key={idx}>{rule}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {showDelete && (
        <DeleteAgentDialog
          agentName={agent.name}
          isDeleting={deleteMutation.isPending}
          onConfirm={() => void handleDelete()}
          onCancel={() => setShowDelete(false)}
        />
      )}
    </div>
  );
}
