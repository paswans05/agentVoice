"use client";

import type { CSVImportPreviewResponse, CSVImportResult } from "@agentvoice/shared-types";
import { ArrowLeft, CheckCircle2, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { executeCSVImport, previewCSVImport } from "@/lib/api-client";

const TARGET_FIELDS = [
  { value: "IGNORE", label: "— Ignore Column —" },
  { value: "full_name", label: "Full Name" },
  { value: "first_name", label: "First Name" },
  { value: "last_name", label: "Last Name" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "company", label: "Company" },
  { value: "job_title", label: "Job Title" },
  { value: "city", label: "City" },
  { value: "state", label: "State" },
  { value: "country", label: "Country" },
  { value: "source", label: "Source" },
  { value: "notes", label: "Notes" },
];

export default function ImportLeadsPage() {
  const [preview, setPreview] = useState<CSVImportPreviewResponse | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [duplicateStrategy, setDuplicateStrategy] = useState<"SKIP" | "UPDATE_EXISTING" | "IMPORT_AS_NEW">("SKIP");
  const [matchStrategy, setMatchStrategy] = useState<"EMAIL" | "PHONE" | "EMAIL_OR_PHONE">("EMAIL_OR_PHONE");
  const [result, setResult] = useState<CSVImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await previewCSVImport(file);
      setPreview(data);
      const initial: Record<string, string> = {};
      for (const h of data.headers) {
        initial[h] = data.suggested_mapping[h] ?? "IGNORE";
      }
      setMapping(initial);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to parse CSV.");
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!preview) return;
    setError(null);
    setLoading(true);
    try {
      const res = await executeCSVImport({
        job_id: preview.job_id,
        column_mapping: mapping,
        duplicate_strategy: duplicateStrategy,
        match_strategy: matchStrategy,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setLoading(false);
    }
  };

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
          <h1 className="text-2xl font-semibold tracking-tight">Import Leads from CSV</h1>
          <p className="text-xs text-muted-foreground">
            Imported leads default to UNKNOWN consent and respect existing suppression rules.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          {error}
        </div>
      )}

      {!preview && (
        <div className="rounded-xl border-2 border-dashed border-border bg-card p-10 text-center">
          <Upload className="mx-auto h-8 w-8 text-primary" />
          <p className="mt-2 text-sm font-medium">
            {loading ? "Parsing CSV..." : "Select a UTF-8 CSV file to preview and map columns"}
          </p>
          <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90">
            <span>Choose CSV File</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => void handleFile(e.target.files?.[0])}
              className="hidden"
            />
          </label>
        </div>
      )}

      {preview && !result && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <div className="flex justify-between text-sm">
              <span className="font-semibold">
                {preview.filename} ({preview.total_rows} rows)
              </span>
              <button
                type="button"
                onClick={() => setPreview(null)}
                className="text-xs text-primary hover:underline"
              >
                Choose another file
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {preview.headers.map((header) => (
                <div key={header} className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-mono truncate">{header}</span>
                  <select
                    value={mapping[header] ?? "IGNORE"}
                    onChange={(e) => setMapping((m) => ({ ...m, [header]: e.target.value }))}
                    className="rounded-lg border border-border bg-background px-2.5 py-1.5"
                  >
                    {TARGET_FIELDS.map((f) => (
                      <option key={f.value} value={f.value}>
                        {f.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="grid gap-4 border-t border-border pt-4 sm:grid-cols-2 text-xs">
              <div>
                <label className="block font-medium">Duplicate Handling</label>
                <select
                  value={duplicateStrategy}
                  onChange={(e) => setDuplicateStrategy(e.target.value as typeof duplicateStrategy)}
                  className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
                >
                  <option value="SKIP">SKIP duplicates (Recommended)</option>
                  <option value="UPDATE_EXISTING">UPDATE_EXISTING</option>
                  <option value="IMPORT_AS_NEW">IMPORT_AS_NEW</option>
                </select>
              </div>
              <div>
                <label className="block font-medium">Duplicate Match Strategy</label>
                <select
                  value={matchStrategy}
                  onChange={(e) => setMatchStrategy(e.target.value as typeof matchStrategy)}
                  className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2"
                >
                  <option value="EMAIL_OR_PHONE">Email or Normalized Phone</option>
                  <option value="EMAIL">Email only</option>
                  <option value="PHONE">Normalized Phone only</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                disabled={loading}
                onClick={() => void handleImport()}
                className="rounded-lg bg-primary px-5 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {loading ? "Importing..." : `Import ${preview.total_rows} Rows`}
              </button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="rounded-xl border border-border bg-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold">
            <CheckCircle2 className="h-5 w-5" />
            <span>CSV Import Completed</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-5 text-xs">
            <div className="rounded-lg border border-border p-3">
              <div className="text-muted-foreground">Imported</div>
              <div className="text-lg font-semibold">{result.imported_count}</div>
            </div>
            <div className="rounded-lg border border-border p-3">
              <div className="text-muted-foreground">Updated</div>
              <div className="text-lg font-semibold">{result.updated_count}</div>
            </div>
            <div className="rounded-lg border border-border p-3">
              <div className="text-muted-foreground">Skipped</div>
              <div className="text-lg font-semibold">{result.skipped_count}</div>
            </div>
            <div className="rounded-lg border border-border p-3">
              <div className="text-muted-foreground">Duplicates</div>
              <div className="text-lg font-semibold">{result.duplicate_count}</div>
            </div>
            <div className="rounded-lg border border-border p-3">
              <div className="text-muted-foreground">Invalid</div>
              <div className="text-lg font-semibold">{result.invalid_count}</div>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs space-y-1">
              <div className="font-semibold">Row Errors</div>
              {result.errors.slice(0, 10).map((e, i) => (
                <div key={i}>
                  Row {e.row_number}: {e.message}
                </div>
              ))}
            </div>
          )}
          <Link
            href="/leads"
            className="inline-flex rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
          >
            Back to Leads
          </Link>
        </div>
      )}
    </div>
  );
}
