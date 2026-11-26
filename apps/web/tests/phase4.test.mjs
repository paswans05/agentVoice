import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("sidebar config marks Voice Playground as active in Phase 4", () => {
  const configPath = path.resolve(import.meta.dirname, "../../../packages/config/src/index.ts");
  const content = fs.readFileSync(configPath, "utf8");
  assert.match(content, /id:\s*"playground"[\s\S]*?status:\s*"active"/);
});

test("Voice Playground directory and voice session hook exist", () => {
  const webDir = path.resolve(import.meta.dirname, "..");
  assert.ok(fs.existsSync(path.join(webDir, "app/playground/page.tsx")));
  assert.ok(fs.existsSync(path.join(webDir, "hooks/use-voice-session.ts")));
  assert.ok(fs.existsSync(path.join(webDir, "hooks/use-speech.ts")));
});

test("API client exposes speech and voice session helpers", () => {
  const apiClientPath = path.resolve(import.meta.dirname, "../lib/api-client.ts");
  const content = fs.readFileSync(apiClientPath, "utf8");
  for (const fnName of [
    "fetchSpeechHealth",
    "fetchSTTModels",
    "fetchTTSVoices",
    "fetchAudioSettings",
    "updateAudioSettings",
    "createVoiceSession",
    "deleteVoiceSession",
    "getVoiceWebSocketUrl",
  ]) {
    assert.ok(content.includes(fnName), `Missing Phase 4 API helper: ${fnName}`);
  }
});
