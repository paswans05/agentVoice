"use client";

import { APP_CONFIG } from "@agentvoice/config";
import type { AudioSettings } from "@agentvoice/shared-types";
import { STATUS_TONE_CLASSES } from "@agentvoice/ui";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useBackendHealth, useSystemStatus } from "@/hooks/use-health";
import {
  useAudioSettings,
  useSpeechHealth,
  useSTTModels,
  useTTSVoices,
  useUpdateAudioSettings,
} from "@/hooks/use-speech";
import { API_BASE_URL } from "@/lib/api-client";

export default function SettingsPage() {
  const { data: health } = useBackendHealth();
  const { data: status } = useSystemStatus();
  const speechHealthQuery = useSpeechHealth();
  const audioSettingsQuery = useAudioSettings();
  const sttModelsQuery = useSTTModels();
  const ttsVoicesQuery = useTTSVoices();
  const updateAudioMutation = useUpdateAudioSettings();

  const [audioForm, setAudioForm] = useState<AudioSettings | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    if (audioSettingsQuery.data && !audioForm) {
      setAudioForm(audioSettingsQuery.data);
    }
  }, [audioSettingsQuery.data, audioForm]);

  const handleSaveAudio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!audioForm) return;
    setSaveMessage(null);
    try {
      await updateAudioMutation.mutateAsync(audioForm);
      setSaveMessage("Audio & speech defaults saved.");
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : "Failed to save audio settings.");
    }
  };

  const speechHealth = speechHealthQuery.data;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Runtime, storage, audio defaults, and appearance settings for {APP_CONFIG.name}.
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-medium">Appearance</h2>
            <p className="text-sm text-muted-foreground">
              Switch between light and dark dashboard themes.
            </p>
          </div>
          <ThemeToggle />
        </div>
      </div>

      {/* Audio & Speech Settings */}
      <form onSubmit={(e) => void handleSaveAudio(e)} className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-medium">Audio &amp; Speech Defaults</h2>
            <p className="text-xs text-muted-foreground">
              Agent-specific voice settings take precedence over these global defaults.
            </p>
          </div>
          {speechHealth && (
            <div className="flex gap-2 text-[11px]">
              <span
                className={`rounded-full border px-2 py-0.5 ${
                  STATUS_TONE_CLASSES[speechHealth.stt.available ? "healthy" : "unavailable"]
                }`}
              >
                STT: {speechHealth.stt.available ? "Ready" : "Unavailable"}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 ${
                  STATUS_TONE_CLASSES[speechHealth.tts.available ? "healthy" : "unavailable"]
                }`}
              >
                TTS: {speechHealth.tts.available ? "Ready" : "Unavailable"}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 ${
                  STATUS_TONE_CLASSES[speechHealth.vad.available ? "healthy" : "unavailable"]
                }`}
              >
                VAD: {speechHealth.vad.available ? "Ready" : "Unavailable"}
              </span>
            </div>
          )}
        </div>

        {audioForm && (
          <div className="grid gap-4 sm:grid-cols-2 text-sm">
            <div>
              <label htmlFor="stt-model" className="block text-xs font-medium text-muted-foreground">
                STT Model (faster-whisper)
              </label>
              <select
                id="stt-model"
                value={audioForm.stt_model}
                onChange={(e) => setAudioForm({ ...audioForm, stt_model: e.target.value })}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                {(sttModelsQuery.data ?? []).map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.approximate_size})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="hinglish-mode" className="block text-xs font-medium text-muted-foreground">
                Hinglish Script Behavior
              </label>
              <select
                id="hinglish-mode"
                value={audioForm.hinglish_script_mode}
                onChange={(e) =>
                  setAudioForm({
                    ...audioForm,
                    hinglish_script_mode: e.target.value as AudioSettings["hinglish_script_mode"],
                  })
                }
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="auto">Auto (Preserve English technical terms)</option>
                <option value="original">Original</option>
                <option value="hindi">Hindi-oriented</option>
                <option value="english">English-oriented</option>
              </select>
            </div>

            <div>
              <label htmlFor="default-voice" className="block text-xs font-medium text-muted-foreground">
                Default TTS Voice (Piper)
              </label>
              <select
                id="default-voice"
                value={audioForm.default_voice_id}
                onChange={(e) => setAudioForm({ ...audioForm, default_voice_id: e.target.value })}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="default">Not selected</option>
                {(ttsVoicesQuery.data ?? []).map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.language})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="vad-silence" className="block text-xs font-medium text-muted-foreground">
                Silence Timeout (ms)
              </label>
              <input
                id="vad-silence"
                type="number"
                min={200}
                max={5000}
                value={audioForm.min_silence_ms}
                onChange={(e) =>
                  setAudioForm({ ...audioForm, min_silence_ms: Number(e.target.value) || 700 })
                }
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label htmlFor="vad-threshold" className="block text-xs font-medium text-muted-foreground">
                VAD Sensitivity Threshold ({audioForm.vad_threshold})
              </label>
              <input
                id="vad-threshold"
                type="range"
                min={0.005}
                max={0.1}
                step={0.005}
                value={audioForm.vad_threshold}
                onChange={(e) =>
                  setAudioForm({ ...audioForm, vad_threshold: Number(e.target.value) })
                }
                className="mt-2 w-full"
              />
            </div>

            <div>
              <label htmlFor="max-utterance" className="block text-xs font-medium text-muted-foreground">
                Max Utterance Duration (ms)
              </label>
              <input
                id="max-utterance"
                type="number"
                min={2000}
                max={60000}
                value={audioForm.max_utterance_ms}
                onChange={(e) =>
                  setAudioForm({ ...audioForm, max_utterance_ms: Number(e.target.value) || 20000 })
                }
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-muted-foreground">{saveMessage ?? ""}</span>
          <button
            type="submit"
            disabled={!audioForm || updateAudioMutation.isPending}
            className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {updateAudioMutation.isPending ? "Saving..." : "Save Audio Settings"}
          </button>
        </div>
      </form>

      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-base font-medium">System &amp; Storage Configuration</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex flex-col gap-1 border-b border-border pb-2 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Backend API URL</dt>
            <dd className="font-mono text-xs sm:text-sm">{API_BASE_URL}</dd>
          </div>
          <div className="flex flex-col gap-1 border-b border-border pb-2 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Storage Backend</dt>
            <dd className="font-medium uppercase">{health?.storage.backend ?? "json"}</dd>
          </div>
          <div className="flex flex-col gap-1 border-b border-border pb-2 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Data Directory</dt>
            <dd className="font-mono text-xs sm:text-sm break-all">
              {health?.storage.data_dir ?? "—"}
            </dd>
          </div>
          <div className="flex flex-col gap-1 sm:flex-row sm:justify-between">
            <dt className="text-muted-foreground">Environment</dt>
            <dd className="font-medium capitalize">{status?.environment ?? "—"}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
