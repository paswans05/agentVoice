import { APP_CONFIG } from "@agentvoice/config";
import type {
  Agent,
  AgentCreatePayload,
  AgentStatus,
  AgentTemplate,
  AgentType,
  AgentUpdatePayload,
  ApiResponse,
  HealthData,
  SystemStatusData,
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
