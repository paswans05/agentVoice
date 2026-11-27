"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type {
  CallMetricsSnapshot,
  CallSession,
  LiveCallsWsFrame,
  NormalizedCallEvent,
  TranscriptSegment,
} from "@agentvoice/shared-types";
import {
  ArrowLeft,
  Flag,
  Gauge,
  MessageSquareText,
  PauseCircle,
  PhoneForwarded,
  PhoneOff,
  PlayCircle,
  Search,
  ShieldAlert,
} from "lucide-react";

import { useLiveCallsWebSocket } from "@/hooks/use-live-calls";
import {
  fetchCallEvents,
  fetchCallMetrics,
  fetchCallTranscript,
  fetchLiveCallDetail,
  flagLiveCall,
  holdLiveCall,
  resumeLiveCall,
  terminateLiveCall,
  transferLiveCall,
} from "@/lib/api-client";

const TERMINAL = new Set([
  "COMPLETED",
  "FAILED",
  "BUSY",
  "NO_ANSWER",
  "TERMINATED",
  "DISCONNECTED",
]);

export default function LiveCallDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: callId } = use(params);
  const [session, setSession] = useState<CallSession | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [events, setEvents] = useState<NormalizedCallEvent[]>([]);
  const [metrics, setMetrics] = useState<CallMetricsSnapshot | null>(null);
  const [transcriptSearch, setTranscriptSearch] = useState("");
  const [transferDest, setTransferDest] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    try {
      const [s, t, e, m] = await Promise.all([
        fetchLiveCallDetail(callId),
        fetchCallTranscript(callId, transcriptSearch || undefined),
        fetchCallEvents(callId),
        fetchCallMetrics(callId),
      ]);
      setSession(s);
      setTranscript(t);
      setEvents(e);
      setMetrics(m);
      setErrorMsg(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load call session.");
    }
  }, [callId, transcriptSearch]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const { connectionState } = useLiveCallsWebSocket({
    callIds: useMemo(() => [callId], [callId]),
    onFrame: useCallback(
      (frame: LiveCallsWsFrame) => {
        if (frame.type === "TRANSCRIPT_SEGMENT" && frame.call_id === callId) {
          setTranscript((prev) => {
            const idx = prev.findIndex((seg) => seg.segment_id === frame.segment.segment_id);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = frame.segment;
              return next;
            }
            return [...prev, frame.segment];
          });
        } else if (frame.type === "METRICS_UPDATED" && frame.call_id === callId) {
          setMetrics(frame.metrics);
        } else if (frame.type === "CALL_EVENT" && frame.call_id === callId) {
          void loadDetail();
        }
      },
      [callId, loadDetail],
    ),
  });

  const isTerminal = session ? TERMINAL.has(session.status) : false;
  const supportsHoldOrTransfer = session ? session.provider !== "browser" && session.provider !== "dry_run" : false;

  const runAction = async (fn: () => Promise<CallSession>, label: string) => {
    setBusy(true);
    setNotice(null);
    try {
      const updated = await fn();
      setSession(updated);
      setNotice(`${label} succeeded.`);
      await loadDetail();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : `${label} failed.`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href="/live-calls"
            className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <div>
            <h1 className="text-xl font-semibold font-mono">{callId}</h1>
            <p className="text-xs text-muted-foreground">
              Stream: {connectionState} · Provider: {session?.provider ?? "—"} · Recording:{" "}
              {session?.recording_enabled ? "Enabled" : "Disabled"}
            </p>
          </div>
        </div>

        {session && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void runAction(() => flagLiveCall(callId, "Supervisor review"), "Flag")
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
            >
              <Flag className="h-3.5 w-3.5" />
              Flag
            </button>
            <button
              type="button"
              disabled={busy || isTerminal || !supportsHoldOrTransfer}
              title={
                supportsHoldOrTransfer
                  ? "Hold call"
                  : "Hold requires an active telephony provider"
              }
              onClick={() =>
                void runAction(
                  () =>
                    session.status === "ON_HOLD"
                      ? resumeLiveCall(callId)
                      : holdLiveCall(callId),
                  session.status === "ON_HOLD" ? "Resume" : "Hold",
                )
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-40"
            >
              {session.status === "ON_HOLD" ? (
                <>
                  <PlayCircle className="h-3.5 w-3.5" /> Resume
                </>
              ) : (
                <>
                  <PauseCircle className="h-3.5 w-3.5" /> Hold
                </>
              )}
            </button>
            <button
              type="button"
              disabled={busy || isTerminal}
              onClick={() =>
                void runAction(
                  () => terminateLiveCall(callId, "Operator terminated call"),
                  "Terminate",
                )
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-500/20 dark:text-rose-300 disabled:opacity-50"
            >
              <PhoneOff className="h-3.5 w-3.5" />
              Terminate Call
            </button>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-border bg-muted/50 p-3 text-xs text-foreground">
          {notice}
        </div>
      )}

      {session && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs text-muted-foreground">Status / AI State</div>
            <div className="mt-1 text-base font-semibold">
              {session.status} · {session.current_agent_state}
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs text-muted-foreground">Agent ID</div>
            <div className="mt-1 font-mono text-sm font-medium">{session.agent_id}</div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs text-muted-foreground">Masked Caller</div>
            <div className="mt-1 font-mono text-sm font-medium">
              {session.caller_number_masked || "Browser Microphone"}
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs text-muted-foreground">Duration</div>
            <div className="mt-1 font-mono text-base font-semibold">
              {session.duration_seconds}s
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Live Transcript */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card flex flex-col">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <div className="flex items-center gap-2 font-medium">
              <MessageSquareText className="h-4 w-4 text-primary" />
              <span>Live Transcript ({transcript.length})</span>
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                value={transcriptSearch}
                onChange={(e) => setTranscriptSearch(e.target.value)}
                placeholder="Search transcript..."
                className="rounded-md border border-border bg-background py-1 pl-8 pr-2.5 text-xs"
              />
            </div>
          </div>
          <div className="max-h-[420px] overflow-y-auto p-4 space-y-3">
            {transcript.length === 0 ? (
              <p className="text-xs text-muted-foreground">No transcript segments yet.</p>
            ) : (
              transcript.map((seg) => (
                <div
                  key={seg.segment_id}
                  className={`rounded-lg border p-3 text-sm ${
                    seg.speaker === "AI_AGENT"
                      ? "border-primary/20 bg-primary/5"
                      : "border-border bg-muted/30"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">{seg.speaker}</span>
                    <span>
                      {seg.final ? "Final" : "Partial"} ·{" "}
                      {new Date(seg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap">{seg.text}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Metrics, Transfer, Event Timeline */}
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center gap-2 font-medium text-sm">
              <Gauge className="h-4 w-4 text-primary" />
              <span>Latency & Stream Health</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-muted/40 p-2">
                <div className="text-muted-foreground">STT</div>
                <div className="font-mono font-semibold">
                  {metrics?.stt_latency_ms != null ? `${metrics.stt_latency_ms} ms` : "—"}
                </div>
              </div>
              <div className="rounded-lg bg-muted/40 p-2">
                <div className="text-muted-foreground">LLM TTFT</div>
                <div className="font-mono font-semibold">
                  {metrics?.llm_ttft_ms != null ? `${metrics.llm_ttft_ms} ms` : "—"}
                </div>
              </div>
              <div className="rounded-lg bg-muted/40 p-2">
                <div className="text-muted-foreground">TTS</div>
                <div className="font-mono font-semibold">
                  {metrics?.tts_latency_ms != null ? `${metrics.tts_latency_ms} ms` : "—"}
                </div>
              </div>
              <div className="rounded-lg bg-muted/40 p-2">
                <div className="text-muted-foreground">End-to-End</div>
                <div className="font-mono font-semibold">
                  {metrics?.end_to_end_ms != null ? `${metrics.end_to_end_ms} ms` : "—"}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center gap-2 font-medium text-sm">
              <PhoneForwarded className="h-4 w-4 text-primary" />
              <span>Human Handoff / Transfer</span>
            </div>
            {!supportsHoldOrTransfer && (
              <p className="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-300">
                <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                Transfer requires an active telephony provider; browser/dry-run sessions cannot
                transfer.
              </p>
            )}
            <div className="flex gap-2">
              <input
                type="text"
                value={transferDest}
                onChange={(e) => setTransferDest(e.target.value)}
                placeholder="Extension or phone..."
                disabled={!supportsHoldOrTransfer || isTerminal}
                className="flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs disabled:opacity-50"
              />
              <button
                type="button"
                disabled={busy || !supportsHoldOrTransfer || isTerminal || !transferDest.trim()}
                onClick={() =>
                  void runAction(
                    () => transferLiveCall(callId, transferDest.trim()),
                    "Transfer",
                  )
                }
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-40"
              >
                Transfer
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="font-medium text-sm">Event Timeline ({events.length})</div>
            <div className="max-h-[240px] overflow-y-auto space-y-2">
              {events.length === 0 ? (
                <p className="text-xs text-muted-foreground">No events recorded.</p>
              ) : (
                events.map((ev) => (
                  <div key={ev.event_id} className="rounded-md border border-border p-2 text-xs">
                    <div className="flex items-center justify-between font-medium">
                      <span>{ev.event_type}</span>
                      <span className="font-mono text-muted-foreground">#{ev.sequence_number}</span>
                    </div>
                    <div className="text-muted-foreground">
                      {ev.source} · {new Date(ev.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
