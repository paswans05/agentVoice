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
  ConsentChannel,
  ConsentRecord,
  ConsentStatus,
  Conversation,
  CSVImportPreviewResponse,
  CSVImportResult,
  EligibilityResult,
  HealthData,
  KnowledgeBase,
  KnowledgeDocument,
  Lead,
  LeadActivity,
  LeadDashboardStats,
  LeadGroup,
  LeadListResponse,
  LeadPriority,
  LeadStatus,
  LLMRuntimeHealth,
  ModelPullTask,
  ModelsOverview,
  RAGSettings,
  RetrievalTestResult,
  SpeechRuntimeHealth,
  StreamEvent,
  STTModelInfo,
  SuppressionRecord,
  SystemStatusData,
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
