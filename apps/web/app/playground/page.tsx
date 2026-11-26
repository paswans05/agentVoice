"use client";

import { Bot, Mic, ArrowRight } from "lucide-react";
import Link from "next/link";
import { AGENT_TYPE_LABELS, AgentAvatar, AgentStatusBadge } from "@/components/agents/agent-badges";
import { useAgents } from "@/hooks/use-agents";

export default function PlaygroundDirectoryPage() {
  const agentsQuery = useAgents();
  const agents = agentsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Voice Playground</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Select an AI agent to start a real-time local voice or text conversation.
        </p>
      </div>

      {agentsQuery.isLoading ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Loading agents...
        </div>
      ) : agents.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Bot className="h-6 w-6" />
          </div>
          <h2 className="mt-4 text-base font-semibold">No agents available</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Create an AI agent first, then open it in the Voice Playground.
          </p>
          <Link
            href="/agents/new"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            Create Agent
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {agents.map((agent) => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}/playground`}
              className="group flex items-center justify-between rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/50"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <AgentAvatar avatar={agent.avatar} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold">{agent.name}</span>
                    <AgentStatusBadge status={agent.status} />
                  </div>
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    {AGENT_TYPE_LABELS[agent.type]} · {agent.language.primary_language} ·{" "}
                    {agent.model?.model_id || "Default LLM"}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
                <Mic className="h-4 w-4" />
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
