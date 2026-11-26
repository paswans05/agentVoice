"use client";

import { STATUS_TONE_CLASSES } from "@agentvoice/ui";
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Download,
  RefreshCw,
  Server,
  Star,
  Trash2,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  useCancelPull,
  useDeleteModel,
  useModelsOverview,
  usePullModel,
  usePullStatus,
  useRefreshModels,
  useSetDefaultModel,
} from "@/hooks/use-models";

function formatBytes(bytes: number | null): string {
  if (!bytes || bytes <= 0) return "—";
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(2)} GB`;
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(0)} MB`;
}

export default function ModelsPage() {
  const overviewQuery = useModelsOverview();
  const refreshMutation = useRefreshModels();
  const setDefaultMutation = useSetDefaultModel();
  const pullMutation = usePullModel();
  const cancelPullMutation = useCancelPull();
  const deleteMutation = useDeleteModel();

  const [modelInput, setModelInput] = useState("");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null,
  );

  const pullStatusQuery = usePullStatus(activeTaskId);
  const pullTask = pullStatusQuery.data;

  useEffect(() => {
    if (pullTask?.status === "COMPLETED") {
      setFeedback({ type: "success", text: `Model "${pullTask.model_id}" downloaded.` });
      void refreshMutation.mutateAsync();
    } else if (pullTask?.status === "ERROR") {
      setFeedback({
        type: "error",
        text: pullTask.error ?? `Failed to download "${pullTask.model_id}".`,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pullTask?.status]);

  const handleStartPull = async (targetModelId: string) => {
    const trimmed = targetModelId.trim();
    if (!trimmed) return;
    setFeedback(null);
    try {
      const task = await pullMutation.mutateAsync(trimmed);
      setActiveTaskId(task.task_id);
      setModelInput("");
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to start model download.",
      });
    }
  };

  const handleCancelPull = async () => {
    if (!activeTaskId) return;
    try {
      await cancelPullMutation.mutateAsync(activeTaskId);
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to cancel download.",
      });
    }
  };

  const handleSetDefault = async (modelId: string) => {
    setFeedback(null);
    try {
      await setDefaultMutation.mutateAsync(modelId);
      setFeedback({ type: "success", text: `Default model set to "${modelId}".` });
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to set default model.",
      });
    }
  };

  const handleDelete = async (modelId: string) => {
    setFeedback(null);
    try {
      await deleteMutation.mutateAsync(modelId);
      setFeedback({ type: "success", text: `Deleted model "${modelId}".` });
    } catch (err) {
      setFeedback({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to delete model.",
      });
    }
  };

  const overview = overviewQuery.data;
  const runtime = overview?.runtime;
  const installed = overview?.installed ?? [];
  const recommendations = overview?.recommendations ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Model Manager</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Discover, download, and manage local LLM models powered by Ollama.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refreshMutation.mutateAsync()}
          disabled={refreshMutation.isPending || overviewQuery.isFetching}
          className="inline-flex items-center gap-2 self-start rounded-lg border border-border bg-card px-3.5 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              refreshMutation.isPending || overviewQuery.isFetching ? "animate-spin" : ""
            }`}
          />
          Refresh Models
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

      {/* Runtime Status */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Server className="h-5 w-5 text-primary" />
            <h2 className="text-base font-semibold">Local LLM Runtime (Ollama)</h2>
          </div>
          {overviewQuery.isLoading ? (
            <span className="text-xs text-muted-foreground">Checking runtime...</span>
          ) : runtime ? (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                STATUS_TONE_CLASSES[runtime.available ? "healthy" : "unavailable"]
              }`}
            >
              {runtime.available ? "Connected" : "Unavailable"}
            </span>
          ) : null}
        </div>

        <div className="grid gap-3 text-xs sm:grid-cols-3">
          <div>
            <span className="text-muted-foreground">Endpoint</span>
            <div className="mt-0.5 font-mono">{runtime?.endpoint ?? "http://localhost:11434"}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Version</span>
            <div className="mt-0.5 font-medium">{runtime?.version ?? "—"}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Default Model</span>
            <div className="mt-0.5 font-mono">{overview?.default_model_id ?? "Not selected"}</div>
          </div>
        </div>

        {runtime && !runtime.available && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
            <div className="flex items-center gap-1.5 font-semibold">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>Ollama is not reachable</span>
            </div>
            <p className="mt-1">
              {runtime.error ??
                "Install Ollama from https://ollama.com and run `ollama serve` on your machine, then click Refresh Models."}
            </p>
          </div>
        )}
      </section>

      {/* Download / Pull Model */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <h2 className="text-base font-semibold">Download Local Model</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Enter an Ollama model tag (for example, <code>qwen2.5:3b</code> or{" "}
            <code>llama3.2:3b</code>). Downloads only start when you click Download.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleStartPull(modelInput);
          }}
          className="flex flex-col gap-2 sm:flex-row"
        >
          <input
            type="text"
            value={modelInput}
            onChange={(e) => setModelInput(e.target.value)}
            placeholder="e.g., qwen2.5:3b"
            aria-label="Model identifier to download"
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
          <button
            type="submit"
            disabled={!modelInput.trim() || pullMutation.isPending || !runtime?.available}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Download Model
          </button>
        </form>

        {pullTask && (
          <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium">
                {pullTask.model_id} · {pullTask.status_text}
              </span>
              <span>{pullTask.progress_percent.toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${Math.min(100, Math.max(0, pullTask.progress_percent))}%` }}
              />
            </div>
            {pullTask.status === "DOWNLOADING" && (
              <button
                type="button"
                onClick={() => void handleCancelPull()}
                className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
              >
                <XCircle className="h-3.5 w-3.5" />
                Cancel Download
              </button>
            )}
          </div>
        )}
      </section>

      {/* Installed Models */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-base font-semibold">Installed Models ({installed.length})</h2>
        {installed.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {runtime?.available
              ? "No models installed in Ollama yet. Download a model above to get started."
              : "Connect Ollama to discover installed models."}
          </p>
        ) : (
          <div className="divide-y divide-border">
            {installed.map((model) => (
              <div
                key={model.id}
                className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold">{model.id}</span>
                    {model.is_default && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2 py-0.5 text-[11px] font-medium text-primary">
                        <CheckCircle2 className="h-3 w-3" />
                        Default
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span>Size: {formatBytes(model.size_bytes)}</span>
                    {model.family && <span>Family: {model.family}</span>}
                    {model.parameter_size && <span>Params: {model.parameter_size}</span>}
                    {model.quantization && <span>Quant: {model.quantization}</span>}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!model.is_default && (
                    <button
                      type="button"
                      onClick={() => void handleSetDefault(model.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                    >
                      <Star className="h-3.5 w-3.5" />
                      Set Default
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void handleDelete(model.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-rose-500/30 px-2.5 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Hardware Guidance */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Cpu className="h-5 w-5 text-primary" />
          <h2 className="text-base font-semibold">Hardware Guidance &amp; Model Recommendations</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Response speed depends on model size, quantization, CPU/GPU hardware, and context length.
          Test Hindi and Hinglish quality locally on your own prompts.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {recommendations.map((rec) => {
            const isInstalled = installed.some(
              (m) => m.id === rec.id || m.id === `${rec.id}:latest`,
            );
            return (
              <div key={rec.id} className="rounded-lg border border-border p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold">{rec.name}</div>
                    <div className="font-mono text-xs text-muted-foreground">{rec.id}</div>
                  </div>
                  {isInstalled ? (
                    <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                      Installed
                    </span>
                  ) : (
                    <button
                      type="button"
                      disabled={!runtime?.available || pullMutation.isPending}
                      onClick={() => void handleStartPull(rec.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50"
                    >
                      <Download className="h-3 w-3" />
                      Pull
                    </button>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  Size: {rec.approximate_size} · Min RAM: {rec.min_ram_gb} GB · {rec.quantization}
                </div>
                <p className="text-xs text-muted-foreground">{rec.language_notes}</p>
                <p className="text-xs text-muted-foreground">{rec.performance_notes}</p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
