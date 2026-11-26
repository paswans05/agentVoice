"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  assignKBToAgent,
  createKnowledgeBase,
  deleteKBDocument,
  deleteKnowledgeBase,
  disableKnowledgeBase,
  enableKnowledgeBase,
  fetchKBDocuments,
  fetchKnowledgeBase,
  fetchKnowledgeBases,
  reprocessKBDocument,
  searchKnowledgeBase,
  unassignKBFromAgent,
  uploadKBDocuments,
} from "@/lib/api-client";

export function useKnowledgeBases() {
  return useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: fetchKnowledgeBases,
  });
}

export function useKnowledgeBase(kbId: string) {
  return useQuery({
    queryKey: ["knowledge-base", kbId],
    queryFn: () => fetchKnowledgeBase(kbId),
    enabled: Boolean(kbId),
  });
}

export function useKBDocuments(kbId: string) {
  return useQuery({
    queryKey: ["kb-documents", kbId],
    queryFn: () => fetchKBDocuments(kbId),
    enabled: Boolean(kbId),
  });
}

export function useCreateKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description: string }) => createKnowledgeBase(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useDeleteKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (kbId: string) => deleteKnowledgeBase(kbId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useToggleKnowledgeBase(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (enable: boolean) =>
      enable ? enableKnowledgeBase(kbId) : disableKnowledgeBase(kbId),
    onSuccess: (updated) => {
      qc.setQueryData(["knowledge-base", kbId], updated);
      void qc.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useUploadKBDocuments(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => uploadKBDocuments(kbId, files),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["kb-documents", kbId] });
      void qc.invalidateQueries({ queryKey: ["knowledge-base", kbId] });
      void qc.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useDeleteKBDocument(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => deleteKBDocument(docId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["kb-documents", kbId] });
      void qc.invalidateQueries({ queryKey: ["knowledge-base", kbId] });
      void qc.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useReprocessKBDocument(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => reprocessKBDocument(docId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["kb-documents", kbId] });
      void qc.invalidateQueries({ queryKey: ["knowledge-base", kbId] });
    },
  });
}

export function useAssignKBAgent(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, assign }: { agentId: string; assign: boolean }) =>
      assign ? assignKBToAgent(agentId, kbId) : unassignKBFromAgent(agentId, kbId),
    onSuccess: (updated) => {
      qc.setQueryData(["knowledge-base", kbId], updated);
      void qc.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useSearchKnowledgeBase(kbId: string) {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      searchKnowledgeBase(kbId, query, topK),
  });
}
