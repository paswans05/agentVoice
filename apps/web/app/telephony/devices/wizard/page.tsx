"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { DevicePlatform, PairingCodeRecord } from "@agentvoice/shared-types";
import { ArrowLeft, CheckCircle2, ShieldAlert } from "lucide-react";

import { createDevicePairingCode } from "@/lib/api-client";

export default function MobileDeviceWizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState<DevicePlatform>("android");
  const [pairing, setPairing] = useState<PairingCodeRecord | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleGenerateCode = async () => {
    try {
      const res = await createDevicePairingCode({ platform, ttl_seconds: 300 });
      setPairing(res);
      setErrorMsg(null);
      setStep(2);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to generate pairing code.");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/telephony/devices"
          className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Devices
        </Link>
        <div>
          <h1 className="text-xl font-semibold">Mobile Device Configuration Wizard</h1>
          <p className="text-xs text-muted-foreground">Step {step} of 6</p>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card p-6 space-y-5">
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="font-medium">Step 1 — Select Platform</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setPlatform("android")}
                className={`rounded-xl border p-4 text-left ${
                  platform === "android" ? "border-primary bg-primary/5" : "border-border"
                }`}
              >
                <div className="font-medium text-sm">Android Device Gateway</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Kotlin + Telecom/TelephonyManager + WorkManager + AgentVoice VoIP
                </div>
              </button>
              <button
                type="button"
                onClick={() => setPlatform("ios")}
                className={`rounded-xl border p-4 text-left ${
                  platform === "ios" ? "border-primary bg-primary/5" : "border-border"
                }`}
              >
                <div className="font-medium text-sm">iPhone Companion</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Swift + Keychain + CallKit VoIP (app-level VoIP only)
                </div>
              </button>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => void handleGenerateCode()}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Generate Single-Use Pairing Code
              </button>
            </div>
          </div>
        )}

        {step === 2 && pairing && (
          <div className="space-y-4">
            <h2 className="font-medium">Step 2 — Pair Device</h2>
            <div className="rounded-xl border border-border bg-muted/40 p-5 text-center space-y-2">
              <div className="text-xs text-muted-foreground">Single-Use Pairing Code</div>
              <div className="text-3xl font-mono font-bold tracking-widest">{pairing.code}</div>
              <div className="text-xs text-muted-foreground">
                Expires at: {new Date(pairing.expires_at).toLocaleTimeString()}
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Next: Permissions & Capabilities
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 text-xs">
            <h2 className="font-medium text-sm">Step 3 — Permissions & Capabilities</h2>
            <p className="text-muted-foreground">
              {platform === "android"
                ? "Android requests READ_PHONE_STATE, CALL_PHONE, and RECORD_AUDIO (for VoIP) at runtime. Privileged cellular audio capture is never requested."
                : "iOS requests Microphone permission for AgentVoice VoIP calls via CallKit and stores tokens in iOS Keychain."}
            </p>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(4)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Next: Connectivity
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4 text-xs">
            <h2 className="font-medium text-sm">Step 4 — Connectivity & Heartbeat</h2>
            <p className="text-muted-foreground">
              Device authenticates with a per-device revocable token over TLS and sends heartbeats
              to <code>/api/v1/devices/{"{device_id}"}/heartbeat</code> and{" "}
              <code>WS /api/v1/devices/ws</code>.
            </p>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(5)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Next: Calling Capabilities
              </button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4 text-xs">
            <h2 className="font-medium text-sm">Step 5 — Calling Capabilities</h2>
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 flex items-start gap-2 text-amber-800 dark:text-amber-200">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                Cellular Audio Bridge: <strong>CELLULAR_AUDIO_BRIDGE_UNAVAILABLE</strong>. Full AI
                voice conversations require an authorized Asterisk/SIP TelephonyProvider or
                AgentVoice VoIP session.
              </span>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(6)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Next: Review & Activate
              </button>
            </div>
          </div>
        )}

        {step === 6 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 font-medium text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
              <span>Step 6 — Ready for Device Pairing</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Once paired from the mobile app, your device will appear in Telephony &gt; Mobile
              Devices with live health and capability status.
            </p>
            <button
              type="button"
              onClick={() => router.push("/telephony/devices")}
              className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
            >
              View Mobile Devices
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
