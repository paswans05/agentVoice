"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AudioSettings } from "@agentvoice/shared-types";
import {
  fetchAudioSettings,
  fetchSpeechHealth,
  fetchSTTModels,
  fetchTTSVoices,
  updateAudioSettings,
} from "@/lib/api-client";

export function useSpeechHealth() {
  return useQuery({
    queryKey: ["speech-health"],
    queryFn: fetchSpeechHealth,
    refetchInterval: 20_000,
    retry: 1,
  });
}

export function useSTTModels() {
  return useQuery({
    queryKey: ["stt-models"],
    queryFn: fetchSTTModels,
  });
}

export function useTTSVoices() {
  return useQuery({
    queryKey: ["tts-voices"],
    queryFn: fetchTTSVoices,
  });
}

export function useAudioSettings() {
  return useQuery({
    queryKey: ["audio-settings"],
    queryFn: fetchAudioSettings,
  });
}

export function useUpdateAudioSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AudioSettings) => updateAudioSettings(payload),
    onSuccess: (saved) => {
      qc.setQueryData(["audio-settings"], saved);
    },
  });
}
