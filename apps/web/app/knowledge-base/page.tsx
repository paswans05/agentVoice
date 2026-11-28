"use client";

import { BookOpen, Database, FileText, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ClayButton, ClayStatCard } from "@/components/clay";
import {
  useCreateKnowledgeBase,
  useDeleteKnowledgeBase,
  useKnowledgeBases,
} from "@/hooks/use-knowledge";

export default function KnowledgeBasePage() {
  const kbsQuery = useKnowledgeBases();
  const createMutation = useCreateKnowledgeBase();
  const deleteMutation = useDeleteKnowledgeBase();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const kbs = kbsQuery.data ?? [];
  const totalDocs = kbs.reduce((acc, kb) => acc + kb.document_count, 0);
  const totalChunks = kbs.reduce((acc, kb) => acc + kb.chunk_count, 0);
  const failedKbs = kbs.filter((kb) => kb.status === "FAILED").length;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 2) {
      setError("Knowledge base name must be at least 2 characters.");
      return;
    }
    setError(null);
    try {
      await createMutation.mutateAsync({ name: name.trim(), description: description.trim() });
      setName("");
      setDescription("");
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create knowledge base.");
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Knowledge Base</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload company documents locally for grounded RAG responses in Hindi, Hinglish, and
            English.
          </p>
        </div>
        <ClayButton
          type="button"
          variant="primary"
          onClick={() => setShowCreate((v) => !v)}
          className="self-start"
        >
          <Plus className="h-4 w-4" />
          New Knowledge Base
        </ClayButton>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <ClayStatCard
          label="Knowledge Bases"
          accent="lavender"
          icon={<BookOpen className="h-4 w-4" />}
          value={kbs.length}
        />
        <ClayStatCard
          label="Total Documents"
          accent="sky"
          icon={<FileText className="h-4 w-4" />}
          value={totalDocs}
        />
        <ClayStatCard
          label="Indexed Chunks"
          accent="mint"
          icon={<Database className="h-4 w-4" />}
          value={totalChunks}
        />
        <ClayStatCard
          label="Failed KBs"
          accent="coral"
          value={failedKbs}
        />
      </div>

      {showCreate && (
        <form
          onSubmit={(e) => void handleCreate(e)}
          className="rounded-xl border border-border bg-card p-5 space-y-4"
        >
          <h2 className="text-base font-semibold">Create Knowledge Base</h2>
          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-300">
              {error}
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="kb-name" className="block text-xs font-medium">
                Name *
              </label>
              <input
                id="kb-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Product Pricing & FAQs"
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="kb-desc" className="block text-xs font-medium">
                Description
              </label>
              <input
                id="kb-desc"
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Verified company pricing and support policies"
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-lg border border-border px-3.5 py-2 text-xs font-medium hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      )}

      {kbsQuery.isLoading ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Loading knowledge bases...
        </div>
      ) : kbs.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <p className="text-sm text-muted-foreground">
            No knowledge bases yet. Create one to upload PDF, DOCX, TXT, Markdown, CSV, HTML, or
            JSON files.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {kbs.map((kb) => (
            <div
              key={kb.id}
              className="flex flex-col justify-between rounded-xl border border-border bg-card p-5"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <Link
                    href={`/knowledge-base/${kb.id}`}
                    className="text-base font-semibold hover:text-primary"
                  >
                    {kb.name}
                  </Link>
                  <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-[11px] font-medium">
                    {kb.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {kb.description || "No description"}
                </p>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span>{kb.document_count} document(s)</span>
                  <span>{kb.chunk_count} chunk(s)</span>
                  <span>{kb.agent_ids.length} agent(s)</span>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                <Link
                  href={`/knowledge-base/${kb.id}`}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Manage Documents &amp; Test Retrieval →
                </Link>
                <button
                  type="button"
                  onClick={() => void deleteMutation.mutateAsync(kb.id)}
                  aria-label={`Delete ${kb.name}`}
                  className="text-xs text-rose-600 hover:underline dark:text-rose-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
