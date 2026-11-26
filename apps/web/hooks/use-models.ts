"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelModelPull,
  deleteModel,
  fetchModelsOverview,
  fetchPullStatus,
  pullModel,
  refreshModels,
  setDefaultModel,
} from "@/lib/api-client";

export function useModelsOverview() {
  return useQuery({
    queryKey: ["models-overview"],
    queryFn: fetchModelsOverview,
  });
}

export function useRefreshModels() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: refreshModels,
    onSuccess: (data) => {
      qc.setQueryData(["models-overview"], data);
    },
  });
}

export function useSetDefaultModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (modelId: string) => setDefaultModel(modelId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["models-overview"] });
    },
  });
}

export function usePullModel() {
  return useMutation({
    mutationFn: (modelId: string) => pullModel(modelId),
  });
}

export function usePullStatus(taskId: string | null) {
  return useQuery({
    queryKey: ["model-pull", taskId],
    queryFn: () => fetchPullStatus(taskId as string),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "DOWNLOADING" ? 1000 : false;
    },
  });
}

export function useCancelPull() {
  return useMutation({
    mutationFn: (taskId: string) => cancelModelPull(taskId),
  });
}

export function useDeleteModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (modelId: string) => deleteModel(modelId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["models-overview"] });
    },
  });
}
