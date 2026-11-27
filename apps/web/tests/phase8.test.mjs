import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("sidebar config marks Campaigns, Call History, and Analytics as active in Phase 8", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");
  for (const id of ["campaigns", "call-history", "analytics"]) {
    assert.match(content, new RegExp(`id:\\s*"${id}"[\\s\\S]*?status:\\s*"active"`));
  }
});

test("Campaigns, Analytics, and Call History routes and hooks exist", () => {
  const webDir = path.resolve(import.meta.dirname, "..");
  for (const rel of [
    "app/campaigns/page.tsx",
    "app/campaigns/new/page.tsx",
    "app/campaigns/[id]/page.tsx",
    "app/analytics/page.tsx",
    "app/call-history/page.tsx",
    "hooks/use-campaigns.ts",
  ]) {
    assert.ok(fs.existsSync(path.join(webDir, rel)), `Missing Phase 8 file: ${rel}`);
  }
});

test("API client exposes Campaign, Execution, Analytics, and Telephony helpers", () => {
  const apiClientPath = path.resolve(import.meta.dirname, "../lib/api-client.ts");
  const content = fs.readFileSync(apiClientPath, "utf8");
  for (const fnName of [
    "fetchCampaigns",
    "createCampaign",
    "validateCampaign",
    "activateCampaign",
    "pauseCampaign",
    "stopCampaign",
    "cancelCampaign",
    "fetchCampaignAnalytics",
    "fetchCampaignOverview",
    "fetchAllCalls",
    "fetchTelephonyProviders",
  ]) {
    assert.ok(content.includes(fnName), `Missing Phase 8 API helper: ${fnName}`);
  }
});
