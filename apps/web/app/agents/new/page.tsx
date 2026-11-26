"use client";

import type { AgentCreatePayload } from "@agentvoice/shared-types";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AgentForm } from "@/components/agents/agent-form";
import { useActivateAgent, useAgentTemplates, useCreateAgent } from "@/hooks/use-agents";

export default function NewAgentPage() {
  const router = useRouter();
  const templatesQuery = useAgentTemplates();
  const createMutation = useCreateAgent();
  const activateMutation = useActivateAgent();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (payload: AgentCreatePayload, activateAfterSave: boolean) => {
    setErrorMessage(null);
    try {
      const created = await createMutation.mutateAsync(payload);
      if (activateAfterSave) {
        await activateMutation.mutateAsync(created.id);
      }
      router.push(`/agents/${created.id}`);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to create agent.");
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/agents"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
          aria-label="Back to agents"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Create AI Agent</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Configure personality, instructions, Hindi/Hinglish/English language, and voice
            preferences.
          </p>
        </div>
      </div>

      <AgentForm
        mode="create"
        templates={templatesQuery.data ?? []}
        isSubmitting={createMutation.isPending || activateMutation.isPending}
        errorMessage={errorMessage}
        onSubmit={handleSubmit}
        onCancel={() => router.push("/agents")}
      />
    </div>
  );
}
