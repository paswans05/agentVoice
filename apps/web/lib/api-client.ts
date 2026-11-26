import { APP_CONFIG } from "@agentvoice/config";
import type { ApiResponse, HealthData, SystemStatusData } from "@agentvoice/shared-types";

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
