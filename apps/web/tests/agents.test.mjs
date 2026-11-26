import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("sidebar config marks AI Agents as active in Phase 2", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");
  assert.match(content, /id:\s*"agents"[\s\S]*?status:\s*"active"/);
});

test("all required AI Agents routes exist", () => {
  const webAppDir = path.resolve(import.meta.dirname, "../app");
  const requiredRoutes = [
    "agents/page.tsx",
    "agents/new/page.tsx",
    "agents/[id]/page.tsx",
    "agents/[id]/edit/page.tsx",
  ];
  for (const rel of requiredRoutes) {
    assert.ok(fs.existsSync(path.join(webAppDir, rel)), `Missing route: ${rel}`);
  }
});

test("API client exposes all agent CRUD and lifecycle methods", () => {
  const apiClientPath = path.resolve(import.meta.dirname, "../lib/api-client.ts");
  const content = fs.readFileSync(apiClientPath, "utf8");
  for (const fnName of [
    "fetchAgents",
    "fetchAgent",
    "fetchAgentTemplates",
    "createAgent",
    "updateAgent",
    "deleteAgent",
    "duplicateAgent",
    "activateAgent",
    "deactivateAgent",
  ]) {
    assert.ok(content.includes(`export function ${fnName}`), `Missing API helper: ${fnName}`);
  }
});
