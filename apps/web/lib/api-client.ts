import { APP_CONFIG } from "@agentvoice/config";
import type {
  Agent,
  AgentCreatePayload,
  AgentStatus,
  AgentTemplate,
  AgentType,
  AgentUpdatePayload,
  ApiResponse,
  AudioSettings,
  Campaign,
  CampaignAnalytics,
  CampaignAnalyticsOverview,
  CampaignCallRecord,
  CampaignEligibilitySummary,
  CampaignJob,
  CampaignProgress,
  CampaignValidationResult,
  CallMetricsSnapshot,
  CallMonitoringSettings,
  CallSession,
  CallSessionStatus,
  ConsentChannel,
  ConsentRecord,
  ConsentStatus,
  Conversation,
  CSVImportPreviewResponse,
  CSVImportResult,
  CustomerPersona,
  DeviceEventRecord,
  EligibilityResult,
  GsmGatewayRecord,
  HealthData,
  InboundRouteRecord,
  KnowledgeBase,
  KnowledgeDocument,
  Lead,
  LeadActivity,
  LeadDashboardStats,
  LeadGroup,
  LeadListResponse,
  LeadPriority,
  LeadStatus,
  LiveCallsStats,
  LLMRuntimeHealth,
  MobileDevice,
  ModelPullTask,
  ModelsOverview,
  NormalizedCallEvent,
  OutboundRouteRecord,
  PairingCodeRecord,
  RAGSettings,
  RetrievalTestResult,
  SipTrunkRecord,
  SpeechRuntimeHealth,
  StreamEvent,
  STTModelInfo,
  SuppressionRecord,
  SystemStatusData,
  TelephonyOverview,
  TelephonyProviderInfo,
  TelephonyProviderRecord,
  TelephonySettings,
  TestingOverviewStats,
  TestRun,
  TestScenario,
  TranscriptSegment,
  TTSVoiceInfo,
  VoiceSessionInfo,
} from "@agentvoice/shared-types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || APP_CONFIG.defaultApiUrl;

export class ApiClientError extends Error {
  public readonly code: string;
  public readonly status: number;

  constructor(message: string, code = "API_ERROR", status = 500) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  let payload: ApiResponse<T>;
  try {
    payload = (await response.json()) as ApiResponse<T>;
  } catch {
    throw new ApiClientError(
      `Invalid JSON response from backend (${response.status})`,
      "INVALID_RESPONSE",
      response.status,
    );
  }

  if (!response.ok || !payload.success || payload.data === null) {
    throw new ApiClientError(
      payload.error?.message ?? `Request failed with status ${response.status}`,
      payload.error?.code ?? "REQUEST_FAILED",
      response.status,
    );
  }

  return payload.data;
}

export function fetchHealth(): Promise<HealthData> {
  return apiFetch<HealthData>("/api/v1/health");
}

export function fetchSystemStatus(): Promise<SystemStatusData> {
  return apiFetch<SystemStatusData>("/api/v1/system/status");
}

export interface AgentListFilters {
  search?: string;
  status?: AgentStatus | "";
  type?: AgentType | "";
}

export function fetchAgents(filters?: AgentListFilters): Promise<Agent[]> {
  const params = new URLSearchParams();
  if (filters?.search?.trim()) params.set("search", filters.search.trim());
  if (filters?.status) params.set("status", filters.status);
  if (filters?.type) params.set("type", filters.type);
  const qs = params.toString();
  return apiFetch<Agent[]>(`/api/v1/agents${qs ? `?${qs}` : ""}`);
}

export function fetchAgent(agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}`);
}

export function fetchAgentTemplates(): Promise<AgentTemplate[]> {
  return apiFetch<AgentTemplate[]>("/api/v1/agents/templates");
}

export function createAgent(payload: AgentCreatePayload): Promise<Agent> {
  return apiFetch<Agent>("/api/v1/agents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAgent(agentId: string, payload: AgentUpdatePayload): Promise<Agent> {
  return apiFetch<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAgent(agentId: string): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/agents/${encodeURIComponent(agentId)}`,
    { method: "DELETE" },
  );
}

export function duplicateAgent(agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}/duplicate`, {
    method: "POST",
  });
}

export function activateAgent(agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}/activate`, {
    method: "POST",
  });
}

