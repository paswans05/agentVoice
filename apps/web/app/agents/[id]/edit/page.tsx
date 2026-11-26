"use client";

import type { AgentCreatePayload } from "@agentvoice/shared-types";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { AgentForm } from "@/components/agents/agent-form";
import { useAgent, useUpdateAgent } from "@/hooks/use-agents";

export default function EditAgentPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const agentId = params.id;

  const agentQuery = useAgent(agentId);
  const updateMutation = useUpdateAgent(agentId);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (agentQuery.isLoading) {
    return (
      <div className="mx-auto max-w-4xl rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Loading agent configuration...
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

  const handleSubmit = async (payload: AgentCreatePayload) => {
    setErrorMessage(null);
    try {
      await updateMutation.mutateAsync({
        name: payload.name,
        description: payload.description,
        avatar: payload.avatar,
        type: payload.type,
        personality: payload.personality,
        instructions: payload.instructions,
        language: payload.language,
        voice: payload.voice,
      });
      router.push(`/agents/${agentId}`);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to update agent.");
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href={`/agents/${agentId}`}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
          aria-label="Back to agent details"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Edit {agentQuery.data.name}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Update personality, instructions, language, or voice preferences.
          </p>
        </div>
      </div>

      <AgentForm
        mode="edit"
        initialAgent={agentQuery.data}
        isSubmitting={updateMutation.isPending}
        errorMessage={errorMessage}
        onSubmit={handleSubmit}
        onCancel={() => router.push(`/agents/${agentId}`)}
      />
    </div>
  );
}
