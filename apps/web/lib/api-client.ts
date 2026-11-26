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
  Conversation,
  HealthData,
  LLMRuntimeHealth,
  ModelPullTask,
  ModelsOverview,
  SpeechRuntimeHealth,
  StreamEvent,
  STTModelInfo,
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