export function deactivateAgent(agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}/deactivate`, {
    method: "POST",
  });
}

// --- Phase 3: LLM, Models & Conversations ---

export function fetchLLMHealth(): Promise<LLMRuntimeHealth> {
  return apiFetch<LLMRuntimeHealth>("/api/v1/llm/health");
}

export function fetchModelsOverview(): Promise<ModelsOverview> {
  return apiFetch<ModelsOverview>("/api/v1/models");
}

export function refreshModels(): Promise<ModelsOverview> {
  return apiFetch<ModelsOverview>("/api/v1/models/refresh", { method: "POST" });
}

export function setDefaultModel(modelId: string): Promise<{ default_model_id: string }> {
  return apiFetch<{ default_model_id: string }>("/api/v1/models/default", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId }),
  });
}

export function pullModel(modelId: string): Promise<ModelPullTask> {
  return apiFetch<ModelPullTask>("/api/v1/models/pull", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId }),
  });
}

export function fetchPullStatus(taskId: string): Promise<ModelPullTask> {
  return apiFetch<ModelPullTask>(`/api/v1/models/pull/${encodeURIComponent(taskId)}`);
}

export function cancelModelPull(taskId: string): Promise<ModelPullTask> {
  return apiFetch<ModelPullTask>(`/api/v1/models/pull/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
  });
}

export function deleteModel(modelId: string): Promise<{ deleted: boolean; model_id: string }> {
  return apiFetch<{ deleted: boolean; model_id: string }>(
    `/api/v1/models/${encodeURIComponent(modelId)}`,
    { method: "DELETE" },
  );
}

export function fetchAgentConversations(agentId: string): Promise<Conversation[]> {
  return apiFetch<Conversation[]>(`/api/v1/agents/${encodeURIComponent(agentId)}/conversations`);
}

export function createConversation(
  agentId: string,
  title = "New Conversation",
  modelId?: string,
): Promise<Conversation> {
  return apiFetch<Conversation>(`/api/v1/agents/${encodeURIComponent(agentId)}/conversations`, {
    method: "POST",
    body: JSON.stringify({ title, model_id: modelId ?? null }),
  });
}

export function fetchConversation(conversationId: string): Promise<Conversation> {
  return apiFetch<Conversation>(`/api/v1/conversations/${encodeURIComponent(conversationId)}`);
}

export function deleteConversation(
  conversationId: string,
): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/conversations/${encodeURIComponent(conversationId)}`,
    { method: "DELETE" },
  );
}

export async function streamConversationMessage(
  conversationId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/conversations/${encodeURIComponent(conversationId)}/messages/stream`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, allow_draft_preview: true }),
    signal,
  });

  if (!response.ok || !response.body) {
    let message = `Streaming request failed (${response.status})`;
    try {
      const errJson = (await response.json()) as ApiResponse<null>;
      if (errJson.error?.message) message = errJson.error.message;
    } catch {
      // ignore non-json error body
    }
    throw new ApiClientError(message, "STREAM_FAILED", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        const parsed = JSON.parse(line.slice(6)) as StreamEvent;
        onEvent(parsed);
      } catch {
        // ignore malformed SSE chunk
      }
    }
  }
}

// --- Phase 4: Speech & Real-Time Voice ---

export function fetchSpeechHealth(): Promise<SpeechRuntimeHealth> {
  return apiFetch<SpeechRuntimeHealth>("/api/v1/speech/health");
}

export function fetchSTTModels(): Promise<STTModelInfo[]> {
  return apiFetch<STTModelInfo[]>("/api/v1/speech/stt/models");
}

export function fetchTTSVoices(): Promise<TTSVoiceInfo[]> {
  return apiFetch<TTSVoiceInfo[]>("/api/v1/speech/tts/voices");
}

export function fetchAudioSettings(): Promise<AudioSettings> {
  return apiFetch<AudioSettings>("/api/v1/speech/settings");
}

