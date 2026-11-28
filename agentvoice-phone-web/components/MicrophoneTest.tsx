"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2 } from "lucide-react";

export function MicrophoneTest({
  onMicGranted,
}: {
  onMicGranted?: (granted: boolean) => void;
}) {
  const [testing, setTesting] = useState(false);
  const [muted, setMuted] = useState(false);
  const [level, setLevel] = useState(0);
  const [status, setStatus] = useState("Tap Start Microphone Test to grant permission.");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const stopTest = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (streamRef.current) {
      for (const t of streamRef.current.getTracks()) t.stop();
      streamRef.current = null;
    }
    if (audioCtxRef.current) {
      void audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    setTesting(false);
    setLevel(0);
  };

  useEffect(() => () => stopTest(), []);

  const startTest = async () => {
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
      onMicGranted?.(true);
      setTesting(true);
      setStatus("Microphone active. Speak to test input level.");

      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      const buf = new Uint8Array(analyser.frequencyBinCount);

      const tick = () => {
        analyser.getByteFrequencyData(buf);
        const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
        setLevel(Math.min(100, Math.round((avg / 128) * 100)));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch (err) {
      onMicGranted?.(false);
      setErrorMsg(
        err instanceof Error
          ? `${err.name}: ${err.message}. In Safari, tap aA / Website Settings → Microphone → Allow.`
          : "Microphone access denied.",
      );
    }
  };

  const toggleMute = () => {
    if (!streamRef.current) return;
    const next = !muted;
    for (const track of streamRef.current.getAudioTracks()) {
      track.enabled = !next;
    }
    setMuted(next);
  };

  const playTestTone = () => {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 523.25;
    gain.gain.value = 0.15;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
    setStatus("Played speaker test tone.");
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-sm">Microphone & Speaker Test</span>
        <span className="text-xs text-zinc-400">{testing ? "Active" : "Idle"}</span>
      </div>

      <p className="text-xs text-zinc-400">{status}</p>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-2.5 text-xs text-rose-200">
          {errorMsg}
        </div>
      )}

      <div className="h-2.5 w-full rounded-full bg-zinc-800 overflow-hidden">
        <div
          className="h-full bg-emerald-500 transition-all duration-75"
          style={{ width: `${muted ? 0 : level}%` }}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {!testing ? (
          <button
            type="button"
            onClick={() => void startTest()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white"
          >
            <Mic className="h-3.5 w-3.5" />
            Start Microphone Test
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={toggleMute}
              className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-xs"
            >
              {muted ? <MicOff className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
              {muted ? "Unmute" : "Mute"}
            </button>
            <button
              type="button"
              onClick={stopTest}
              className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white"
            >
              Stop Test
            </button>
          </>
        )}
        <button
          type="button"
          onClick={playTestTone}
          className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-xs"
        >
          <Volume2 className="h-3.5 w-3.5" />
          Test Speaker
        </button>
      </div>
    </div>
  );
}
