"use client";

import type {
  LatencyMetrics,
  VoiceSessionInfo,
  VoiceSessionState,
  VoiceWsEvent,
} from "@agentvoice/shared-types";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  createVoiceSession,
  deleteVoiceSession,
  getVoiceWebSocketUrl,
} from "@/lib/api-client";

export interface MediaDeviceOption {
  deviceId: string;
  label: string;
}

export interface UseVoiceSessionOptions {
  agentId: string;
  conversationId: string | null;
  onTranscriptFinal?: (text: string) => void;
  onResponseText?: (text: string) => void;
}

function float32ToPcm16(input: Float32Array, inputRate: number, targetRate = 16000): ArrayBuffer {
  let samples = input;
  if (inputRate !== targetRate && inputRate > targetRate) {
    const ratio = inputRate / targetRate;
    const newLength = Math.floor(input.length / ratio);
    const resampled = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
      resampled[i] = input[Math.floor(i * ratio)];
    }
    samples = resampled;
  }

  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

export function useVoiceSession({
  agentId,
  conversationId,
  onTranscriptFinal,
  onResponseText,
}: UseVoiceSessionOptions) {
  const [session, setSession] = useState<VoiceSessionInfo | null>(null);
  const [sessionState, setSessionState] = useState<VoiceSessionState>("IDLE");
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<LatencyMetrics | null>(null);

  const [microphones, setMicrophones] = useState<MediaDeviceOption[]>([]);
  const [speakers, setSpeakers] = useState<MediaDeviceOption[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>("");
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string>("");

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const activeSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const isMutedRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);

  isMutedRef.current = isMuted;

  const stopPlayback = useCallback(() => {
    if (activeSourceRef.current) {
      try {
        activeSourceRef.current.stop();
      } catch {
        // ignore if already stopped
      }
      activeSourceRef.current.disconnect();
      activeSourceRef.current = null;
    }
  }, []);

  const refreshDevices = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.enumerateDevices) return;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const mics = devices
        .filter((d) => d.kind === "audioinput")
        .map((d, idx) => ({
          deviceId: d.deviceId,
          label: d.label || `Microphone ${idx + 1}`,
        }));
      const spks = devices
        .filter((d) => d.kind === "audiooutput")
        .map((d, idx) => ({
          deviceId: d.deviceId,
          label: d.label || `Speaker ${idx + 1}`,
        }));
      setMicrophones(mics);
      setSpeakers(spks);
    } catch {
      // Device enumeration may be restricted before permission
    }
  }, []);

  const cleanup = useCallback(() => {
    stopPlayback();
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop();
      }
      streamRef.current = null;
    }
    if (audioCtxRef.current) {
      void audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (wsRef.current) {
      try {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "session.end" }));
        }
        wsRef.current.close();
      } catch {
        // ignore
      }
      wsRef.current = null;
    }
    if (sessionIdRef.current) {
      const idToDelete = sessionIdRef.current;
      sessionIdRef.current = null;
      void deleteVoiceSession(idToDelete).catch(() => {});
    }
    setIsConnected(false);
    setAudioLevel(0);
    setSessionState("IDLE");
  }, [stopPlayback]);

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  const playWavBytes = useCallback(
    async (wavBuffer: ArrayBuffer) => {
      stopPlayback();
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = audioCtxRef.current ?? new AudioCtx();
      audioCtxRef.current = ctx;
      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      const decoded = await ctx.decodeAudioData(wavBuffer.slice(0));
      const source = ctx.createBufferSource();
      source.buffer = decoded;
      source.connect(ctx.destination);
      source.onended = () => {
        if (activeSourceRef.current === source) {
          activeSourceRef.current = null;
        }
      };
      activeSourceRef.current = source;
      source.start(0);
    },
    [stopPlayback],
  );

  const startConversation = useCallback(async () => {
    setError(null);
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Browser microphone capture is not supported in this environment.");
      return;
    }

    setSessionState("CONNECTING");

    let mediaStream: MediaStream;
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: selectedMicId
          ? { deviceId: { exact: selectedMicId }, echoCancellation: true, noiseSuppression: true }
          : { echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = mediaStream;
      void refreshDevices();
    } catch (err) {
      setSessionState("ERROR");
      setError(
        err instanceof Error
          ? `Microphone permission denied or unavailable: ${err.message}`
          : "Microphone permission denied or unavailable.",
      );
      return;
    }

    let createdSession: VoiceSessionInfo;
    try {
      createdSession = await createVoiceSession(agentId, conversationId);
      setSession(createdSession);
      sessionIdRef.current = createdSession.session_id;
    } catch (err) {
      cleanup();
      setSessionState("ERROR");
      setError(err instanceof Error ? err.message : "Failed to start voice session.");
      return;
    }

    const ws = new WebSocket(getVoiceWebSocketUrl(createdSession.session_id));
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;

      const source = ctx.createMediaStreamSource(mediaStream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (event) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);

        if (isMutedRef.current) {
          setAudioLevel(0);
          return;
        }

        // Compute real RMS level for UI activity indicator
        let sumSq = 0;
        for (let i = 0; i < input.length; i++) {
          sumSq += input[i] * input[i];
        }
        const rms = Math.sqrt(sumSq / input.length);
        setAudioLevel(Math.min(1, rms * 6));

        const pcmBuffer = float32ToPcm16(input, ctx.sampleRate, 16000);
        ws.send(pcmBuffer);
      };

      source.connect(processor);
      processor.connect(ctx.destination);
    };

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        void playWavBytes(event.data).catch((err) => {
          setError(err instanceof Error ? err.message : "Audio playback failed.");
        });
        return;
      }

      if (typeof event.data === "string") {
        try {
          const parsed = JSON.parse(event.data) as VoiceWsEvent;
          if (parsed.type === "session.state") {
            setSessionState(parsed.state);
          } else if (parsed.type === "transcript.final") {
            onTranscriptFinal?.(parsed.text);
          } else if (parsed.type === "response.text") {
            onResponseText?.(parsed.text);
          } else if (parsed.type === "response.interrupted") {
            stopPlayback();
          } else if (parsed.type === "metrics") {
            setLatency(parsed.data);
          } else if (parsed.type === "error") {
            setError(parsed.message);
          }
        } catch {
          // ignore malformed event
        }
      }
    };

    ws.onerror = () => {
      setError("Voice WebSocket connection error.");
      setSessionState("ERROR");
    };

    ws.onclose = () => {
      setIsConnected(false);
    };
  }, [
    agentId,
    cleanup,
    conversationId,
    onResponseText,
    onTranscriptFinal,
    playWavBytes,
    refreshDevices,
    selectedMicId,
    stopPlayback,
  ]);

  const endConversation = useCallback(() => {
    cleanup();
  }, [cleanup]);

  const interrupt = useCallback(() => {
    stopPlayback();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "session.interrupt" }));
    }
  }, [stopPlayback]);

  return {
    session,
    sessionState,
    isConnected,
    isMuted,
    setIsMuted,
    audioLevel,
    error,
    latency,
    microphones,
    speakers,
    selectedMicId,
    setSelectedMicId,
    selectedSpeakerId,
    setSelectedSpeakerId,
    refreshDevices,
    startConversation,
    endConversation,
    interrupt,
  };
}