export function updateAudioSettings(payload: AudioSettings): Promise<AudioSettings> {
  return apiFetch<AudioSettings>("/api/v1/speech/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function createVoiceSession(
  agentId: string,
  conversationId?: string | null,
): Promise<VoiceSessionInfo> {
  return apiFetch<VoiceSessionInfo>("/api/v1/voice/sessions", {
    method: "POST",
    body: JSON.stringify({
      agent_id: agentId,
      conversation_id: conversationId ?? null,
      allow_draft_preview: true,
    }),
  });
}

export function deleteVoiceSession(
  sessionId: string,
): Promise<{ deleted: boolean; session_id: string }> {
  return apiFetch<{ deleted: boolean; session_id: string }>(
    `/api/v1/voice/sessions/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

export function getVoiceWebSocketUrl(sessionId: string): string {
  const wsBase = API_BASE_URL.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
  return `${wsBase}/api/v1/voice/sessions/${encodeURIComponent(sessionId)}/stream`;
}

// --- Phase 5: Knowledge Base & RAG ---

export function fetchKnowledgeBases(): Promise<KnowledgeBase[]> {
  return apiFetch<KnowledgeBase[]>("/api/v1/knowledge-bases");
}

export function createKnowledgeBase(payload: {
  name: string;
  description: string;
  agent_ids?: string[];
}): Promise<KnowledgeBase> {
  return apiFetch<KnowledgeBase>("/api/v1/knowledge-bases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchKnowledgeBase(kbId: string): Promise<KnowledgeBase> {
  return apiFetch<KnowledgeBase>(`/api/v1/knowledge-bases/${encodeURIComponent(kbId)}`);
}

export function deleteKnowledgeBase(kbId: string): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/knowledge-bases/${encodeURIComponent(kbId)}`,
    { method: "DELETE" },
  );
}

export function enableKnowledgeBase(kbId: string): Promise<KnowledgeBase> {
  return apiFetch<KnowledgeBase>(`/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/enable`, {
    method: "POST",
  });
}

export function disableKnowledgeBase(kbId: string): Promise<KnowledgeBase> {
  return apiFetch<KnowledgeBase>(`/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/disable`, {
    method: "POST",
  });
}

export function fetchKBDocuments(kbId: string): Promise<KnowledgeDocument[]> {
  return apiFetch<KnowledgeDocument[]>(
    `/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/documents`,
  );
}

export async function uploadKBDocuments(
  kbId: string,
  files: File[],
): Promise<KnowledgeDocument[]> {
  const formData = new FormData();
  for (const f of files) {
    formData.append("files", f);
  }
  const url = `${API_BASE_URL}/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/documents`;
  const response = await fetch(url, { method: "POST", body: formData });
  const payload = (await response.json()) as ApiResponse<KnowledgeDocument[]>;
  if (!response.ok || !payload.success || !payload.data) {
    throw new ApiClientError(
      payload.error?.message ?? `Upload failed (${response.status})`,
      payload.error?.code ?? "UPLOAD_FAILED",
      response.status,
    );
  }
  return payload.data;
}

export function deleteKBDocument(docId: string): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/documents/${encodeURIComponent(docId)}`,
    { method: "DELETE" },
  );
}

export function reprocessKBDocument(docId: string): Promise<KnowledgeDocument> {
  return apiFetch<KnowledgeDocument>(
    `/api/v1/documents/${encodeURIComponent(docId)}/reprocess`,
    { method: "POST" },
  );
}

export function assignKBToAgent(agentId: string, kbId: string): Promise<KnowledgeBase> {
  return apiFetch<KnowledgeBase>(
    `/api/v1/agents/${encodeURIComponent(agentId)}/knowledge-bases/${encodeURIComponent(kbId)}`,
    { method: "POST" },
  );
}

export function unassignKBFromAgent(agentId: string, kbId: string): Promise<KnowledgeBase> {
  return apiFetch<KnowledgeBase>(
    `/api/v1/agents/${encodeURIComponent(agentId)}/knowledge-bases/${encodeURIComponent(kbId)}`,
    { method: "DELETE" },
  );
}

export function searchKnowledgeBase(
  kbId: string,
  query: string,
  topK = 5,
  similarityThreshold = 0.25,
): Promise<RetrievalTestResult> {
  return apiFetch<RetrievalTestResult>(
    `/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/search`,
    {
      method: "POST",
      body: JSON.stringify({
        query,
        top_k: topK,
        similarity_threshold: similarityThreshold,
      }),
    },
  );
}

export function fetchRAGSettings(): Promise<RAGSettings> {
  return apiFetch<RAGSettings>("/api/v1/rag/settings");
}

export function updateRAGSettings(payload: RAGSettings): Promise<RAGSettings> {
  return apiFetch<RAGSettings>("/api/v1/rag/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

// --- Phase 7: Leads Management ---

export interface LeadListFilters {
  search?: string;
  status?: LeadStatus | "";
  priority?: LeadPriority | "";
  assigned_agent_id?: string;
  group_id?: string;
  consent_status?: ConsentStatus | "";
  page?: number;
  page_size?: number;
}

export function fetchLeadStats(): Promise<LeadDashboardStats> {
  return apiFetch<LeadDashboardStats>("/api/v1/leads/stats");
}

export function fetchLeads(filters?: LeadListFilters): Promise<LeadListResponse> {
  const params = new URLSearchParams();
  if (filters?.search?.trim()) params.set("search", filters.search.trim());
  if (filters?.status) params.set("status", filters.status);
  if (filters?.priority) params.set("priority", filters.priority);
  if (filters?.assigned_agent_id) params.set("assigned_agent_id", filters.assigned_agent_id);
  if (filters?.group_id) params.set("group_id", filters.group_id);
  if (filters?.consent_status) params.set("consent_status", filters.consent_status);
  if (filters?.page) params.set("page", String(filters.page));
  if (filters?.page_size) params.set("page_size", String(filters.page_size));
  const qs = params.toString();
  return apiFetch<LeadListResponse>(`/api/v1/leads${qs ? `?${qs}` : ""}`);
}

export function fetchLead(leadId: string): Promise<Lead> {
  return apiFetch<Lead>(`/api/v1/leads/${encodeURIComponent(leadId)}`);
}

export function createLead(payload: Partial<Lead>): Promise<Lead> {
  return apiFetch<Lead>("/api/v1/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateLead(leadId: string, payload: Partial<Lead>): Promise<Lead> {
  return apiFetch<Lead>(`/api/v1/leads/${encodeURIComponent(leadId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteLead(leadId: string): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/leads/${encodeURIComponent(leadId)}`,
    { method: "DELETE" },
  );
}

export function bulkDeleteLeads(leadIds: string[]): Promise<{ deleted_count: number }> {
  return apiFetch<{ deleted_count: number }>("/api/v1/leads/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ lead_ids: leadIds }),
  });
}

export function bulkUpdateLeads(payload: {
  lead_ids: string[];
  status?: LeadStatus;
  priority?: LeadPriority;
}): Promise<{ updated_count: number }> {
  return apiFetch<{ updated_count: number }>("/api/v1/leads/bulk-update", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function assignAgentToLead(leadId: string, agentId: string): Promise<Lead> {
  return apiFetch<Lead>(
    `/api/v1/leads/${encodeURIComponent(leadId)}/assign-agent?agent_id=${encodeURIComponent(agentId)}`,
    { method: "POST" },
  );
}

export function unassignAgentFromLead(leadId: string): Promise<Lead> {
  return apiFetch<Lead>(`/api/v1/leads/${encodeURIComponent(leadId)}/assign-agent`, {
    method: "DELETE",
  });
}

export function fetchLeadConsent(leadId: string): Promise<ConsentRecord[]> {
  return apiFetch<ConsentRecord[]>(`/api/v1/leads/${encodeURIComponent(leadId)}/consent`);
}

export function grantLeadConsent(
  leadId: string,
  payload: { channel: ConsentChannel; purpose: string; source: string; consent_status?: ConsentStatus },
): Promise<ConsentRecord> {
  return apiFetch<ConsentRecord>(`/api/v1/leads/${encodeURIComponent(leadId)}/consent`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeLeadConsent(
  leadId: string,
  payload: { channel: ConsentChannel; purpose: string; reason: string },
): Promise<ConsentRecord> {
  return apiFetch<ConsentRecord>(`/api/v1/leads/${encodeURIComponent(leadId)}/consent/revoke`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchLeadEligibility(
  leadId: string,
  channel: ConsentChannel = "PHONE",
  purpose = "PRODUCT_INFORMATION",
): Promise<EligibilityResult> {
  return apiFetch<EligibilityResult>(
    `/api/v1/leads/${encodeURIComponent(leadId)}/eligibility?channel=${channel}&purpose=${encodeURIComponent(purpose)}`,
  );
}

export function fetchLeadActivities(leadId: string): Promise<LeadActivity[]> {
  return apiFetch<LeadActivity[]>(`/api/v1/leads/${encodeURIComponent(leadId)}/activities`);
}

export function fetchLeadGroups(): Promise<LeadGroup[]> {
  return apiFetch<LeadGroup[]>("/api/v1/lead-groups");
}

export function createLeadGroup(payload: {
  name: string;
  description: string;
  color?: string;
}): Promise<LeadGroup> {
  return apiFetch<LeadGroup>("/api/v1/lead-groups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteLeadGroup(groupId: string): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/lead-groups/${encodeURIComponent(groupId)}`,
    { method: "DELETE" },
  );
}

export function fetchSuppressionList(search?: string): Promise<SuppressionRecord[]> {
  const qs = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
  return apiFetch<SuppressionRecord[]>(`/api/v1/suppression-list${qs}`);
}

export function addSuppressionRecord(payload: {
  lead_id?: string;
  phone?: string;
  email?: string;
  reason: string;
}): Promise<SuppressionRecord> {
  return apiFetch<SuppressionRecord>("/api/v1/suppression-list", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeSuppressionRecord(recordId: string): Promise<SuppressionRecord> {
  return apiFetch<SuppressionRecord>(
    `/api/v1/suppression-list/${encodeURIComponent(recordId)}`,
    { method: "DELETE" },
  );
}

export async function previewCSVImport(file: File): Promise<CSVImportPreviewResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/api/v1/leads/import/preview`, {
    method: "POST",
    body: form,
  });
  const payload = (await res.json()) as ApiResponse<CSVImportPreviewResponse>;
  if (!res.ok || !payload.success || !payload.data) {
    throw new ApiClientError(payload.error?.message ?? "CSV preview failed", "CSV_ERROR", res.status);
  }
  return payload.data;
}

export function executeCSVImport(payload: {
  job_id: string;
  column_mapping: Record<string, string>;
  duplicate_strategy: "SKIP" | "UPDATE_EXISTING" | "IMPORT_AS_NEW";
  match_strategy: "EMAIL" | "PHONE" | "EMAIL_OR_PHONE";
}): Promise<CSVImportResult> {
  return apiFetch<CSVImportResult>("/api/v1/leads/import/execute", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function exportLeadsCSV(payload: {
  lead_ids?: string[];
  status?: LeadStatus;
  include_consent?: boolean;
}): Promise<Blob> {
  const res = await fetch(`${API_BASE_URL}/api/v1/leads/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new ApiClientError("Failed to export CSV", "EXPORT_ERROR", res.status);
  }
  return res.blob();
}

// --- Phase 8: Campaigns & Telephony Status ---

export function fetchCampaigns(): Promise<Campaign[]> {
  return apiFetch<Campaign[]>("/api/v1/campaigns");
}

export function fetchCampaign(campaignId: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/api/v1/campaigns/${encodeURIComponent(campaignId)}`);
}

export function createCampaign(payload: Partial<Campaign>): Promise<Campaign> {
  return apiFetch<Campaign>("/api/v1/campaigns", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteCampaign(campaignId: string): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}`,
    { method: "DELETE" },
  );
}

