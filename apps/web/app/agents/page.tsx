"use client";

import type { Agent, AgentStatus, AgentType } from "@agentvoice/shared-types";
import {
  Bot,
  Copy,
  Edit,
  Eye,
  Plus,
  Power,
  PowerOff,
  Search,
  Trash2,
} from "lucide-react";
import Link from "next/link";
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
  useAgents,
  useDeactivateAgent,
  useDeleteAgent,
  useDuplicateAgent,
} from "@/hooks/use-agents";

export default function AgentsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AgentStatus | "">("");
  const [typeFilter, setTypeFilter] = useState<AgentType | "">("");
  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null,
  );

  const agentsQuery = useAgents({ search, status: statusFilter, type: typeFilter });
  const duplicateMutation = useDuplicateAgent();
  const activateMutation = useActivateAgent();
  const deactivateMutation = useDeactivateAgent();
  const deleteMutation = useDeleteAgent();

  const handleDuplicate = async (agent: Agent) => {
    setFeedback(null);
    try {
      const copy = await duplicateMutation.mutateAsync(agent.id);
      setFeedback({ type: "success", text: `Duplicated as "${copy.name}" (DRAFT).` });
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to duplicate agent.",
      });
    }
  };

  const handleToggleActive = async (agent: Agent) => {
    setFeedback(null);
    try {
      if (agent.status === "ACTIVE") {
        await deactivateMutation.mutateAsync(agent.id);
        setFeedback({ type: "success", text: `"${agent.name}" deactivated.` });
      } else {
        await activateMutation.mutateAsync(agent.id);
        setFeedback({ type: "success", text: `"${agent.name}" activated.` });
      }
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to update agent status.",
      });
    }
  };

  const handleConfirmDelete = async () => {
    if (!agentToDelete) return;
    setFeedback(null);
    try {
      await deleteMutation.mutateAsync(agentToDelete.id);
      setFeedback({ type: "success", text: `Deleted "${agentToDelete.name}".` });
      setAgentToDelete(null);
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to delete agent.",
      });
      setAgentToDelete(null);
    }
  };

  const agents = agentsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AI Agents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create, configure, and manage local-first AI voice agents.
          </p>
        </div>
        <Link
          href="/agents/new"
          className="inline-flex items-center gap-2 self-start rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          Create Agent
        </Link>
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

      {/* Search & Filters */}
      <div className="grid gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents..."
            aria-label="Search agents"
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AgentStatus | "")}
          aria-label="Filter by status"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="DRAFT">DRAFT</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="INACTIVE">INACTIVE</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as AgentType | "")}
          aria-label="Filter by type"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">All Types</option>
          {(Object.keys(AGENT_TYPE_LABELS) as AgentType[]).map((t) => (
            <option key={t} value={t}>
              {AGENT_TYPE_LABELS[t]}
            </option>
          ))}
        </select>
      </div>

      {/* Loading / Error / Empty / List */}
      {agentsQuery.isLoading ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Loading agents...
        </div>
      ) : agentsQuery.isError ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-700 dark:text-rose-300">
          Failed to load agents:{" "}
          {agentsQuery.error instanceof Error ? agentsQuery.error.message : "Unknown error"}
        </div>
      ) : agents.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Bot className="h-6 w-6" />
          </div>
          <h2 className="mt-4 text-base font-semibold">No agents found</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {search || statusFilter || typeFilter
              ? "Try clearing your search or filters."
              : "Create your first local AI voice agent to get started."}
          </p>
          <Link
            href="/agents/new"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            Create Agent
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="flex flex-col justify-between rounded-xl border border-border bg-card p-5"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <AgentAvatar avatar={agent.avatar} />
                    </div>
                    <div className="min-w-0">
                      <Link
                        href={`/agents/${agent.id}`}
                        className="block truncate text-base font-semibold hover:text-primary"
                      >
                        {agent.name}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {AGENT_TYPE_LABELS[agent.type]}
                      </div>
                    </div>
                  </div>
                  <AgentStatusBadge status={agent.status} />
                </div>

                <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
                  {agent.description || "No description provided."}
                </p>

                <dl className="mt-4 grid grid-cols-2 gap-2 border-t border-border pt-3 text-xs">
                  <div>
                    <dt className="text-muted-foreground">Primary Language</dt>
                    <dd className="mt-0.5 font-medium">
                      {agent.language.primary_language}
                      {agent.language.hinglish_enabled ? " (Hinglish)" : ""}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Voice Preference</dt>
                    <dd className="mt-0.5 truncate font-medium">
                      {agent.voice.provider} · {agent.voice.voice_id}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-muted-foreground">Last Updated</dt>
                    <dd className="mt-0.5 font-medium">{formatAgentDate(agent.updated_at)}</dd>
                  </div>
                </dl>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3">
                <Link
                  href={`/agents/${agent.id}`}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                >
                  <Eye className="h-3.5 w-3.5" />
                  View
                </Link>
                <Link
                  href={`/agents/${agent.id}/edit`}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                >
                  <Edit className="h-3.5 w-3.5" />
                  Edit
                </Link>
                <button
                  type="button"
                  onClick={() => void handleDuplicate(agent)}
                  disabled={duplicateMutation.isPending}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
                >
                  <Copy className="h-3.5 w-3.5" />
                  Duplicate
                </button>
                <button
                  type="button"
                  onClick={() => void handleToggleActive(agent)}
                  disabled={activateMutation.isPending || deactivateMutation.isPending}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
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
                  onClick={() => setAgentToDelete(agent)}
                  className="ml-auto inline-flex items-center gap-1 rounded-lg border border-rose-500/30 px-2.5 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {agentToDelete && (
        <DeleteAgentDialog
          agentName={agentToDelete.name}
          isDeleting={deleteMutation.isPending}
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setAgentToDelete(null)}
        />
      )}
    </div>
  );
}
