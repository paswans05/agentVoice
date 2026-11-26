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

export interface KnowledgeBaseAgentConfig {
  enabled: boolean;
  knowledge_base_id: string | null;
  top_k: number;
  similarity_threshold: number;
  max_context_tokens: number;
  require_sources_for_company_facts: boolean;
  fallback_when_not_found: boolean;
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
  knowledge_base?: KnowledgeBaseAgentConfig;
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
  knowledge_base?: KnowledgeBaseAgentConfig;
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
  knowledge_base?: KnowledgeBaseAgentConfig;
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

export interface SourceCitation {
  document_id: string;
  filename: string;
  page_number?: number | null;
  chunk_id: string;
  score?: number | null;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
  timestamp: string;
  model_id?: string | null;
  duration_ms?: number | null;
  sources?: SourceCitation[];
  grounded?: boolean | null;
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

export type VoiceSessionState =
  | "IDLE"
  | "CONNECTING"
  | "LISTENING"
  | "SPEECH_DETECTED"
  | "TRANSCRIBING"
  | "THINKING"
  | "GENERATING_SPEECH"
  | "SPEAKING"
  | "INTERRUPTED"
  | "ERROR"
  | "COMPLETED";

export interface SpeechProviderHealth {
  provider: string;
  available: boolean;
  is_local: boolean;
  details: string | null;
  error: string | null;
}

export interface SpeechRuntimeHealth {
  stt: SpeechProviderHealth;
  tts: SpeechProviderHealth;
  vad: SpeechProviderHealth;
  checked_at: string;
}

export interface STTModelInfo {
  id: string;
  name: string;
  provider: string;
  languages: string[];
  approximate_size: string;
  min_ram_gb: number;
  license: string;
  installed: boolean;
}

export interface TTSVoiceInfo {
  id: string;
  name: string;
  provider: string;
  language: string;
  sample_rate: number;
  license: string;
  installed: boolean;
}

export interface AudioSettings {
  input_sample_rate: number;
  output_format: "audio/wav" | "pcm_s16le";
  stt_provider: string;
  stt_model: string;
  hinglish_script_mode: "auto" | "original" | "hindi" | "english";
  tts_provider: string;
  default_voice_id: string;
  default_speed: number;
  default_pitch: number;
  vad_threshold: number;
  min_speech_ms: number;
  min_silence_ms: number;
  max_utterance_ms: number;
}

export interface LatencyMetrics {
  vad_ms: number;
  stt_ms: number;
  llm_ttft_ms: number;
  llm_total_ms: number;
  tts_ms: number;
  total_ms: number;
}

export interface VoiceSessionInfo {
  session_id: string;
  agent_id: string;
  conversation_id: string;
  model_id: string;
  state: VoiceSessionState;
  stt_provider: string;
  tts_provider: string;
  voice_id: string;
  created_at: string;
  updated_at: string;
  last_latency: LatencyMetrics | null;
}

export type VoiceWsEvent =
  | { type: "session.state"; state: VoiceSessionState; session_id: string }
  | { type: "transcript.partial"; text: string }
  | { type: "transcript.final"; text: string; language?: string | null; duration_seconds?: number }
  | { type: "response.text"; text: string }
  | { type: "response.interrupted"; session_id: string }
  | { type: "metrics"; data: LatencyMetrics }
  | { type: "error"; message: string };

export type KnowledgeBaseStatus =
  | "EMPTY"
  | "PENDING"
  | "PROCESSING"
  | "INDEXING"
  | "READY"
  | "FAILED"
  | "DISABLED";

export type DocumentStatus = "PENDING" | "PROCESSING" | "INDEXING" | "READY" | "FAILED";

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  agent_ids: string[];
  enabled: boolean;
  status: KnowledgeBaseStatus;
  document_count: number;
  chunk_count: number;
  embedding_model: string;
  last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: DocumentStatus;
  chunk_count: number;
  error_message: string | null;
  extraction_ms: number;
  chunking_ms: number;
  embedding_ms: number;
  created_at: string;
  updated_at: string;
}

export interface RetrievalHit {
  chunk_id: string;
  document_id: string;
  knowledge_base_id: string;
  filename: string;
  page_number: number | null;
  section_title: string | null;
  content: string;
  score: number;
}

export interface RetrievalTestResult {
  query: string;
  hits: RetrievalHit[];
  grounded: boolean;
  retrieval_ms: number;
  answer?: string | null;
}

export interface RAGSettings {
  embedding_provider: string;
  embedding_model: string;
  chunk_size_tokens: number;
  chunk_overlap_tokens: number;
  default_top_k: number;
  similarity_threshold: number;
  max_context_tokens: number;
  max_file_size_mb: number;
}

export type LeadStatus =
  | "NEW"
  | "CONTACTED"
  | "QUALIFIED"
  | "UNQUALIFIED"
  | "INTERESTED"
  | "NOT_INTERESTED"
  | "FOLLOW_UP"
  | "CONVERTED"
  | "LOST"
  | "DO_NOT_CONTACT";

export type LeadPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type ConsentStatus =
  | "UNKNOWN"
  | "PENDING"
  | "GRANTED"
  | "DENIED"
  | "REVOKED"
  | "EXPIRED";

export type ConsentChannel =
  | "PHONE"
  | "SMS"
  | "EMAIL"
  | "WHATSAPP"
  | "WEB"
  | "IN_PERSON"
  | "OTHER";

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  normalized_phone: string | null;
  alternate_phone: string | null;
  company: string;
  job_title: string;
  website: string;
  country: string;
  state: string;
  city: string;
  address: string;
  source: string;
  status: LeadStatus;
  priority: LeadPriority;
  assigned_agent_id: string | null;
  group_ids: string[];
  tags: string[];
  notes: string;
  custom_fields: Record<string, unknown>;
  consent_status: ConsentStatus;
  suppressed: boolean;
  created_at: string;
  updated_at: string;
  last_contacted_at: string | null;
  next_follow_up_at: string | null;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LeadDashboardStats {
  total_leads: number;
  new_leads: number;
  qualified_leads: number;
  interested_leads: number;
  follow_up_leads: number;
  converted_leads: number;
  suppressed_contacts: number;
}

export interface LeadGroup {
  id: string;
  name: string;
  description: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface ConsentRecord {
  id: string;
  lead_id: string;
  consent_status: ConsentStatus;
  consent_type: string;
  purpose: string;
  channel: ConsentChannel;
  source: string;
  captured_at: string | null;
  revoked_at: string | null;
  revocation_reason: string;
  created_at: string;
}

export interface SuppressionRecord {
  id: string;
  lead_id: string | null;
  phone: string | null;
  email: string | null;
  channel: string;
  reason: string;
  source: string;
  created_at: string;
  revoked_at: string | null;
}

export interface LeadActivity {
  activity_id: string;
  lead_id: string;
  activity_type: string;
  description: string;
  actor: string;
  timestamp: string;
}

export interface EligibilityResult {
  lead_id: string;
  channel: ConsentChannel;
  purpose: string;
  eligible: boolean;
  blocked: boolean;
  reason: string;
  applicable_consent_status: ConsentStatus;
  suppression_status: boolean;
}

export interface CSVImportPreviewResponse {
  job_id: string;
  filename: string;
  headers: string[];
  total_rows: number;
  sample_rows: Record<string, string>[];
  suggested_mapping: Record<string, string>;
}

export interface CSVImportResult {
  job_id: string;
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  duplicate_count: number;
  invalid_count: number;
  updated_count: number;
  errors: { row_number: number; message: string }[];
  warnings: string[];
}