export function validateCampaign(campaignId: string): Promise<CampaignValidationResult> {
  return apiFetch<CampaignValidationResult>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}/validate`,
    { method: "POST" },
  );
}

export function activateCampaign(
  campaignId: string,
  options?: { runInline?: boolean; bypassWindow?: boolean },
): Promise<Campaign> {
  const qs = new URLSearchParams();
  if (options?.runInline) qs.set("run_inline", "true");
  if (options?.bypassWindow) qs.set("bypass_window", "true");
  const q = qs.toString();
  return apiFetch<Campaign>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}/activate${q ? `?${q}` : ""}`,
    { method: "POST" },
  );
}

export function pauseCampaign(campaignId: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/api/v1/campaigns/${encodeURIComponent(campaignId)}/pause`, {
    method: "POST",
  });
}

export function stopCampaign(campaignId: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/api/v1/campaigns/${encodeURIComponent(campaignId)}/stop`, {
    method: "POST",
  });
}

export function cancelCampaign(campaignId: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/api/v1/campaigns/${encodeURIComponent(campaignId)}/cancel`, {
    method: "POST",
  });
}

export function fetchCampaignEligibility(campaignId: string): Promise<CampaignEligibilitySummary> {
  return apiFetch<CampaignEligibilitySummary>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}/leads`,
  );
}

