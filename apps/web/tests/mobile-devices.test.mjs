import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "../../..");

test("Mobile Devices shared types and API client methods exist", () => {
  const types = fs.readFileSync(path.join(repoRoot, "packages/shared-types/src/index.ts"), "utf8");
  for (const symbol of [
    "MobileDevice",
    "DeviceCapabilityProfile",
    "DeviceHealthSnapshot",
    "PairingCodeRecord",
    "DeviceEventRecord",
  ]) {
    assert.ok(types.includes(symbol), `Missing shared type: ${symbol}`);
  }

  const client = fs.readFileSync(path.join(repoRoot, "apps/web/lib/api-client.ts"), "utf8");
  for (const fn of [
    "fetchMobileDevices",
    "fetchMobileDevice",
    "createDevicePairingCode",
    "revokeMobileDevice",
    "fetchDeviceEvents",
    "sendDeviceCommand",
  ]) {
    assert.ok(client.includes(fn), `Missing API client function: ${fn}`);
  }
});

test("Mobile Devices dashboard, detail, wizard, and Flutter project exist", () => {
  for (const rel of [
    "apps/web/app/telephony/devices/page.tsx",
    "apps/web/app/telephony/devices/[id]/page.tsx",
    "apps/web/app/telephony/devices/wizard/page.tsx",
    "agentvoice-mobile/pubspec.yaml",
    "agentvoice-mobile/lib/main.dart",
    "agentvoice-mobile/android/app/src/main/kotlin/com/agentvoice/mobile/DeviceGatewayPlugin.kt",
    "agentvoice-mobile/ios/Runner/CallKitVoipBridge.swift",
  ]) {
    assert.ok(fs.existsSync(path.join(repoRoot, rel)), `Missing file: ${rel}`);
  }
});
