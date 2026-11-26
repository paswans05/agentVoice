"use client";

import { ArrowLeft, Ban, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useSuppressionList, useSuppressionMutations } from "@/hooks/use-leads";

export default function SuppressionListPage() {
  const [search, setSearch] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("Opt-out requested");

  const listQuery = useSuppressionList(search);
  const { add, revoke } = useSuppressionMutations();

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim() && !email.trim()) return;
    await add.mutateAsync({
      phone: phone.trim() || undefined,
      email: email.trim() || undefined,
      reason: reason.trim() || "Opt-out requested",
    });
    setPhone("");
    setEmail("");
  };

  const records = listQuery.data ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/leads"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Suppression List (Do-Not-Contact)</h1>
          <p className="text-xs text-muted-foreground">
            Centralized phone and email opt-outs enforced across imports and future campaigns.
          </p>
        </div>
      </div>

      <form
        onSubmit={(e) => void handleAdd(e)}
        className="grid gap-3 rounded-xl border border-border bg-card p-5 sm:grid-cols-4"
      >
        <input
          type="text"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Phone (+91...)"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={add.isPending || (!phone.trim() && !email.trim())}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-50"
        >
          <Ban className="h-4 w-4" />
          Suppress Contact
        </button>
      </form>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search suppressed phone, email, or reason..."
          className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm"
        />
      </div>

      <div className="divide-y divide-border rounded-xl border border-border bg-card">
        {records.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">No suppressed contacts.</p>
        ) : (
          records.map((rec) => (
            <div key={rec.id} className="flex flex-wrap items-center justify-between gap-3 p-4 text-xs">
              <div>
                <div className="font-medium text-sm">
                  {rec.phone || "—"} · {rec.email || "—"}
                </div>
                <div className="text-muted-foreground">
                  Reason: {rec.reason} · Channel: {rec.channel} · Source: {rec.source}
                </div>
              </div>
              <button
                type="button"
                onClick={() => void revoke.mutateAsync(rec.id)}
                className="rounded-lg border border-border px-3 py-1.5 font-medium hover:bg-muted"
              >
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