export function fetchCampaignProgress(campaignId: string): Promise<CampaignProgress> {
  return apiFetch<CampaignProgress>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}/progress`,
  );
}

export function fetchCampaignJobs(campaignId: string): Promise<CampaignJob[]> {
  return apiFetch<CampaignJob[]>(`/api/v1/campaigns/${encodeURIComponent(campaignId)}/jobs`);
}

export function fetchCampaignCalls(campaignId: string): Promise<CampaignCallRecord[]> {
  return apiFetch<CampaignCallRecord[]>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}/calls`,
  );
}

export function fetchCampaignAnalytics(campaignId: string): Promise<CampaignAnalytics> {
  return apiFetch<CampaignAnalytics>(
    `/api/v1/campaigns/${encodeURIComponent(campaignId)}/analytics`,
  );
}

export function fetchCampaignOverview(): Promise<CampaignAnalyticsOverview> {
  return apiFetch<CampaignAnalyticsOverview>("/api/v1/campaigns/analytics/overview");
}

export function fetchAllCalls(): Promise<CampaignCallRecord[]> {
  return apiFetch<CampaignCallRecord[]>("/api/v1/calls");
}

export function fetchTelephonyProviders(): Promise<TelephonyProviderInfo[]> {
  return apiFetch<TelephonyProviderInfo[]>("/api/v1/telephony/providers");
}

