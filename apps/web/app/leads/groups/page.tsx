"use client";

import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useGroupMutations, useLeadGroups } from "@/hooks/use-leads";

export default function LeadGroupsPage() {
  const groupsQuery = useLeadGroups();
  const { create, remove } = useGroupMutations();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 2) return;
    await create.mutateAsync({ name: name.trim(), description: description.trim() });
    setName("");
    setDescription("");
  };

  const groups = groupsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/leads"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Lead Groups</h1>
          <p className="text-xs text-muted-foreground">
            Organize leads into segments. Deleting a group does not delete its leads.
          </p>
        </div>
      </div>

      <form
        onSubmit={(e) => void handleCreate(e)}
        className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5 sm:flex-row"
      >
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Group name (e.g., Enterprise)"
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={create.isPending || name.trim().length < 2}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          Add Group
        </button>
      </form>

      <div className="divide-y divide-border rounded-xl border border-border bg-card">
        {groups.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">No groups created yet.</p>
        ) : (
          groups.map((g) => (
            <div key={g.id} className="flex items-center justify-between p-4">
              <div>
                <div className="font-medium text-sm">{g.name}</div>
                <div className="text-xs text-muted-foreground">{g.description || "—"}</div>
              </div>
              <button
                type="button"
                onClick={() => void remove.mutateAsync(g.id)}
                className="text-rose-600 hover:text-rose-700 dark:text-rose-400"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
