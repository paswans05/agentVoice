"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, PhoneOff, Radio } from "lucide-react";

import {
  AgentSummary,
  createVoiceAndWebRTCSession,
  listActiveAgents,
  terminateWebRTCSession,
} from "@/services/api";
import { loadDeviceIdentity } from "@/services/device";
import { startWebRTCVoiceConnection, WebRTCSessionHandles } from "@/services/webrtc";

export function VoiceSession() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [agentId, setAgentId] = useState("");
  const [active, setActive] = useState(false);
  const [muted, setMuted] = useState(false);
  const [iceState, setIceState] = useState("new");
  const [agentState, setAgentState] = useState("IDLE");
  const [transcript, setTranscript] = useState<{ speaker: string; text: string }[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handlesRef = useRef<WebRTCSessionHandles | null>(null);
  const webrtcSessionIdRef = useRef<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    const id = loadDeviceIdentity();
    if (!id) return;
    void listActiveAgents(id.apiBaseUrl).then((list) => {
      setAgents(list);
      if (list.length > 0) setAgentId(list[0].id);
    });
    return () => {
      handlesRef.current?.cleanup();
    };
  }, []);

  const handleStart = async () => {
    const id = loadDeviceIdentity();
    if (!id || !agentId) return;
    setErrorMsg(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      streamRef.current = stream;

      const sess = await createVoiceAndWebRTCSession(
        id.apiBaseUrl,
        id.deviceId,
        id.deviceToken,
        agentId,
      );
      webrtcSessionIdRef.current = sess.webrtcSessionId;

      const handles = await startWebRTCVoiceConnection({
        apiBase: id.apiBaseUrl,
        deviceId: id.deviceId,
        deviceToken: id.deviceToken,
        webrtcSessionId: sess.webrtcSessionId,
        voiceSessionId: sess.voiceSessionId,
        stunUrls: sess.stunUrls,
        stream,
        onIceState: setIceState,
        onAgentState: setAgentState,
        onTranscript: (speaker, text) =>
          setTranscript((prev) => [...prev, { speaker, text }]),
        onAudioWav: (buf) => {
          const blob = new Blob([buf], { type: "audio/wav" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.onended = () => URL.revokeObjectURL(url);
          void audio.play().catch(() => {
            setErrorMsg("Tap screen if Safari paused audio playback.");
          });
        },
        onError: setErrorMsg,
      });
      handlesRef.current = handles;
      setActive(true);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to start WebRTC voice session.");
    }
  };

  const handleStop = async () => {
    handlesRef.current?.cleanup();
    handlesRef.current = null;
    const id = loadDeviceIdentity();
    if (id && webrtcSessionIdRef.current) {
      await terminateWebRTCSession(id.apiBaseUrl, webrtcSessionIdRef.current);
      webrtcSessionIdRef.current = null;
    }
    setActive(false);
    setAgentState("COMPLETED");
  };

  const toggleMute = () => {
    if (!streamRef.current) return;
    const next = !muted;
    for (const t of streamRef.current.getAudioTracks()) t.enabled = !next;
    setMuted(next);
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">AgentVoice Internet Voice Call</div>
          <div className="text-[11px] text-zinc-400">
            WebRTC + VoiceConversationService · ICE: {iceState} · AI: {agentState}
          </div>
        </div>
        {active && <Radio className="h-4 w-4 text-emerald-400 animate-pulse" />}
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-2.5 text-xs text-rose-200">
          {errorMsg}
        </div>
      )}

      <label className="block text-xs space-y-1">
        <span className="text-zinc-400">Select Active AI Agent</span>
        <select
          value={agentId}
          disabled={active}
          onChange={(e) => setAgentId(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white"
        >
          {agents.length === 0 && <option value="">No active agents found</option>}
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.type})
            </option>
          ))}
        </select>
      </label>

      <div className="flex flex-wrap gap-2">
        {!active ? (
          <button
            type="button"
            disabled={!agentId}
            onClick={() => void handleStart()}
            className="flex-1 rounded-xl bg-emerald-600 py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Start AI Voice Call
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={toggleMute}
              className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-700 px-4 py-3 text-xs"
            >
              {muted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              {muted ? "Unmute" : "Mute"}
            </button>
            <button
              type="button"
              onClick={() => void handleStop()}
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-rose-600 py-3 text-sm font-semibold text-white"
            >
              <PhoneOff className="h-4 w-4" />
              End Session
            </button>
          </>
        )}
      </div>

      <div className="max-h-56 overflow-y-auto space-y-2 rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs">
        {transcript.length === 0 ? (
          <div className="text-zinc-500">Live transcript will appear here once you speak.</div>
        ) : (
          transcript.map((item, i) => (
            <div key={i}>
              <strong className={item.speaker === "AI" ? "text-blue-400" : "text-emerald-400"}>
                {item.speaker}:
              </strong>{" "}
              <span>{item.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
