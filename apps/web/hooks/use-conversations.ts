"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createConversation,
  deleteConversation,
  fetchAgentConversations,
  fetchConversation,
} from "@/lib/api-client";

export function useAgentConversations(agentId: string) {
  return useQuery({
    queryKey: ["agent-conversations", agentId],
    queryFn: () => fetchAgentConversations(agentId),
    enabled: Boolean(agentId),
  });
}

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => fetchConversation(conversationId as string),
    enabled: Boolean(conversationId),
  });
}

export function useCreateConversation(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) => createConversation(agentId, title),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agent-conversations", agentId] });
    },
  });
}

export function useDeleteConversation(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => deleteConversation(conversationId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agent-conversations", agentId] });
    },
  });
}
