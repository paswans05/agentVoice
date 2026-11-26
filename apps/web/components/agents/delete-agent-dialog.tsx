"use client";

import { AlertTriangle } from "lucide-react";

interface DeleteAgentDialogProps {
  agentName: string;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteAgentDialog({
  agentName,
  isDeleting,
  onConfirm,
  onCancel,
}: DeleteAgentDialogProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-agent-title"
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-rose-500/15 text-rose-600 dark:text-rose-400">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h2 id="delete-agent-title" className="text-base font-semibold">
              Delete Agent
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Are you sure you want to delete <strong>{agentName}</strong>? This action removes the
              saved agent configuration permanently.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50"
          >
            {isDeleting ? "Deleting..." : "Delete Agent"}
          </button>
        </div>
      </div>
    </div>
  );
}
