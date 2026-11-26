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

export type AgentStatus = "DRAFT" | "ACTIVE" | "INACTIVE";

export type AgentType =
  | "SALES"
  | "CUSTOMER_SUPPORT"
  | "LEAD_QUALIFICATION"
  | "APPOINTMENT_BOOKING"
  | "GENERAL_ASSISTANT"
  | "CUSTOM";

export type PersonalityTone =
  | "FRIENDLY"
  | "PROFESSIONAL"
  | "FORMAL"
  | "CASUAL"
  | "CONFIDENT"
  | "EMPATHETIC"
  | "CUSTOM";

export type LanguageResponseMode = "AUTO" | "PRIMARY" | "FIXED";

export type SupportedLocale = "hi-IN" | "en-IN";

export interface PersonalityConfig {
  tone: PersonalityTone;
  traits: string[];
  custom_instructions: string;
}

export interface InstructionConfig {
  system_prompt: string;
  greeting: string;
  additional_rules: string[];
}

export interface LanguageConfig {
  primary_language: SupportedLocale;
  supported_languages: SupportedLocale[];
  hinglish_enabled: boolean;
  response_mode: LanguageResponseMode;
}

export interface VoiceConfig {
  provider: string;
  voice_id: string;
  speed: number;
  pitch: number;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  avatar: string;
  type: AgentType;
  status: AgentStatus;
  personality: PersonalityConfig;
  instructions: InstructionConfig;
  language: LanguageConfig;
  voice: VoiceConfig;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface AgentCreatePayload {
  name: string;
  description: string;
  avatar: string;
  type: AgentType;
  template_id?: string | null;
  personality: PersonalityConfig;
  instructions: InstructionConfig;
  language: LanguageConfig;
  voice: VoiceConfig;
}

export interface AgentUpdatePayload {
  name: string;
  description: string;
  avatar: string;
  type: AgentType;
  personality: PersonalityConfig;
  instructions: InstructionConfig;
  language: LanguageConfig;
  voice: VoiceConfig;
}

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  avatar: string;
  type: AgentType;
  personality: PersonalityConfig;
  instructions: InstructionConfig;
  language: LanguageConfig;
  voice: VoiceConfig;
}
