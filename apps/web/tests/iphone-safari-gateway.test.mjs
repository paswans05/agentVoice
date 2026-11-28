import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "../../..");

test("iPhone 13 Safari Web Gateway PWA, HTTPS script, and Caddyfile exist", () => {
  for (const rel of [
    "scripts/setup-iphone-https.ps1",
    "docker/caddy/Caddyfile.iphone",
    "agentvoice-phone-web/package.json",
    "agentvoice-phone-web/public/manifest.json",
    "agentvoice-phone-web/app/page.tsx",
    "agentvoice-phone-web/app/pair/page.tsx",
    "agentvoice-phone-web/app/gateway/page.tsx",
    "agentvoice-phone-web/app/voice-test/page.tsx",
    "agentvoice-phone-web/app/settings/page.tsx",
    "agentvoice-phone-web/components/PairingScreen.tsx",
    "agentvoice-phone-web/components/MicrophoneTest.tsx",
    "agentvoice-phone-web/components/VoiceSession.tsx",
    "agentvoice-phone-web/services/api.ts",
    "agentvoice-phone-web/services/websocket.ts",
    "agentvoice-phone-web/services/device.ts",
    "agentvoice-phone-web/services/webrtc.ts",
    "docs/iphone-safari-gateway.md",
  ]) {
    assert.ok(fs.existsSync(path.join(repoRoot, rel)), `Missing file: ${rel}`);
  }

  const pairing = fs.readFileSync(
    path.join(repoRoot, "agentvoice-phone-web/components/PairingScreen.tsx"),
    "utf8",
  );
  assert.match(pairing, /No native iOS application is required/);

  const deviceSvc = fs.readFileSync(
    path.join(repoRoot, "agentvoice-phone-web/services/device.ts"),
    "utf8",
  );
  assert.ok(!deviceSvc.includes("window.localStorage"), "Secrets must never use localStorage");
});
