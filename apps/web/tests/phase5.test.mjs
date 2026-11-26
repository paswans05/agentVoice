import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("sidebar config marks Knowledge Base as active in Phase 5", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");
  assert.match(content, /id:\s*"knowledge-base"[\s\S]*?status:\s*"active"/);
});

test("Knowledge Base routes and hooks exist", () => {
  const webDir = path.resolve(import.meta.dirname, "..");
  assert.ok(fs.existsSync(path.join(webDir, "app/knowledge-base/page.tsx")));
  assert.ok(fs.existsSync(path.join(webDir, "app/knowledge-base/[id]/page.tsx")));
  assert.ok(fs.existsSync(path.join(webDir, "hooks/use-knowledge.ts")));
});

test("API client exposes knowledge base, document, and retrieval helpers", () => {
  const apiClientPath = path.resolve(import.meta.dirname, "../lib/api-client.ts");
  const content = fs.readFileSync(apiClientPath, "utf8");
  for (const fnName of [
    "fetchKnowledgeBases",
    "createKnowledgeBase",
    "fetchKnowledgeBase",
    "deleteKnowledgeBase",
    "enableKnowledgeBase",
    "disableKnowledgeBase",
    "fetchKBDocuments",
    "uploadKBDocuments",
    "deleteKBDocument",
    "reprocessKBDocument",
    "assignKBToAgent",
    "unassignKBFromAgent",
    "searchKnowledgeBase",
    "fetchRAGSettings",
    "updateRAGSettings",
  ]) {
    assert.ok(content.includes(fnName), `Missing Phase 5 API helper: ${fnName}`);
  }
});
