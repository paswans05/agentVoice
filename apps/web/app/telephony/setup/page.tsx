"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type {
  SipAuthMode,
  TelephonyProviderRecord,
  TelephonyProviderType,
  TransportProtocol,
} from "@agentvoice/shared-types";
import { ArrowLeft, CheckCircle2, ShieldCheck } from "lucide-react";

import {
  createGsmGateway,
  createInboundRoute,
  createOutboundRoute,
  createTelephonyProvider,
  testTelephonyProvider,
} from "@/lib/api-client";

export default function TelephonySetupWizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [providerType, setProviderType] = useState<TelephonyProviderType>("asterisk");
  const [name, setName] = useState("Local Asterisk PBX");
  const [host, setHost] = useState("127.0.0.1");
  const [port, setPort] = useState(8088);
  const [useTls, setUseTls] = useState(false);
  const [transport, setTransport] = useState<TransportProtocol>("UDP");
  const [authMode, setAuthMode] = useState<SipAuthMode>("userpass_registration");
  const [sipDomain, setSipDomain] = useState("");
  const [ariUsername, setAriUsername] = useState("agentvoice");
  const [ariPassword, setAriPassword] = useState("");
  const [callerId, setCallerId] = useState("");
  const [allowedDestinations, setAllowedDestinations] = useState("+91*");
  const [inboundNumber, setInboundNumber] = useState("");
  const [inboundAgentId, setInboundAgentId] = useState("");

  const [createdProvider, setCreatedProvider] = useState<TelephonyProviderRecord | null>(null);
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleCreateAndTest = async () => {
    setBusy(true);
    setErrorMsg(null);
    try {
      if (providerType === "gsm_gateway") {
        await createGsmGateway({
          name,
          host,
          port,
          mode: "sip_trunk",
        });
        setStep(6);
        return;
      }
      const created =
        createdProvider ??
        (await createTelephonyProvider({
          name,
          provider_type: providerType,
          host,
          port,
          use_tls: useTls,
          transport,
          auth_mode: authMode,
          sip_domain: sipDomain || undefined,
          ari_username: ariUsername || undefined,
          ari_password: ariPassword || undefined,
          caller_id: callerId || undefined,
          allowed_destinations: allowedDestinations
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }));
      setCreatedProvider(created);
      const res = await testTelephonyProvider(created.id);
      setTestResult(res);
      setStep(4);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to save/test provider.");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveRouting = async () => {
    if (!createdProvider) {
      setStep(6);
      return;
    }
    setBusy(true);
    setErrorMsg(null);
    try {
      if (inboundNumber && inboundAgentId) {
        await createInboundRoute({
          name: `${name} Inbound`,
          phone_number: inboundNumber,
          agent_id: inboundAgentId,
        });
      }
      if (callerId) {
        await createOutboundRoute({
          name: `${name} Outbound`,
          provider_id: createdProvider.id,
          caller_id: callerId,
          destination_pattern: allowedDestinations.split(",")[0]?.trim() || "+91*",
        });
      }
      setStep(6);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to save routes.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/telephony"
          className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Telephony
        </Link>
        <div>
          <h1 className="text-xl font-semibold">Provider Configuration Wizard</h1>
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
            <h2 className="font-medium">Step 1 — Select Telephony Provider</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {(
                [
                  ["asterisk", "Asterisk PBX (ARI + PJSIP)", "Self-hosted Asterisk over ARI"],
                  ["sip_trunk", "SIP Trunk via Asterisk", "Authorized external SIP carrier"],
                  ["gsm_gateway", "Authorized GSM Gateway", "SIP-compatible or vendor API hardware"],
                  ["custom", "Custom Provider Adapter", "Extensible TelephonyProvider adapter"],
                ] as const
              ).map(([val, title, desc]) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setProviderType(val)}
                  className={`rounded-xl border p-4 text-left transition-colors ${
                    providerType === val
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-muted/40"
                  }`}
                >
                  <div className="font-medium text-sm">{title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{desc}</div>
                </button>
              ))}
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="font-medium">Step 2 — Configure Connection & Credentials</h2>
            <div className="grid gap-3 sm:grid-cols-2 text-xs">
              <label className="space-y-1">
                <span>Provider Name</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>Host / IP</span>
                <input
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>ARI / SIP Port</span>
                <input
                  type="number"
                  value={port}
                  onChange={(e) => setPort(Number(e.target.value))}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>Transport</span>
                <select
                  value={transport}
                  onChange={(e) => setTransport(e.target.value as TransportProtocol)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                >
                  <option value="UDP">UDP</option>
                  <option value="TCP">TCP</option>
                  <option value="TLS">TLS</option>
                </select>
              </label>
              <label className="space-y-1">
                <span>SIP Auth Mode</span>
                <select
                  value={authMode}
                  onChange={(e) => setAuthMode(e.target.value as SipAuthMode)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                >
                  <option value="userpass_registration">Username + Password + Registration</option>
                  <option value="ip_whitelist">IP Whitelisting (e.g. Exotel vSIP)</option>
                  <option value="digest_challenge">SIP Digest Auth (No Registration)</option>
                </select>
              </label>
              <label className="space-y-1">
                <span>SIP Domain (optional)</span>
                <input
                  value={sipDomain}
                  onChange={(e) => setSipDomain(e.target.value)}
                  placeholder="pstn.in2.exotel.com"
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>ARI Username</span>
                <input
                  value={ariUsername}
                  onChange={(e) => setAriUsername(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>ARI Password (stored encrypted)</span>
                <input
                  type="password"
                  value={ariPassword}
                  onChange={(e) => setAriPassword(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
            </div>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={useTls}
                onChange={(e) => setUseTls(e.target.checked)}
              />
              Use HTTPS / TLS for Asterisk ARI
            </label>
            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-lg border border-border px-4 py-2 text-xs"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Next: Caller Identity & Test
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="font-medium">Step 3 & 4 — Caller Identity & Connection Test</h2>
            <div className="grid gap-3 sm:grid-cols-2 text-xs">
              <label className="space-y-1">
                <span>Authorized Caller ID</span>
                <input
                  value={callerId}
                  onChange={(e) => setCallerId(e.target.value)}
                  placeholder="+911140001234"
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>Allowed Destination Patterns</span>
                <input
                  value={allowedDestinations}
                  onChange={(e) => setAllowedDestinations(e.target.value)}
                  placeholder="+91*"
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
            </div>
            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="rounded-lg border border-border px-4 py-2 text-xs"
              >
                Back
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleCreateAndTest()}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground disabled:opacity-50"
              >
                {busy ? "Testing..." : "Save & Test Connection"}
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h2 className="font-medium">Step 4 — Connection Verification Result</h2>
            <div className="rounded-lg border border-border bg-muted/40 p-4 text-xs space-y-1">
              <div>
                <strong>Status:</strong> {String(testResult?.status ?? "DISCONNECTED")}
              </div>
              <div>
                <strong>Connected:</strong> {String(Boolean(testResult?.connected))}
              </div>
              <div>
                <strong>Message:</strong> {String(testResult?.message ?? "—")}
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(5)}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Next: Configure Routing
              </button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4">
            <h2 className="font-medium">Step 5 — Inbound & Outbound Routing (Optional)</h2>
            <div className="grid gap-3 sm:grid-cols-2 text-xs">
              <label className="space-y-1">
                <span>Inbound DID / Phone Number</span>
                <input
                  value={inboundNumber}
                  onChange={(e) => setInboundNumber(e.target.value)}
                  placeholder="+911140001234"
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
              <label className="space-y-1">
                <span>Assigned Active Agent ID</span>
                <input
                  value={inboundAgentId}
                  onChange={(e) => setInboundAgentId(e.target.value)}
                  placeholder="agent_..."
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
                />
              </label>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleSaveRouting()}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
              >
                Finish Verification
              </button>
            </div>
          </div>
        )}

        {step === 6 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 font-medium text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
              <span>Step 6 — Configuration Saved</span>
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              Real outbound calling remains blocked unless the provider connection check succeeds
              and all consent/suppression checks pass.
            </p>
            <button
              type="button"
              onClick={() => router.push("/telephony")}
              className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
            >
              Open Telephony Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
