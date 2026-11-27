import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "../../..");

test("Testing Lab navigation item is active in config", () => {
  const cfg = fs.readFileSync(path.join(repoRoot, "packages/config/src/index.ts"), "utf8");
  assert.match(cfg, /id:\s*"testing-lab"[\s\S]*status:\s*"active"/);
});

test("Testing Lab shared types and API client helpers exist", () => {
  const types = fs.readFileSync(path.join(repoRoot, "packages/shared-types/src/index.ts"), "utf8");
  for (const symbol of [
    "CustomerPersona",
    "TestScenario",
    "ConversationEvaluation",
    "TestRun",
    "TestingOverviewStats",
  ]) {
    assert.ok(types.includes(symbol), `Missing shared type: ${symbol}`);
  }

  const client = fs.readFileSync(path.join(repoRoot, "apps/web/lib/api-client.ts"), "utf8");
  for (const fn of [
    "fetchTestingStatus",
    "fetchTestingPersonas",
    "fetchTestingScenarios",
    "runTestSimulation",
    "runKbSuiteTest",
    "runTelephonySuiteTest",
    "runPerformanceSuiteTest",
    "runTestingAssistant",
  ]) {
    assert.ok(client.includes(fn), `Missing API client function: ${fn}`);
  }
});

test("Testing Lab page exists with simulator, assistant, and live test sections", () => {
  const pagePath = path.join(repoRoot, "apps/web/app/testing-lab/page.tsx");
  assert.ok(fs.existsSync(pagePath), "Missing /testing-lab page");
  const content = fs.readFileSync(pagePath, "utf8");
  assert.match(content, /AI Client Simulator/);
  assert.match(content, /AI Testing Assistant/);
  assert.match(content, /Live Test/);
});
