import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";

test("config package defines all 11 sidebar navigation items", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");

  const expectedIds = [
    "overview",
    "agents",
    "models",
    "playground",
    "leads",
    "campaigns",
    "live-calls",
    "call-history",
    "analytics",
    "telephony",
    "settings",
  ];

  for (const id of expectedIds) {
    assert.ok(content.includes(`id: "${id}"`), `Missing nav item: ${id}`);
  }
  assert.ok(!content.toLowerCase().includes("agentpulse"), "Old product name must not appear");
});
