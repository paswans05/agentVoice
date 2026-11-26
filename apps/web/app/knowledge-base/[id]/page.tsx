"use client";

import {
  ArrowLeft,
  FileText,
  Power,
  PowerOff,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useAgents } from "@/hooks/use-agents";
import {
  useAssignKBAgent,
  useDeleteKBDocument,
  useKBDocuments,
  useKnowledgeBase,
  useReprocessKBDocument,
  useSearchKnowledgeBase,
  useToggleKnowledgeBase,
  useUploadKBDocuments,
} from "@/hooks/use-knowledge";

export default function KnowledgeBaseDetailPage() {
  const params = useParams<{ id: string }>();
  const kbId = params.id;

  const kbQuery = useKnowledgeBase(kbId);
  const docsQuery = useKBDocuments(kbId);
  const agentsQuery = useAgents();

  const toggleMutation = useToggleKnowledgeBase(kbId);
  const uploadMutation = useUploadKBDocuments(kbId);
  const deleteDocMutation = useDeleteKBDocument(kbId);
  const reprocessDocMutation = useReprocessKBDocument(kbId);
  const assignAgentMutation = useAssignKBAgent(kbId);
  const searchMutation = useSearchKnowledgeBase(kbId);

  const [docSearch, setDocSearch] = useState("");
  const [testQuery, setTestQuery] = useState("");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null,
  );
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setFeedback(null);
    try {
      const uploaded = await uploadMutation.mutateAsync(Array.from(fileList));
      const failed = uploaded.filter((d) => d.status === "FAILED");
      if (failed.length > 0) {
        setFeedback({
          type: "error",
          text: `${failed.length} file(s) failed: ${failed[0].error_message ?? "Unknown error"}`,
        });
      } else {
        setFeedback({
          type: "success",
          text: `Indexed ${uploaded.length} document(s) successfully.`,
        });
      }
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Upload failed.",
      });
    }
  };

  const handleRetrievalTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testQuery.trim()) return;
    await searchMutation.mutateAsync({ query: testQuery.trim(), topK: 5 });
  };

  if (kbQuery.isLoading) {
    return (
      <div className="mx-auto max-w-5xl rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Loading knowledge base...
      </div>
    );
  }

  if (kbQuery.isError || !kbQuery.data) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <Link href="/knowledge-base" className="inline-flex items-center gap-1.5 text-sm text-primary">
          <ArrowLeft className="h-4 w-4" />
          Back to Knowledge Base
        </Link>
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-700 dark:text-rose-300">
          Knowledge base not found.
        </div>
      </div>
    );
  }

  const kb = kbQuery.data;
  const docs = (docsQuery.data ?? []).filter((d) =>
    docSearch.trim() ? d.filename.toLowerCase().includes(docSearch.toLowerCase()) : true,
  );
  const agents = agentsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/knowledge-base"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
            aria-label="Back to knowledge bases"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{kb.name}</h1>
              <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium">
                {kb.status}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {kb.document_count} documents · {kb.chunk_count} chunks · Embedding:{" "}
              <code>{kb.embedding_model}</code>
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void toggleMutation.mutateAsync(!kb.enabled)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3.5 py-2 text-xs font-medium hover:bg-muted"
        >
          {kb.enabled ? (
            <>
              <PowerOff className="h-3.5 w-3.5" />
              Disable
            </>
          ) : (
            <>
              <Power className="h-3.5 w-3.5" />
              Enable
            </>
          )}
        </button>
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

      {/* Upload Zone */}
      <section
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          void handleFiles(e.dataTransfer.files);
        }}
        className={`rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
          dragActive ? "border-primary bg-primary/5" : "border-border bg-card"
        }`}
      >
        <UploadCloud className="mx-auto h-8 w-8 text-primary" />
        <p className="mt-2 text-sm font-medium">
          {uploadMutation.isPending
            ? "Extracting, chunking, and embedding documents..."
            : "Drag & drop documents here, or choose files"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Supported: PDF, DOCX, TXT, Markdown (.md), CSV, HTML, JSON
        </p>
        <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90">
          <span>Select Files</span>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md,.csv,.html,.htm,.json"
            onChange={(e) => void handleFiles(e.target.files)}
            className="hidden"
          />
        </label>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Document List */}
        <section className="rounded-xl border border-border bg-card p-5 space-y-4 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold">Documents ({docs.length})</h2>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="search"
                value={docSearch}
                onChange={(e) => setDocSearch(e.target.value)}
                placeholder="Search filenames..."
                className="rounded-lg border border-border bg-background py-1.5 pl-8 pr-3 text-xs"
              />
            </div>
          </div>

          {docs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>
          ) : (
            <div className="divide-y divide-border">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-primary" />
                      <span className="truncate text-sm font-medium">{doc.filename}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                        {doc.status}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {doc.chunk_count} chunks · {(doc.size_bytes / 1024).toFixed(1)} KB
                      {doc.error_message && (
                        <span className="ml-2 text-rose-500">{doc.error_message}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void reprocessDocMutation.mutateAsync(doc.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 text-xs hover:bg-muted"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Reprocess
                    </button>
                    <button
                      type="button"
                      onClick={() => void deleteDocMutation.mutateAsync(doc.id)}
                      aria-label={`Delete ${doc.filename}`}
                      className="rounded-lg border border-rose-500/30 p-1.5 text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Agent Assignment */}
        <section className="rounded-xl border border-border bg-card p-5 space-y-3">
          <h2 className="text-base font-semibold">Assigned Agents</h2>
          <p className="text-xs text-muted-foreground">
            Only checked agents can retrieve from this knowledge base.
          </p>
          {agents.length === 0 ? (
            <p className="text-xs text-muted-foreground">No agents created yet.</p>
          ) : (
            <div className="space-y-2">
              {agents.map((ag) => {
                const isAssigned = kb.agent_ids.includes(ag.id);
                return (
                  <label key={ag.id} className="flex items-center gap-2.5 text-sm">
                    <input
                      type="checkbox"
                      checked={isAssigned}
                      onChange={() =>
                        void assignAgentMutation.mutateAsync({
                          agentId: ag.id,
                          assign: !isAssigned,
                        })
                      }
                      className="rounded border-border"
                    />
                    <span>{ag.name}</span>
                  </label>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* Retrieval Testing Diagnostic */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <h2 className="text-base font-semibold">Retrieval Testing Playground</h2>
          <p className="text-xs text-muted-foreground">
            Test semantic search in Hindi, Hinglish, or English and inspect retrieved chunks and
            scores.
          </p>
        </div>

        <form onSubmit={(e) => void handleRetrievalTest(e)} className="flex gap-2">
          <input
            type="text"
            value={testQuery}
            onChange={(e) => setTestQuery(e.target.value)}
            placeholder="e.g., आपके product की कीमत कितनी है?"
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={searchMutation.isPending || !testQuery.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {searchMutation.isPending ? "Searching..." : "Test Retrieval"}
          </button>
        </form>

        {searchMutation.isError && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-300">
            {searchMutation.error instanceof Error
              ? searchMutation.error.message
              : "Retrieval search failed."}
          </div>
        )}

        {searchMutation.data && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-xs">
              <span
                className={`rounded-full px-2.5 py-0.5 font-medium ${
                  searchMutation.data.grounded
                    ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                    : "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                }`}
              >
                {searchMutation.data.grounded ? "Grounded (Matches Found)" : "No Grounded Match"}
              </span>
              <span className="text-muted-foreground">
                Latency: {searchMutation.data.retrieval_ms}ms · {searchMutation.data.hits.length}{" "}
                hit(s)
              </span>
            </div>

            {searchMutation.data.hits.map((hit) => (
              <div key={hit.chunk_id} className="rounded-lg border border-border p-3 text-xs space-y-1">
                <div className="flex justify-between font-medium">
                  <span>
                    {hit.filename}
                    {hit.page_number ? ` (p. ${hit.page_number})` : ""}
                  </span>
                  <span className="text-primary">Score: {hit.score.toFixed(3)}</span>
                </div>
                <p className="text-muted-foreground whitespace-pre-wrap">{hit.content}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
