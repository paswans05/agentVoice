"use client";

import type { InternalCallMode } from "@agentvoice/shared-types";
import {
  Activity,
  Bot,
  CheckCircle2,
  Mic,
  MicOff,
  Pause,
  Phone,
  PhoneCall,
  PhoneIncoming,
  PhoneOff,
  Play,
  Radio,
  RefreshCw,
  ShieldAlert,
  User,
  Volume2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ClayAudioVisualizer,
  ClayCallControl,
  ClayDialPad,
} from "@/components/clay";
import { useAgents } from "@/hooks/use-agents";
import {
  useDialInternalCall,
  useHangupInternalCall,
  useInternalActiveCalls,
  useInternalCallHistory,
  useInternalCallsHealth,
  useInternalExtensions,
  useInternalWebRTCConfig,
} from "@/hooks/use-internal-calls";
import {
  SipWebRTCClient,
  type SipCallState,
  type SipIncomingCall,
  type SipRegistrationState,
} from "@/lib/sip-webrtc-client";

const DIAL_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"] as const;

export default function InternalDialerPage() {
  const extensionsQuery = useInternalExtensions();
  const activeCallsQuery = useInternalActiveCalls();
  const historyQuery = useInternalCallHistory();
  const healthQuery = useInternalCallsHealth();
  const webrtcConfigQuery = useInternalWebRTCConfig();
  const agentsQuery = useAgents({ status: "ACTIVE" });

  const dialMutation = useDialInternalCall();
  const hangupMutation = useHangupInternalCall();

  // Dialer & WebRTC registration state
  const [fromExtension, setFromExtension] = useState("1001-ws");
  const [sipPassword, setSipPassword] = useState("");
  const [targetNumber, setTargetNumber] = useState("600");
  const [callMode, setCallMode] = useState<InternalCallMode>("human");
  const [agentId, setAgentId] = useState("");
  const [regState, setRegState] = useState<SipRegistrationState>("unregistered");
  const [regDetail, setRegDetail] = useState("Not registered");
  const [sipCallState, setSipCallState] = useState<SipCallState>("idle");
  const [incomingCall, setIncomingCall] = useState<SipIncomingCall | null>(null);
  const [iceState, setIceState] = useState<string>("new");
  const [muted, setMuted] = useState(false);
  const [held, setHeld] = useState(false);
  const [durationSec, setDurationSec] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Audio devices & mic test
  const [audioInputs, setAudioInputs] = useState<MediaDeviceInfo[]>([]);
  const [audioOutputs, setAudioOutputs] = useState<MediaDeviceInfo[]>([]);
  const [selectedMicId, setSelectedMicId] = useState("");
  const [selectedSpeakerId, setSelectedSpeakerId] = useState("");
  const [micTesting, setMicTesting] = useState(false);
  const [micLevel, setMicLevel] = useState(0);

  const clientRef = useRef<SipWebRTCClient | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const micRafRef = useRef<number | null>(null);

  const extensions = extensionsQuery.data ?? [];
  const activeCalls = activeCallsQuery.data ?? [];
  const history = historyQuery.data ?? [];
  const health = healthQuery.data;
  const webrtcCfg = webrtcConfigQuery.data;
  const activeAgents = agentsQuery.data ?? [];

  useEffect(() => {
    const client = new SipWebRTCClient({
      onRegistrationChange: (st, detail) => {
        setRegState(st);
        if (detail) setRegDetail(detail);
      },
      onCallStateChange: (st, detail) => {
        setSipCallState(st);
        if (st === "connected") setDurationSec(0);
        if (st === "ended" || st === "idle") {
          setMuted(false);
          setHeld(false);
          setIncomingCall(null);
        }
        if (detail) setNotice(detail);
      },
      onIncomingCall: (inc) => setIncomingCall(inc),
      onIceStateChange: (ice) => setIceState(ice),
      onRemoteStream: (stream) => {
        if (remoteAudioRef.current) {
          remoteAudioRef.current.srcObject = stream;
          void remoteAudioRef.current.play().catch(() => undefined);
        }
      },
      onError: (msg) => setErrorMsg(msg),
    });
    clientRef.current = client;
    return () => {
      client.disconnect();
      stopMicTest();
    };
  }, []);

  useEffect(() => {
    if (sipCallState !== "connected") return;
    const t = setInterval(() => setDurationSec((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [sipCallState]);

  const refreshDevices = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      const list = await navigator.mediaDevices.enumerateDevices();
      const ins = list.filter((d) => d.kind === "audioinput");
      const outs = list.filter((d) => d.kind === "audiooutput");
      setAudioInputs(ins);
      setAudioOutputs(outs);
      if (!selectedMicId && ins[0]) setSelectedMicId(ins[0].deviceId);
      if (!selectedSpeakerId && outs[0]) setSelectedSpeakerId(outs[0].deviceId);
      setNotice("Microphone permission granted and audio devices refreshed.");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Microphone permission denied.");
    }
  };

  const stopMicTest = () => {
    if (micRafRef.current) cancelAnimationFrame(micRafRef.current);
    micRafRef.current = null;
    micStreamRef.current?.getTracks().forEach((t) => t.stop());
    micStreamRef.current = null;
    setMicTesting(false);
    setMicLevel(0);
  };

  const toggleMicTest = async () => {
    if (micTesting) {
      stopMicTest();
      return;
    }
    try {
      setErrorMsg(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: selectedMicId ? { deviceId: { exact: selectedMicId } } : true,
      });
      micStreamRef.current = stream;
      const ctx = new AudioContext();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      setMicTesting(true);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b, 0) / Math.max(1, data.length);
        setMicLevel(Math.min(100, Math.round((avg / 128) * 100)));
        micRafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unable to start microphone test.");
    }
  };

  const handleRegister = async () => {
    setErrorMsg(null);
    setNotice(null);
    if (!sipPassword.trim()) {
      setErrorMsg("Enter your SIP extension password (ASTERISK_EXT_1001_PASSWORD / 1002).");
      return;
    }
    const wsUrl = webrtcCfg?.ws_url || "ws://127.0.0.1:8088/ws";
    const domain = webrtcCfg?.sip_domain || "127.0.0.1";
    await clientRef.current?.connectAndRegister({
      wsUrl,
      domain,
      extension: fromExtension,
      password: sipPassword,
      iceServers: webrtcCfg?.ice_servers,
    });
  };

  const handlePlaceCall = async () => {
    setErrorMsg(null);
    setNotice(null);
    const dest = targetNumber.trim();
    if (!dest) {
      setErrorMsg("Enter an internal extension (1001, 1002, 600, 700).");
      return;
    }
    if (regState === "registered" && clientRef.current) {
      try {
        await clientRef.current.call(dest, selectedMicId || undefined);
        return;
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "WebRTC call failed.");
      }
    }
    try {
      const rec = await dialMutation.mutateAsync({
        from_extension: fromExtension,
        to_extension: dest,
        mode: callMode,
        agent_id: callMode === "ai" ? agentId || activeAgents[0]?.id || null : null,
      });
      setNotice(`ARI originated ${rec.from_extension} → ${rec.to_extension} (${rec.call_id})`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Internal call origination failed.");
    }
  };

  const handleDialKey = (key: string) => {
    if (sipCallState === "connected") {
      clientRef.current?.sendDtmf(key);
      setNotice(`Sent DTMF ${key}`);
    } else {
      setTargetNumber((prev) => prev + key);
    }
  };

  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="space-y-6">
      <audio ref={remoteAudioRef} autoPlay className="hidden" />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Internal SIP &amp; WebRTC Dialer</h1>
          <p className="text-sm text-muted-foreground">
            Asterisk 23 internal extension calling, echo test (600), and AI voice assistant (700) — no paid SIP trunk required.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
              regState === "registered"
                ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
                : "border-border bg-muted text-muted-foreground"
            }`}
          >
            <Radio className="h-3.5 w-3.5" />
            WebRTC: {regState.toUpperCase()}
          </span>
          <Link
            href="/telephony"
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Back to Telephony
          </Link>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-border bg-muted/50 p-3 text-xs">{notice}</div>
      )}

      {incomingCall && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4">
          <div className="flex items-center gap-2 text-sm font-medium">
            <PhoneIncoming className="h-4 w-4 text-emerald-500" />
            <span>Incoming Call from {incomingCall.from}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void clientRef.current?.answerIncoming(selectedMicId || undefined)}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
            >
              Answer
            </button>
            <button
              type="button"
              onClick={() => clientRef.current?.rejectIncoming()}
              className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Dial Pad & Calling Mode */}
        <div className="rounded-xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Dial Pad &amp; Mode</h2>
            <div className="inline-flex rounded-lg border border-border p-0.5 text-[11px]">
              {(["human", "ai", "echo"] as InternalCallMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    setCallMode(m);
                    if (m === "echo") setTargetNumber("600");
                    if (m === "ai") setTargetNumber("700");
                  }}
                  className={`inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium ${
                    callMode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                  }`}
                >
                  {m === "ai" ? <Bot className="h-3 w-3" /> : m === "human" ? <User className="h-3 w-3" /> : <Volume2 className="h-3 w-3" />}
                  {m.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {callMode === "ai" && (
            <div>
              <label className="block text-[11px] font-medium text-muted-foreground">AI Agent</label>
              <select
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs"
              >
                <option value="">Default Active Agent</option>
                {activeAgents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <ClayDialPad
            value={targetNumber}
            onChange={setTargetNumber}
            onDigitPress={(d) => {
              if (sipCallState === "connected") {
                clientRef.current?.sendDtmf(d);
              }
            }}
            onCall={() => void handlePlaceCall()}
            onHangup={() => clientRef.current?.hangup()}
            inCall={sipCallState !== "idle" && sipCallState !== "ended"}
            canCall={!dialMutation.isPending}
            placeholder="Extension (1001, 1002, 600, 700)"
          />

          <div className="flex flex-wrap gap-1.5 text-[11px]">
            {[
              { ext: "1001", label: "Ext 1001" },
              { ext: "1002", label: "Ext 1002" },
              { ext: "600", label: "600 Echo" },
              { ext: "700", label: "700 AI" },
            ].map((p) => (
              <button
                key={p.ext}
                type="button"
                onClick={() => setTargetNumber(p.ext)}
                className="clay-btn rounded-xl bg-card px-2.5 py-1 text-foreground"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Center: Extension Login + Active Call Panel */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <h2 className="text-sm font-semibold">Extension Login (WebRTC / ARI)</h2>
            <div>
              <label className="block text-[11px] font-medium text-muted-foreground">Extension</label>
              <select
                value={fromExtension}
                onChange={(e) => setFromExtension(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
              >
                {extensions.length > 0 ? (
                  extensions
                    .filter((e) => e.transport !== "INTERNAL")
                    .map((e) => (
                      <option key={e.extension} value={e.extension}>
                        {e.label} ({e.state})
                      </option>
                    ))
                ) : (
                  <>
                    <option value="1001-ws">1001-ws (WebRTC Browser)</option>
                    <option value="1002-ws">1002-ws (WebRTC Browser)</option>
                    <option value="1001">1001 (UDP SIP)</option>
                    <option value="1002">1002 (UDP SIP)</option>
                  </>
                )}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-muted-foreground">SIP Password</label>
              <input
                type="password"
                value={sipPassword}
                onChange={(e) => setSipPassword(e.target.value)}
                placeholder="Extension secret (never stored)"
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void handleRegister()}
                className="flex-1 rounded-lg bg-primary py-2 text-xs font-medium text-primary-foreground hover:opacity-90"
              >
                Register WebRTC
              </button>
              <button
                type="button"
                onClick={() => clientRef.current?.disconnect()}
                className="rounded-lg border border-border px-3 py-2 text-xs hover:bg-muted"
              >
                Disconnect
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground">{regDetail}</p>
          </div>

          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Active Call Panel</h2>
              <span className="text-xs font-mono text-muted-foreground">
                {sipCallState === "connected" ? formatDuration(durationSec) : sipCallState.toUpperCase()}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              <ClayCallControl
                icon={muted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                label={muted ? "Unmute" : "Mute"}
                active={muted}
                disabled={sipCallState !== "connected" && sipCallState !== "held"}
                onClick={() => setMuted(clientRef.current?.setMuted(!muted) ?? !muted)}
              />
              <ClayCallControl
                icon={held ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                label={held ? "Resume" : "Hold"}
                active={held}
                disabled={sipCallState !== "connected" && sipCallState !== "held"}
                onClick={() => void clientRef.current?.setHold(!held).then(setHeld)}
              />
            </div>
            <div className="space-y-1.5 pt-1">
              <div className="text-[11px] font-medium text-muted-foreground">
                ARI Active Calls ({activeCalls.length})
              </div>
              {activeCalls.map((c) => (
                <div
                  key={c.call_id}
                  className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-xs"
                >
                  <span>
                    {c.from_extension} → {c.to_extension} ({c.mode})
                  </span>
                  <button
                    type="button"
                    onClick={() => void hangupMutation.mutateAsync({ callId: c.call_id })}
                    className="rounded bg-rose-600 px-2 py-1 text-[11px] text-white"
                  >
                    Hangup
                  </button>
                </div>
              ))}
              {activeCalls.length === 0 && (
                <p className="text-xs text-muted-foreground">No active ARI internal calls.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right: Audio Test & Connection Diagnostics */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Microphone &amp; Audio Devices</h2>
              <button
                type="button"
                onClick={() => void refreshDevices()}
                className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] hover:bg-muted"
              >
                <RefreshCw className="h-3 w-3" />
                Detect
              </button>
            </div>
            <select
              value={selectedMicId}
              onChange={(e) => setSelectedMicId(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs"
            >
              <option value="">Default Microphone</option>
              {audioInputs.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || `Mic ${d.deviceId.slice(0, 6)}`}
                </option>
              ))}
            </select>
            <select
              value={selectedSpeakerId}
              onChange={(e) => setSelectedSpeakerId(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-xs"
            >
              <option value="">Default Speaker</option>
              {audioOutputs.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || `Speaker ${d.deviceId.slice(0, 6)}`}
                </option>
              ))}
            </select>
            <div className="space-y-2.5">
              <button
                type="button"
                onClick={() => void toggleMicTest()}
                className="clay-btn w-full rounded-xl bg-card px-3 py-2 text-xs font-medium text-foreground"
              >
                {micTesting ? "Stop Mic Test" : "Test Microphone"}
              </button>
              <ClayAudioVisualizer
                active={micTesting || sipCallState === "connected"}
                level={micTesting ? micLevel / 100 : 0.45}
                label="Microphone & call audio level"
              />
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5 space-y-2 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-sm">
              <Activity className="h-4 w-4 text-primary" />
              <span>Connection Diagnostics</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Asterisk ARI</span>
              <span className="inline-flex items-center gap-1 font-medium">
                {health?.ari_connected ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    Connected ({health.asterisk_version || "23.x"})
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                    Disconnected
                  </>
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">WebRTC WS URL</span>
              <span className="font-mono">{webrtcCfg?.ws_url || "ws://127.0.0.1:8088/ws"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">ICE State</span>
              <span className="font-mono">{iceState}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Registered Extensions</span>
              <span>{health?.registered_extensions ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">External PSTN Gateway</span>
              <span>
                {health?.external_telephony_configured ? "Configured" : "Disabled (Internal Only)"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Call History */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Phone className="h-4 w-4" />
          <span>Internal Call History</span>
        </div>
        {history.length === 0 ? (
          <p className="text-xs text-muted-foreground">No internal calls recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3">Call ID</th>
                  <th className="py-2 pr-3">Route</th>
                  <th className="py-2 pr-3">Mode</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Duration</th>
                  <th className="py-2">Started</th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => (
                  <tr key={r.call_id} className="border-b border-border/50">
                    <td className="py-2 pr-3 font-mono">{r.call_id}</td>
                    <td className="py-2 pr-3">
                      {r.from_extension} → {r.to_extension}
                    </td>
                    <td className="py-2 pr-3 uppercase">{r.mode}</td>
                    <td className="py-2 pr-3">{r.status}</td>
                    <td className="py-2 pr-3">{r.duration_seconds}s</td>
                    <td className="py-2 text-muted-foreground">
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
