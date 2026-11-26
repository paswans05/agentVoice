import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("sidebar config marks Leads as active in Phase 7", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");
  assert.match(content, /id:\s*"leads"[\s\S]*?status:\s*"active"/);
});

test("all Leads routes and hooks exist", () => {
  const webDir = path.resolve(import.meta.dirname, "..");
  for (const rel of [
    "app/leads/page.tsx",
    "app/leads/new/page.tsx",
    "app/leads/[id]/page.tsx",
    "app/leads/import/page.tsx",
    "app/leads/groups/page.tsx",
    "app/leads/suppression/page.tsx",
    "hooks/use-leads.ts",
  ]) {
    assert.ok(fs.existsSync(path.join(webDir, rel)), `Missing Leads file: ${rel}`);
  }
});

test("API client exposes Leads, Consent, Suppression, Groups, and CSV helpers", () => {
  const apiClientPath = path.resolve(import.meta.dirname, "../lib/api-client.ts");
  const content = fs.readFileSync(apiClientPath, "utf8");
  for (const fnName of [
    "fetchLeadStats",
    "fetchLeads",
    "createLead",
    "grantLeadConsent",
    "revokeLeadConsent",
    "fetchLeadEligibility",
    "fetchSuppressionList",
    "addSuppressionRecord",
    "previewCSVImport",
    "executeCSVImport",
    "exportLeadsCSV",
  ]) {
    assert.ok(content.includes(fnName), `Missing Phase 7 API helper: ${fnName}`);
  }
});