// --- Phase 9: Live Calls & Real-Time Monitoring ---

export interface LiveCallsFilter {
  active_only?: boolean;
  status?: CallSessionStatus | "";
  campaign_id?: string;
  agent_id?: string;
  search?: string;
  limit?: number;
}

export function fetchLiveCalls(filters: LiveCallsFilter = {}): Promise<CallSession[]> {
  const params = new URLSearchParams();
  if (filters.active_only !== undefined) params.set("active_only", String(filters.active_only));
  if (filters.status) params.set("status", filters.status);
  if (filters.campaign_id) params.set("campaign_id", filters.campaign_id);
  if (filters.agent_id) params.set("agent_id", filters.agent_id);
  if (filters.search) params.set("search", filters.search);
  if (filters.limit) params.set("limit", String(filters.limit));
  const qs = params.toString();
  return apiFetch<CallSession[]>(`/api/v1/live-calls${qs ? `?${qs}` : ""}`);
}

export function fetchLiveCallsStats(): Promise<LiveCallsStats> {
  return apiFetch<LiveCallsStats>("/api/v1/live-calls/stats");
}

export function fetchLiveCallDetail(callId: string): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/v1/live-calls/${encodeURIComponent(callId)}`);
}

export function fetchCallEvents(callId: string): Promise<NormalizedCallEvent[]> {
  return apiFetch<NormalizedCallEvent[]>(
    `/api/v1/live-calls/${encodeURIComponent(callId)}/events`,
  );
}

export function fetchCallTranscript(callId: string, query?: string): Promise<TranscriptSegment[]> {
  const qs = query && query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return apiFetch<TranscriptSegment[]>(
    `/api/v1/live-calls/${encodeURIComponent(callId)}/transcript${qs}`,
  );
}

export function fetchCallMetrics(callId: string): Promise<CallMetricsSnapshot | null> {
  return apiFetch<CallMetricsSnapshot | null>(
    `/api/v1/live-calls/${encodeURIComponent(callId)}/metrics`,
  );
}

export function terminateLiveCall(callId: string, reason?: string): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/v1/live-calls/${encodeURIComponent(callId)}/terminate`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? "Terminated by operator" }),
  });
}

export function holdLiveCall(callId: string): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/v1/live-calls/${encodeURIComponent(callId)}/hold`, {
    method: "POST",
  });
}

export function resumeLiveCall(callId: string): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/v1/live-calls/${encodeURIComponent(callId)}/resume`, {
    method: "POST",
  });
}

export function transferLiveCall(
  callId: string,
  destination: string,
  reason?: string,
): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/v1/live-calls/${encodeURIComponent(callId)}/transfer`, {
    method: "POST",
    body: JSON.stringify({ destination, reason: reason ?? "Operator transfer" }),
  });
}

export function flagLiveCall(callId: string, reason: string): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/v1/live-calls/${encodeURIComponent(callId)}/flag`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function fetchCallMonitoringSettings(): Promise<CallMonitoringSettings> {
  return apiFetch<CallMonitoringSettings>("/api/v1/live-calls/settings");
}

