"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AgentCreatePayload, AgentUpdatePayload } from "@agentvoice/shared-types";
import {
  activateAgent,
  createAgent,
  deactivateAgent,
  deleteAgent,
  duplicateAgent,
  fetchAgent,
  fetchAgents,
  fetchAgentTemplates,
  updateAgent,
  type AgentListFilters,
} from "@/lib/api-client";

export function useAgents(filters?: AgentListFilters) {
  return useQuery({
    queryKey: ["agents", filters ?? {}],
    queryFn: () => fetchAgents(filters),
  });
}

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => fetchAgent(agentId),
    enabled: Boolean(agentId),
  });
}

export function useAgentTemplates() {
  return useQuery({
    queryKey: ["agent-templates"],
    queryFn: fetchAgentTemplates,
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AgentCreatePayload) => createAgent(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useUpdateAgent(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AgentUpdatePayload) => updateAgent(agentId, payload),
    onSuccess: (updated) => {
      void qc.invalidateQueries({ queryKey: ["agents"] });
      qc.setQueryData(["agent", agentId], updated);
    },
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => deleteAgent(agentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useDuplicateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => duplicateAgent(agentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useActivateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => activateAgent(agentId),
    onSuccess: (updated) => {
      void qc.invalidateQueries({ queryKey: ["agents"] });
      qc.setQueryData(["agent", updated.id], updated);
    },
  });
}

export function useDeactivateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => deactivateAgent(agentId),
    onSuccess: (updated) => {
      void qc.invalidateQueries({ queryKey: ["agents"] });
      qc.setQueryData(["agent", updated.id], updated);
    },
  });
}
