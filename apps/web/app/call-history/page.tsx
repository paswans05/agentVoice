"use client";

import { useAllCalls } from "@/hooks/use-campaigns";

export default function CallHistoryPage() {
  const callsQuery = useAllCalls();
  const calls = callsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Call History</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          All campaign call records with clear separation between real calls and dry-run
          simulations.
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="p-3">Call ID</th>
              <th className="p-3">Campaign</th>
              <th className="p-3">Lead</th>
              <th className="p-3">Mode</th>
              <th className="p-3">Outcome</th>
              <th className="p-3">Started</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-xs">
            {callsQuery.isLoading ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  Loading call history...
                </td>
              </tr>
            ) : calls.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  No campaign calls recorded yet.
                </td>
              </tr>
            ) : (
              calls.map((c) => (
                <tr key={c.call_id}>
                  <td className="p-3 font-mono">{c.call_id}</td>
                  <td className="p-3 font-mono">{c.campaign_id}</td>
                  <td className="p-3 font-mono">{c.lead_id}</td>
                  <td className="p-3">
                    <span className="rounded bg-muted px-2 py-0.5 text-[10px] font-medium">
                      {c.is_dry_run ? "DRY-RUN" : "REAL"}
                    </span>
                  </td>
                  <td className="p-3 font-medium">{c.outcome}</td>
                  <td className="p-3 text-muted-foreground">
                    {new Date(c.started_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