export function updateCallMonitoringSettings(
  payload: CallMonitoringSettings,
): Promise<CallMonitoringSettings> {
  return apiFetch<CallMonitoringSettings>("/api/v1/live-calls/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getLiveCallsWebSocketUrl(): string {
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}/api/v1/live-calls/ws`;
}

// --- Phase 10: Telephony Integration ---

export function fetchTelephonyOverview(): Promise<TelephonyOverview> {
  return apiFetch<TelephonyOverview>("/api/v1/telephony/overview");
}

export function fetchTelephonyProviderRecords(): Promise<TelephonyProviderRecord[]> {
  return apiFetch<TelephonyProviderRecord[]>("/api/v1/telephony/providers");
}

export function createTelephonyProvider(
  payload: Record<string, unknown>,
): Promise<TelephonyProviderRecord> {
  return apiFetch<TelephonyProviderRecord>("/api/v1/telephony/providers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testTelephonyProvider(providerId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/v1/telephony/providers/${encodeURIComponent(providerId)}/test`,
    { method: "POST" },
  );
}

export function deleteTelephonyProvider(providerId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(
    `/api/v1/telephony/providers/${encodeURIComponent(providerId)}`,
    { method: "DELETE" },
  );
}

export function fetchSipTrunks(): Promise<SipTrunkRecord[]> {
  return apiFetch<SipTrunkRecord[]>("/api/v1/telephony/trunks");
}

export function createSipTrunk(payload: Record<string, unknown>): Promise<SipTrunkRecord> {
  return apiFetch<SipTrunkRecord>("/api/v1/telephony/trunks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testSipTrunk(trunkId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/v1/telephony/trunks/${encodeURIComponent(trunkId)}/test`,
    { method: "POST" },
  );
}

export function deleteSipTrunk(trunkId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/api/v1/telephony/trunks/${encodeURIComponent(trunkId)}`, {
    method: "DELETE",
  });
}

export function fetchInboundRoutes(): Promise<InboundRouteRecord[]> {
  return apiFetch<InboundRouteRecord[]>("/api/v1/telephony/inbound-routes");
}

export function createInboundRoute(payload: Record<string, unknown>): Promise<InboundRouteRecord> {
  return apiFetch<InboundRouteRecord>("/api/v1/telephony/inbound-routes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteInboundRoute(routeId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(
    `/api/v1/telephony/inbound-routes/${encodeURIComponent(routeId)}`,
    { method: "DELETE" },
  );
}

export function fetchOutboundRoutes(): Promise<OutboundRouteRecord[]> {
  return apiFetch<OutboundRouteRecord[]>("/api/v1/telephony/outbound-routes");
}

export function createOutboundRoute(
  payload: Record<string, unknown>,
): Promise<OutboundRouteRecord> {
  return apiFetch<OutboundRouteRecord>("/api/v1/telephony/outbound-routes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteOutboundRoute(routeId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(
    `/api/v1/telephony/outbound-routes/${encodeURIComponent(routeId)}`,
    { method: "DELETE" },
  );
}

export function fetchGsmGateways(): Promise<GsmGatewayRecord[]> {
  return apiFetch<GsmGatewayRecord[]>("/api/v1/telephony/gateways");
}

export function createGsmGateway(payload: Record<string, unknown>): Promise<GsmGatewayRecord> {
  return apiFetch<GsmGatewayRecord>("/api/v1/telephony/gateways", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testGsmGateway(gatewayId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/v1/telephony/gateways/${encodeURIComponent(gatewayId)}/test`,
    { method: "POST" },
  );
}

export function deleteGsmGateway(gatewayId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(
    `/api/v1/telephony/gateways/${encodeURIComponent(gatewayId)}`,
    { method: "DELETE" },
  );
}

export function fetchTelephonySettings(): Promise<TelephonySettings> {
  return apiFetch<TelephonySettings>("/api/v1/telephony/settings");
}

