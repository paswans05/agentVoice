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

export interface ModelConfig {
  provider: string;
  model_id: string;
  temperature: number;
  max_tokens: number;
  context_window_messages: number;
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
  model?: ModelConfig;
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
  model?: ModelConfig;
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
  model?: ModelConfig;
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
  model?: ModelConfig;
}

export type ModelStatus = "AVAILABLE" | "DOWNLOADING" | "INSTALLED" | "ERROR" | "UNKNOWN";

export interface LLMRuntimeHealth {
  provider: string;
  available: boolean;
  endpoint: string;
  version: string | null;
  error: string | null;
  checked_at: string;
}

export interface LLMModelInfo {
  id: string;
  name: string;
  provider: string;
  status: ModelStatus;
  size_bytes: number | null;
  family: string | null;
  parameter_size: string | null;
  quantization: string | null;
  modified_at: string | null;
  is_default: boolean;
}

export interface ModelRecommendation {
  id: string;
  name: string;
  approximate_size: string;
  min_ram_gb: number;
  quantization: string;
  language_notes: string;
  performance_notes: string;
}

export interface ModelPullTask {
  task_id: string;
  model_id: string;
  status: "DOWNLOADING" | "COMPLETED" | "CANCELLED" | "ERROR";
  progress_percent: number;
  completed_bytes: number;
  total_bytes: number;
  status_text: string;
  error: string | null;
  updated_at: string;
}

export interface ModelsOverview {
  runtime: LLMRuntimeHealth;
  installed: LLMModelInfo[];
  default_model_id: string | null;
  recommendations: ModelRecommendation[];
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
  timestamp: string;
  model_id?: string | null;
  duration_ms?: number | null;
}

export interface Conversation {
  id: string;
  agent_id: string;
  model_id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export type StreamEvent =
  | { event: "meta"; conversation_id: string; model_id: string }
  | { event: "delta"; content: string }
  | {
      event: "done";
      conversation_id: string;
      model_id: string;
      duration_ms: number;
      message: ChatMessage;
    }
  | { event: "error"; message: string };
