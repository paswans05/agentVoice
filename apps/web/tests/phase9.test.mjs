import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "../../..");

test("Phase 9 live calls navigation is active in config", () => {
  const cfg = fs.readFileSync(path.join(repoRoot, "packages/config/src/index.ts"), "utf8");
  assert.match(cfg, /id:\s*"live-calls"[\s\S]*status:\s*"active"/);
});

test("Phase 9 shared types and API client expose live calls contracts", () => {
  const types = fs.readFileSync(path.join(repoRoot, "packages/shared-types/src/index.ts"), "utf8");
  for (const symbol of [
    "CallSession",
    "NormalizedCallEvent",
    "TranscriptSegment",
    "CallMetricsSnapshot",
    "LiveCallsStats",
    "CallMonitoringSettings",
    "LiveCallsWsFrame",
  ]) {
    assert.ok(types.includes(symbol), `Missing shared type: ${symbol}`);
  }

  const client = fs.readFileSync(path.join(repoRoot, "apps/web/lib/api-client.ts"), "utf8");
  for (const fn of [
    "fetchLiveCalls",
    "fetchLiveCallsStats",
    "fetchLiveCallDetail",
    "fetchCallTranscript",
    "terminateLiveCall",
    "holdLiveCall",
    "transferLiveCall",
    "flagLiveCall",
    "getLiveCallsWebSocketUrl",
  ]) {
    assert.ok(client.includes(fn), `Missing API client function: ${fn}`);
  }
});

test("Phase 9 live calls pages and WebSocket hook exist", () => {
  const hookPath = path.join(repoRoot, "apps/web/hooks/use-live-calls.ts");
  const listPagePath = path.join(repoRoot, "apps/web/app/live-calls/page.tsx");
  const detailPagePath = path.join(repoRoot, "apps/web/app/live-calls/[id]/page.tsx");

  assert.ok(fs.existsSync(hookPath), "Missing use-live-calls.ts");
  assert.ok(fs.existsSync(listPagePath), "Missing /live-calls page");
  assert.ok(fs.existsSync(detailPagePath), "Missing /live-calls/[id] page");

  const hook = fs.readFileSync(hookPath, "utf8");
  assert.match(hook, /SUBSCRIBE/);
  assert.match(hook, /PING/);

  const detail = fs.readFileSync(detailPagePath, "utf8");
  assert.match(detail, /Terminate Call/);
  assert.match(detail, /Live Transcript/);
});
