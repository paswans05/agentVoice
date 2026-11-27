import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "../../..");

test("Phase 10 telephony navigation is active in config", () => {
  const cfg = fs.readFileSync(path.join(repoRoot, "packages/config/src/index.ts"), "utf8");
  assert.match(cfg, /id:\s*"telephony"[\s\S]*status:\s*"active"/);
});

test("Phase 10 shared types and API client expose telephony contracts", () => {
  const types = fs.readFileSync(path.join(repoRoot, "packages/shared-types/src/index.ts"), "utf8");
  for (const symbol of [
    "TelephonyProviderRecord",
    "SipTrunkRecord",
    "InboundRouteRecord",
    "OutboundRouteRecord",
    "GsmGatewayRecord",
    "TelephonySettings",
    "TelephonyOverview",
  ]) {
    assert.ok(types.includes(symbol), `Missing shared type: ${symbol}`);
  }

  const client = fs.readFileSync(path.join(repoRoot, "apps/web/lib/api-client.ts"), "utf8");
  for (const fn of [
    "fetchTelephonyOverview",
    "fetchTelephonyProviderRecords",
    "createTelephonyProvider",
    "testTelephonyProvider",
    "fetchSipTrunks",
    "fetchInboundRoutes",
    "fetchOutboundRoutes",
    "fetchGsmGateways",
    "fetchTelephonySettings",
    "updateTelephonySettings",
  ]) {
    assert.ok(client.includes(fn), `Missing API client function: ${fn}`);
  }
});

test("Phase 10 telephony dashboard and setup wizard pages exist", () => {
  const dashPath = path.join(repoRoot, "apps/web/app/telephony/page.tsx");
  const wizardPath = path.join(repoRoot, "apps/web/app/telephony/setup/page.tsx");
  assert.ok(fs.existsSync(dashPath), "Missing /telephony page");
  assert.ok(fs.existsSync(wizardPath), "Missing /telephony/setup page");

  const dash = fs.readFileSync(dashPath, "utf8");
  assert.match(dash, /Telephony Integration/);
  assert.match(dash, /Inbound Routes/);
  assert.match(dash, /GSM Gateways/);

  const wizard = fs.readFileSync(wizardPath, "utf8");
  assert.match(wizard, /Provider Configuration Wizard/);
});
