"use client";

import type { ConsentStatus, LeadPriority, LeadStatus } from "@agentvoice/shared-types";
import {
  Ban,
  Download,
  FolderKanban,
  Plus,
  Search,
  Trash2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  useBulkLeadActions,
  useDeleteLead,
  useLeadGroups,
  useLeads,
  useLeadStats,
} from "@/hooks/use-leads";
import { exportLeadsCSV } from "@/lib/api-client";

const LEAD_STATUSES: LeadStatus[] = [
  "NEW",
  "CONTACTED",
  "QUALIFIED",
  "UNQUALIFIED",
  "INTERESTED",
  "NOT_INTERESTED",
  "FOLLOW_UP",
  "CONVERTED",
  "LOST",
  "DO_NOT_CONTACT",
];

export default function LeadsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");
  const [priorityFilter, setPriorityFilter] = useState<LeadPriority | "">("");
  const [consentFilter, setConsentFilter] = useState<ConsentStatus | "">("");
  const [groupFilter, setGroupFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const statsQuery = useLeadStats();
  const groupsQuery = useLeadGroups();
  const leadsQuery = useLeads({
    search: debouncedSearch,
    status: statusFilter,
    priority: priorityFilter,
    consent_status: consentFilter,
    group_id: groupFilter || undefined,
    page,
    page_size: 20,
  });

  const deleteMutation = useDeleteLead();
  const { bulkDelete } = useBulkLeadActions();

  const stats = statsQuery.data;
  const leadsData = leadsQuery.data;
  const items = leadsData?.items ?? [];

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleExport = async () => {
    const blob = await exportLeadsCSV({
      lead_ids: selectedIds.length > 0 ? selectedIds : undefined,
      status: statusFilter || undefined,
      include_consent: true,
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "agentvoice-leads.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    await bulkDelete.mutateAsync(selectedIds);
    setFeedback(`Deleted ${selectedIds.length} lead(s).`);
    setSelectedIds([]);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage contacts, CSV import/export, consent records, and do-not-contact suppression.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/leads/groups"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <FolderKanban className="h-3.5 w-3.5" />
            Groups
          </Link>
          <Link
            href="/leads/suppression"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <Ban className="h-3.5 w-3.5" />
            Suppression List
          </Link>
          <Link
            href="/leads/import"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <Upload className="h-3.5 w-3.5" />
            Import CSV
          </Link>
          <button
            type="button"
            onClick={() => void handleExport()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </button>
          <Link
            href="/leads/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            Create Lead
          </Link>
        </div>
      </div>

      {/* Dashboard Stats */}
      <div className="grid gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {[
          { label: "Total", value: stats?.total_leads ?? 0 },
          { label: "New", value: stats?.new_leads ?? 0 },
          { label: "Qualified", value: stats?.qualified_leads ?? 0 },
          { label: "Interested", value: stats?.interested_leads ?? 0 },
          { label: "Follow Up", value: stats?.follow_up_leads ?? 0 },
          { label: "Converted", value: stats?.converted_leads ?? 0 },
          { label: "Suppressed", value: stats?.suppressed_contacts ?? 0 },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-border bg-card p-3.5">
            <div className="text-[11px] text-muted-foreground">{s.label}</div>
            <div className="mt-1 text-xl font-semibold">{s.value}</div>
          </div>
        ))}
      </div>

      {feedback && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-700 dark:text-emerald-300">
          {feedback}
        </div>
      )}

      {/* Search & Filters */}
      <div className="grid gap-2.5 rounded-xl border border-border bg-card p-4 sm:grid-cols-5">
        <div className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search name, email, phone, company..."
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as LeadStatus | "");
            setPage(1);
          }}
          className="rounded-lg border border-border bg-background px-2.5 py-2 text-xs"
        >
          <option value="">All Statuses</option>
          {LEAD_STATUSES.map((st) => (
            <option key={st} value={st}>
              {st}
            </option>
          ))}
        </select>

        <select
          value={consentFilter}
          onChange={(e) => {
            setConsentFilter(e.target.value as ConsentStatus | "");
            setPage(1);
          }}
          className="rounded-lg border border-border bg-background px-2.5 py-2 text-xs"
        >
          <option value="">All Consent</option>
          {(["UNKNOWN", "GRANTED", "DENIED", "REVOKED"] as ConsentStatus[]).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          value={groupFilter}
          onChange={(e) => {
            setGroupFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-background px-2.5 py-2 text-xs"
        >
          <option value="">All Groups</option>
          {(groupsQuery.data ?? []).map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
      </div>

      {selectedIds.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-2.5 text-xs">
          <span>{selectedIds.length} lead(s) selected</span>
          <button
            type="button"
            onClick={() => void handleBulkDelete()}
            className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-3 py-1.5 font-medium text-white hover:bg-rose-700"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete Selected
          </button>
        </div>
      )}

      {/* Leads Table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="p-3 w-8">
                <input
                  type="checkbox"
                  checked={items.length > 0 && selectedIds.length === items.length}
                  onChange={(e) =>
                    setSelectedIds(e.target.checked ? items.map((l) => l.id) : [])
                  }
                />
              </th>
              <th className="p-3">Name</th>
              <th className="p-3">Contact</th>
              <th className="p-3">Company</th>
              <th className="p-3">Status</th>
              <th className="p-3">Consent</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {leadsQuery.isLoading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-xs text-muted-foreground">
                  Loading leads...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-xs text-muted-foreground">
                  No leads found. Create a lead or import a CSV file.
                </td>
              </tr>
            ) : (
              items.map((lead) => (
                <tr key={lead.id} className="hover:bg-muted/20">
                  <td className="p-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(lead.id)}
                      onChange={() => toggleSelect(lead.id)}
                    />
                  </td>
                  <td className="p-3">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="font-medium hover:text-primary"
                    >
                      {lead.full_name || "Unnamed Lead"}
                    </Link>
                    {lead.suppressed && (
                      <span className="ml-2 rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-medium text-rose-600 dark:text-rose-400">
                        SUPPRESSED
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">
                    <div>{lead.phone || "—"}</div>
                    <div>{lead.email || "—"}</div>
                  </td>
                  <td className="p-3 text-xs">{lead.company || "—"}</td>
                  <td className="p-3 text-xs">
                    <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-[11px]">
                      {lead.status}
                    </span>
                  </td>
                  <td className="p-3 text-xs">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        lead.consent_status === "GRANTED"
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                          : lead.consent_status === "REVOKED" || lead.consent_status === "DENIED"
                            ? "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {lead.consent_status}
                    </span>
                  </td>
                  <td className="p-3 text-right text-xs">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="mr-3 text-primary hover:underline"
                    >
                      View
                    </Link>
                    <button
                      type="button"
                      onClick={() => void deleteMutation.mutateAsync(lead.id)}
                      className="text-rose-600 hover:underline dark:text-rose-400"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {leadsData && leadsData.total_pages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Page {leadsData.page} of {leadsData.total_pages} ({leadsData.total} total)
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded border border-border px-3 py-1 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= leadsData.total_pages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border border-border px-3 py-1 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
