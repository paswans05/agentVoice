export interface ApiMeta {
  timestamp: string;
  request_id?: string | null;
  version: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: ApiMeta;
}

export type ServiceHealthState = "healthy" | "degraded" | "unavailable";

export interface StorageHealthInfo {
  backend: "json" | "sqlite" | "postgresql";
  status: ServiceHealthState;
  data_dir: string;
  writable: boolean;
}

export interface HealthData {
  status: ServiceHealthState;
  service: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  storage: StorageHealthInfo;
}

export interface SystemResources {
  cpu_percent: number | null;
  memory_total_mb: number | null;
  memory_used_mb: number | null;
  memory_percent: number | null;
  platform: string;
  python_version: string;
}

export interface SystemStatusData {
  app_name: string;
  tagline: string;
  version: string;
  environment: string;
  storage_backend: string;
  offline_ready: boolean;
  external_ai_required: boolean;
  resources: SystemResources;
  phases: {
    current_phase: number;
    phase_name: string;
  };
}
