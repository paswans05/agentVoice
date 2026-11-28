"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { InternalCallMode } from "@agentvoice/shared-types";
import {
  dialInternalCall,
  fetchInternalActiveCalls,
  fetchInternalCallHistory,
  fetchInternalCallsHealth,
  fetchInternalExtensions,
  fetchInternalWebRTCConfig,
  hangupInternalCall,
} from "@/lib/api-client";

export function useInternalExtensions() {
  return useQuery({
    queryKey: ["internal-extensions"],
    queryFn: fetchInternalExtensions,
    refetchInterval: 5000,
  });
}

export function useInternalActiveCalls() {
  return useQuery({
    queryKey: ["internal-active-calls"],
    queryFn: fetchInternalActiveCalls,
    refetchInterval: 3000,
  });
}

export function useInternalCallHistory() {
  return useQuery({
    queryKey: ["internal-call-history"],
    queryFn: () => fetchInternalCallHistory(50),
    refetchInterval: 6000,
  });
}

export function useInternalCallsHealth() {
  return useQuery({
    queryKey: ["internal-calls-health"],
    queryFn: fetchInternalCallsHealth,
    refetchInterval: 5000,
  });
}

export function useInternalWebRTCConfig() {
  return useQuery({
    queryKey: ["internal-webrtc-config"],
    queryFn: fetchInternalWebRTCConfig,
  });
}

export function useDialInternalCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      from_extension: string;
      to_extension: string;
      mode?: InternalCallMode;
      agent_id?: string | null;
      idempotency_key?: string | null;
    }) => dialInternalCall(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["internal-active-calls"] });
      void qc.invalidateQueries({ queryKey: ["internal-call-history"] });
      void qc.invalidateQueries({ queryKey: ["internal-calls-health"] });
    },
  });
}

export function useHangupInternalCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ callId, reason }: { callId: string; reason?: string }) =>
      hangupInternalCall(callId, reason),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["internal-active-calls"] });
      void qc.invalidateQueries({ queryKey: ["internal-call-history"] });
      void qc.invalidateQueries({ queryKey: ["internal-calls-health"] });
    },
  });
}