export function updateTelephonySettings(payload: TelephonySettings): Promise<TelephonySettings> {
  return apiFetch<TelephonySettings>("/api/v1/telephony/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

// --- End-to-End Testing Lab & AI Client Simulator ---

export function fetchTestingStatus(): Promise<TestingOverviewStats> {
  return apiFetch<TestingOverviewStats>("/api/v1/testing/status");
}

export function fetchTestingPersonas(): Promise<CustomerPersona[]> {
  return apiFetch<CustomerPersona[]>("/api/v1/testing/personas");
}

export function createTestingPersona(payload: Record<string, unknown>): Promise<CustomerPersona> {
  return apiFetch<CustomerPersona>("/api/v1/testing/personas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchTestingScenarios(): Promise<TestScenario[]> {
  return apiFetch<TestScenario[]>("/api/v1/testing/scenarios");
}

export function createTestingScenario(payload: Record<string, unknown>): Promise<TestScenario> {
  return apiFetch<TestScenario>("/api/v1/testing/scenarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteTestingScenario(scenarioId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(
    `/api/v1/testing/scenarios/${encodeURIComponent(scenarioId)}`,
    { method: "DELETE" },
  );
}

export function fetchTestRuns(): Promise<TestRun[]> {
  return apiFetch<TestRun[]>("/api/v1/testing/runs");
}

export function runTestSimulation(payload: {
  agent_id: string;
  persona_id: string;
  scenario_id?: string | null;
  voice_enabled?: boolean;
  max_turns?: number;
}): Promise<TestRun> {
  return apiFetch<TestRun>("/api/v1/testing/simulate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rerunFailedTest(runId: string): Promise<TestRun> {
  return apiFetch<TestRun>(`/api/v1/testing/runs/${encodeURIComponent(runId)}/rerun-failed`, {
    method: "POST",
  });
}

export function deleteTestRun(runId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/api/v1/testing/runs/${encodeURIComponent(runId)}`, {
    method: "DELETE",
  });
}

export function runKbSuiteTest(payload: {
  agent_id: string;
  questions?: string[];
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/v1/testing/kb-tests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runTelephonySuiteTest(payload: {
  provider_id: string;
  mode: "dry_run" | "real_test_call";
  agent_id?: string;
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/v1/testing/telephony-tests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runPerformanceSuiteTest(payload: {
  agent_id: string;
  concurrency: number;
  iterations: number;
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/v1/testing/performance-tests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runFailureRecoverySuiteTest(payload: {
  agent_id: string;
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/v1/testing/failure-recovery-tests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runTestingAssistant(payload: {
  agent_id: string;
  instruction: string;
  execute: boolean;
  voice_enabled?: boolean;
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/v1/testing/assistant", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTestReportExportUrl(runId: string, format: "json" | "csv" | "markdown"): string {
  return `${API_BASE_URL}/api/v1/testing/reports/${encodeURIComponent(runId)}?format=${format}`;
}

// --- Android & iPhone Device Gateway ---

export function fetchMobileDevices(): Promise<MobileDevice[]> {
  return apiFetch<MobileDevice[]>("/api/v1/devices");
}

export function fetchMobileDevice(deviceId: string): Promise<MobileDevice> {
  return apiFetch<MobileDevice>(`/api/v1/devices/${encodeURIComponent(deviceId)}`);
}

export function createDevicePairingCode(payload: {
  platform: "android" | "ios";
  account_id?: string;
  ttl_seconds?: number;
}): Promise<PairingCodeRecord> {
  return apiFetch<PairingCodeRecord>("/api/v1/devices/pairing-codes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeMobileDevice(deviceId: string): Promise<MobileDevice> {
  return apiFetch<MobileDevice>(`/api/v1/devices/${encodeURIComponent(deviceId)}/revoke`, {
    method: "POST",
  });
}

export function deleteMobileDevice(deviceId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/api/v1/devices/${encodeURIComponent(deviceId)}`, {
    method: "DELETE",
  });
}

export function fetchDeviceEvents(deviceId: string): Promise<DeviceEventRecord[]> {
  return apiFetch<DeviceEventRecord[]>(`/api/v1/devices/${encodeURIComponent(deviceId)}/events`);
}

export function sendDeviceCommand(
  deviceId: string,
  command_type: string,
  payload: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/v1/devices/${encodeURIComponent(deviceId)}/commands`,
    {
      method: "POST",
      body: JSON.stringify({ command_type, payload }),
    },
  );
}
