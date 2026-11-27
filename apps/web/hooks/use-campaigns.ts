"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Campaign } from "@agentvoice/shared-types";
import {
  activateCampaign,
  cancelCampaign,
  createCampaign,
  deleteCampaign,
  fetchAllCalls,
  fetchCampaign,
  fetchCampaignAnalytics,
  fetchCampaignCalls,
  fetchCampaignEligibility,
  fetchCampaignJobs,
  fetchCampaignOverview,
  fetchCampaignProgress,
  fetchCampaigns,
  fetchTelephonyProviders,
  pauseCampaign,
  stopCampaign,
  validateCampaign,
} from "@/lib/api-client";

export function useCampaigns() {
  return useQuery({ queryKey: ["campaigns"], queryFn: fetchCampaigns });
}

export function useCampaignOverview() {
  return useQuery({ queryKey: ["campaign-overview"], queryFn: fetchCampaignOverview });
}

export function useCampaign(campaignId: string) {
  return useQuery({
    queryKey: ["campaign", campaignId],
    queryFn: () => fetchCampaign(campaignId),
    enabled: Boolean(campaignId),
  });
}

export function useCampaignEligibility(campaignId: string) {
  return useQuery({
    queryKey: ["campaign-eligibility", campaignId],
    queryFn: () => fetchCampaignEligibility(campaignId),
    enabled: Boolean(campaignId),
  });
}

export function useCampaignProgress(campaignId: string) {
  return useQuery({
    queryKey: ["campaign-progress", campaignId],
    queryFn: () => fetchCampaignProgress(campaignId),
    enabled: Boolean(campaignId),
    refetchInterval: 4000,
  });
}

export function useCampaignJobs(campaignId: string) {
  return useQuery({
    queryKey: ["campaign-jobs", campaignId],
    queryFn: () => fetchCampaignJobs(campaignId),
    enabled: Boolean(campaignId),
  });
}

export function useCampaignCalls(campaignId: string) {
  return useQuery({
    queryKey: ["campaign-calls", campaignId],
    queryFn: () => fetchCampaignCalls(campaignId),
    enabled: Boolean(campaignId),
  });
}

export function useCampaignAnalytics(campaignId: string) {
  return useQuery({
    queryKey: ["campaign-analytics", campaignId],
    queryFn: () => fetchCampaignAnalytics(campaignId),
    enabled: Boolean(campaignId),
  });
}

export function useAllCalls() {
  return useQuery({ queryKey: ["all-calls"], queryFn: fetchAllCalls });
}

export function useTelephonyProviders() {
  return useQuery({ queryKey: ["telephony-providers"], queryFn: fetchTelephonyProviders });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<Campaign>) => createCampaign(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["campaigns"] });
      void qc.invalidateQueries({ queryKey: ["campaign-overview"] });
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => deleteCampaign(campaignId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["campaigns"] });
      void qc.invalidateQueries({ queryKey: ["campaign-overview"] });
    },
  });
}

export function useCampaignControls(campaignId: string) {
  const qc = useQueryClient();
  const inv = () => {
    void qc.invalidateQueries({ queryKey: ["campaign", campaignId] });
    void qc.invalidateQueries({ queryKey: ["campaign-progress", campaignId] });
    void qc.invalidateQueries({ queryKey: ["campaign-jobs", campaignId] });
    void qc.invalidateQueries({ queryKey: ["campaign-calls", campaignId] });
    void qc.invalidateQueries({ queryKey: ["campaign-analytics", campaignId] });
    void qc.invalidateQueries({ queryKey: ["campaigns"] });
    void qc.invalidateQueries({ queryKey: ["campaign-overview"] });
  };
  return {
    validate: useMutation({ mutationFn: () => validateCampaign(campaignId) }),
    activate: useMutation({
      mutationFn: (opts?: { runInline?: boolean; bypassWindow?: boolean }) =>
        activateCampaign(campaignId, opts),
      onSuccess: inv,
    }),
    pause: useMutation({ mutationFn: () => pauseCampaign(campaignId), onSuccess: inv }),
    stop: useMutation({ mutationFn: () => stopCampaign(campaignId), onSuccess: inv }),
    cancel: useMutation({ mutationFn: () => cancelCampaign(campaignId), onSuccess: inv }),
  };
}
