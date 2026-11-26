import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("sidebar config marks Model Manager as active in Phase 3", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");
  assert.match(content, /id:\s*"models"[\s\S]*?status:\s*"active"/);
});

test("Model Manager and Playground routes exist", () => {
  const webAppDir = path.resolve(import.meta.dirname, "../app");
  assert.ok(fs.existsSync(path.join(webAppDir, "models/page.tsx")));
  assert.ok(fs.existsSync(path.join(webAppDir, "agents/[id]/playground/page.tsx")));
});

test("API client exposes model manager and streaming conversation helpers", () => {
  const apiClientPath = path.resolve(import.meta.dirname, "../lib/api-client.ts");
  const content = fs.readFileSync(apiClientPath, "utf8");
  for (const fnName of [
    "fetchLLMHealth",
    "fetchModelsOverview",
    "refreshModels",
    "setDefaultModel",
    "pullModel",
    "fetchPullStatus",
    "cancelModelPull",
    "deleteModel",
    "fetchAgentConversations",
    "createConversation",
    "fetchConversation",
    "deleteConversation",
    "streamConversationMessage",
  ]) {
    assert.ok(content.includes(fnName), `Missing Phase 3 API client helper: ${fnName}`);
  }
});
