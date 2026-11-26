"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ConsentChannel, ConsentStatus, Lead, LeadStatus } from "@agentvoice/shared-types";
import {
  addSuppressionRecord,
  assignAgentToLead,
  bulkDeleteLeads,
  bulkUpdateLeads,
  createLead,
  createLeadGroup,
  deleteLead,
  deleteLeadGroup,
  fetchLead,
  fetchLeadActivities,
  fetchLeadConsent,
  fetchLeadEligibility,
  fetchLeadGroups,
  fetchLeads,
  fetchLeadStats,
  fetchSuppressionList,
  grantLeadConsent,
  revokeLeadConsent,
  revokeSuppressionRecord,
  unassignAgentFromLead,
  updateLead,
  type LeadListFilters,
} from "@/lib/api-client";

export function useLeadStats() {
  return useQuery({ queryKey: ["lead-stats"], queryFn: fetchLeadStats });
}

export function useLeads(filters?: LeadListFilters) {
  return useQuery({ queryKey: ["leads", filters ?? {}], queryFn: () => fetchLeads(filters) });
}

export function useLead(leadId: string) {
  return useQuery({
    queryKey: ["lead", leadId],
    queryFn: () => fetchLead(leadId),
    enabled: Boolean(leadId),
  });
}

export function useLeadConsent(leadId: string) {
  return useQuery({
    queryKey: ["lead-consent", leadId],
    queryFn: () => fetchLeadConsent(leadId),
    enabled: Boolean(leadId),
  });
}

export function useLeadEligibility(leadId: string, channel: ConsentChannel = "PHONE") {
  return useQuery({
    queryKey: ["lead-eligibility", leadId, channel],
    queryFn: () => fetchLeadEligibility(leadId, channel),
    enabled: Boolean(leadId),
  });
}

export function useLeadActivities(leadId: string) {
  return useQuery({
    queryKey: ["lead-activities", leadId],
    queryFn: () => fetchLeadActivities(leadId),
    enabled: Boolean(leadId),
  });
}

export function useLeadGroups() {
  return useQuery({ queryKey: ["lead-groups"], queryFn: fetchLeadGroups });
}

export function useSuppressionList(search?: string) {
  return useQuery({
    queryKey: ["suppression-list", search ?? ""],
    queryFn: () => fetchSuppressionList(search),
  });
}

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<Lead>) => createLead(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leads"] });
      void qc.invalidateQueries({ queryKey: ["lead-stats"] });
    },
  });
}

export function useUpdateLead(leadId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<Lead>) => updateLead(leadId, payload),
    onSuccess: (updated) => {
      qc.setQueryData(["lead", leadId], updated);
      void qc.invalidateQueries({ queryKey: ["leads"] });
      void qc.invalidateQueries({ queryKey: ["lead-stats"] });
      void qc.invalidateQueries({ queryKey: ["lead-activities", leadId] });
    },
  });
}

export function useDeleteLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (leadId: string) => deleteLead(leadId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leads"] });
      void qc.invalidateQueries({ queryKey: ["lead-stats"] });
    },
  });
}

export function useBulkLeadActions() {
  const qc = useQueryClient();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["leads"] });
    void qc.invalidateQueries({ queryKey: ["lead-stats"] });
  };
  return {
    bulkDelete: useMutation({ mutationFn: bulkDeleteLeads, onSuccess: invalidate }),
    bulkUpdate: useMutation({
      mutationFn: (p: { lead_ids: string[]; status?: LeadStatus }) => bulkUpdateLeads(p),
      onSuccess: invalidate,
    }),
  };
}

export function useLeadAgentAssignment(leadId: string) {
  const qc = useQueryClient();
  const inv = () => {
    void qc.invalidateQueries({ queryKey: ["lead", leadId] });
    void qc.invalidateQueries({ queryKey: ["leads"] });
    void qc.invalidateQueries({ queryKey: ["lead-activities", leadId] });
  };
  return {
    assign: useMutation({
      mutationFn: (agentId: string) => assignAgentToLead(leadId, agentId),
      onSuccess: inv,
    }),
    unassign: useMutation({
      mutationFn: () => unassignAgentFromLead(leadId),
      onSuccess: inv,
    }),
  };
}

export function useLeadConsentMutations(leadId: string) {
  const qc = useQueryClient();
  const inv = () => {
    void qc.invalidateQueries({ queryKey: ["lead", leadId] });
    void qc.invalidateQueries({ queryKey: ["lead-consent", leadId] });
    void qc.invalidateQueries({ queryKey: ["lead-eligibility", leadId] });
    void qc.invalidateQueries({ queryKey: ["lead-activities", leadId] });
  };
  return {
    grant: useMutation({
      mutationFn: (p: {
        channel: ConsentChannel;
        purpose: string;
        source: string;
        consent_status?: ConsentStatus;
      }) => grantLeadConsent(leadId, p),
      onSuccess: inv,
    }),
    revoke: useMutation({
      mutationFn: (p: { channel: ConsentChannel; purpose: string; reason: string }) =>
        revokeLeadConsent(leadId, p),
      onSuccess: inv,
    }),
  };
}

export function useGroupMutations() {
  const qc = useQueryClient();
  const inv = () => void qc.invalidateQueries({ queryKey: ["lead-groups"] });
  return {
    create: useMutation({ mutationFn: createLeadGroup, onSuccess: inv }),
    remove: useMutation({ mutationFn: deleteLeadGroup, onSuccess: inv }),
  };
}

export function useSuppressionMutations() {
  const qc = useQueryClient();
  const inv = () => {
    void qc.invalidateQueries({ queryKey: ["suppression-list"] });
    void qc.invalidateQueries({ queryKey: ["leads"] });
    void qc.invalidateQueries({ queryKey: ["lead-stats"] });
  };
  return {
    add: useMutation({ mutationFn: addSuppressionRecord, onSuccess: inv }),
    revoke: useMutation({ mutationFn: revokeSuppressionRecord, onSuccess: inv }),
  };
}
