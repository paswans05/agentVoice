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

export type CampaignType =
  | "SALES"
  | "LEAD_QUALIFICATION"
  | "APPOINTMENT_BOOKING"
  | "CUSTOMER_FOLLOW_UP"
  | "PRODUCT_INFORMATION"
  | "CUSTOM";

export type CampaignStatus =
  | "DRAFT"
  | "VALIDATING"
  | "READY"
  | "SCHEDULED"
  | "RUNNING"
  | "PAUSED"
  | "STOPPING"
  | "STOPPED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type CampaignLeadStatus =
  | "PENDING"
  | "ELIGIBILITY_CHECK"
  | "QUEUED"
  | "INITIATING"
  | "RINGING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "NO_ANSWER"
  | "BUSY"
  | "FAILED"
  | "SKIPPED"
  | "RETRY_SCHEDULED"
  | "EXHAUSTED"
  | "DO_NOT_CONTACT";

export type CallOutcome =
  | "INTERESTED"
  | "NOT_INTERESTED"
  | "CALLBACK_REQUESTED"
  | "APPOINTMENT_BOOKED"
  | "NEEDS_HUMAN"
  | "INFORMATION_REQUESTED"
  | "NO_ANSWER"
  | "BUSY"
  | "WRONG_NUMBER"
  | "DO_NOT_CALL"
  | "FAILED";

export interface Campaign {
  id: string;
  name: string;
  description: string;
  notes: string;
  campaign_type: CampaignType;
  status: CampaignStatus;
  agent_id: string;
  knowledge_base_id: string | null;
  calling_purpose: string;
  lead_group_ids: string[];
  selected_lead_ids: string[];
  timezone: string;
  calling_days: number[];
  start_date: string | null;
  end_date: string | null;
  start_time: string;
  end_time: string;
  maximum_calls: number;
  maximum_concurrent_calls: number;
  maximum_attempts_per_lead: number;
  retry_interval_minutes: number;
  minimum_interval_between_attempts_minutes: number;
  dry_run: boolean;
  telephony_provider: string;
  recording_enabled: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  paused_at: string | null;
  completed_at: string | null;
}

export interface CampaignJob {
  id: string;
  idempotency_key: string;
  campaign_id: string;
  lead_id: string;
  attempt_number: number;
  status: CampaignLeadStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignCallRecord {
  call_id: string;
  campaign_id: string;
  lead_id: string;
  agent_id: string;
  attempt_id: string;
  provider_id: string;
  provider_call_id: string | null;
  is_dry_run: boolean;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  outcome: CallOutcome;
  summary: string;
}

export interface CampaignEligibilitySummary {
  campaign_id: string;
  total_selected: number;
  eligible_count: number;
  ineligible_count: number;
  suppressed_count: number;
  unknown_consent_count: number;
  invalid_phone_count: number;
}

export interface CampaignValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  eligibility: CampaignEligibilitySummary | null;
}

export interface CampaignProgress {
  campaign_id: string;
  status: CampaignStatus;
  dry_run: boolean;
  total_jobs: number;
  pending_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  skipped_jobs: number;
  retry_scheduled_jobs: number;
}

export interface CampaignAnalytics {
  campaign_id: string;
  total_selected_leads: number;
  eligible_leads: number;
  ineligible_leads: number;
  queued_leads: number;
  real_calls_initiated: number;
  real_calls_completed: number;
  real_calls_failed: number;
  dry_run_calls_simulated: number;
  no_answer_count: number;
  busy_count: number;
  interested_count: number;
  not_interested_count: number;
  callback_requests: number;
  appointments_booked: number;
  average_real_duration_seconds: number;
  completion_rate_percent: number;
}

export interface CampaignAnalyticsOverview {
  total_campaigns: number;
  draft_campaigns: number;
  scheduled_campaigns: number;
  running_campaigns: number;
  paused_campaigns: number;
  completed_campaigns: number;
  failed_campaigns: number;
  total_real_calls: number;
  total_dry_run_calls: number;
}

export interface TelephonyProviderInfo {
  id: string;
  name: string;
  supports_real_calls: boolean;
  configured: boolean;
  status: string;
  message: string;
}

// --- Phase 9: Live Calls & Real-Time Monitoring ---

export type CallSessionType = "BROWSER" | "TELEPHONY" | "INTERNAL_TEST";

export type CallDirection = "INBOUND" | "OUTBOUND";

export type CallSessionStatus =
  | "CREATED"
  | "INITIATING"
  | "RINGING"
  | "ANSWERED"
  | "ACTIVE"
  | "ON_HOLD"
  | "TRANSFERRING"
  | "COMPLETED"
  | "FAILED"
  | "BUSY"
  | "NO_ANSWER"
  | "TERMINATED"
  | "DISCONNECTED";

export type CallEventType =
  | "CALL_CREATED"
  | "CALL_INITIATING"
  | "CALL_RINGING"
  | "CALL_ANSWERED"
  | "CALL_STARTED"
  | "CALL_ENDED"
  | "CALL_FAILED"
  | "CALL_DISCONNECTED"
  | "CALL_ON_HOLD"
  | "CALL_RESUMED"
  | "CALL_TRANSFER_STARTED"
  | "CALL_TRANSFER_COMPLETED"
  | "SPEECH_DETECTED"
  | "TRANSCRIPTION_PARTIAL"
  | "TRANSCRIPTION_FINAL"
  | "AI_THINKING"
  | "AI_RESPONSE_STARTED"
  | "AI_RESPONSE_COMPLETED"
  | "TTS_STARTED"
  | "TTS_COMPLETED"
  | "CALL_WARNING"
  | "CALL_ERROR"
  | "CONSENT_CAPTURED"
  | "DO_NOT_CALL_REQUESTED"
  | "HUMAN_HANDOFF_REQUESTED";

export type TranscriptSpeaker =
  | "CUSTOMER"
  | "AI_AGENT"
  | "HUMAN_OPERATOR"
  | "SYSTEM";

export interface CallSession {
  id: string;
  external_call_id: string | null;
  provider_call_id: string | null;
  campaign_id: string | null;
  campaign_lead_id: string | null;
  lead_id: string | null;
  agent_id: string;
  conversation_id: string | null;
  session_type: CallSessionType;
  direction: CallDirection;
  status: CallSessionStatus;
  caller_number_masked: string;
  destination_number_masked: string;
  started_at: string;
  answered_at: string | null;
  ended_at: string | null;
  duration_seconds: number;
  current_speaker: TranscriptSpeaker | null;
  current_agent_state: string;
  last_activity_at: string;
  outcome: string | null;
  end_reason: string | null;
  flagged_for_review: boolean;
  flag_reason: string | null;
  provider: string;
  recording_enabled: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface NormalizedCallEvent {
  event_id: string;
  call_id: string;
  event_type: CallEventType;
  timestamp: string;
  sequence_number: number;
  source: string;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface TranscriptSegment {
  segment_id: string;
  call_id: string;
  speaker: TranscriptSpeaker;
  text: string;
  final: boolean;
  start_time_ms: number | null;
  end_time_ms: number | null;
  timestamp: string;
  language: string | null;
  confidence: number | null;
  source: string;
}

export interface CallMetricsSnapshot {
  call_id: string;
  stt_latency_ms: number | null;
  llm_ttft_ms: number | null;
  llm_total_ms: number | null;
  tts_latency_ms: number | null;
  end_to_end_ms: number | null;
  provider_healthy: boolean;
  updated_at: string;
}

export interface LiveCallsStats {
  active_calls: number;
  ringing_calls: number;
  in_progress_calls: number;
  on_hold_calls: number;
  attention_required_calls: number;
  recently_completed_calls: number;
  provider_status: string;
}

export interface CallMonitoringSettings {
  recording_enabled_by_default: boolean;
  require_explicit_recording_consent: boolean;
  transcript_retention_days: number;
  mask_customer_numbers: boolean;
  heartbeat_interval_seconds: number;
}

export type LiveCallsWsFrame =
  | { type: "CONNECTED"; client_id: string; heartbeat_interval_seconds: number }
  | { type: "PONG" }
  | { type: "SUBSCRIBED" }
  | { type: "UNSUBSCRIBED" }
  | { type: "ERROR"; message: string }
  | {
      type: "CALL_EVENT";
      event_type: CallEventType;
      call_id: string;
      timestamp: string;
      sequence_number: number;
      data: Record<string, unknown>;
      metadata: Record<string, unknown>;
    }
  | {
      type: "TRANSCRIPT_SEGMENT";
      call_id: string;
      segment: TranscriptSegment;
    }
  | {
      type: "METRICS_UPDATED";
      call_id: string;
      metrics: CallMetricsSnapshot;
    };

// --- Phase 10: Telephony Integration ---

export type TelephonyProviderType =
  | "asterisk"
  | "sip_trunk"
  | "gsm_gateway"
  | "dry_run"
  | "custom";

export type TransportProtocol = "UDP" | "TCP" | "TLS";

export type SipAuthMode =
  | "userpass_registration"
  | "ip_whitelist"
  | "digest_challenge";

export type ProviderConnectionStatus =
  | "DISCONNECTED"
  | "REGISTERING"
  | "CONNECTED"
  | "AUTH_FAILED"
  | "NETWORK_ERROR"
  | "UNAVAILABLE"
  | "INCOMPLETE";

export interface ProviderCapabilities {
  inbound: boolean;
  outbound: boolean;
  hold: boolean;
  transfer: boolean;
  recording: boolean;
  dtmf: boolean;
  supported_codecs: string[];
  max_concurrent_calls: number;
}

export interface TelephonyProviderRecord {
  id: string;
  name: string;
  provider_type: TelephonyProviderType;
  supports_real_calls: boolean;
  configured: boolean;
  status: ProviderConnectionStatus;
  message: string;
  host: string;
  port: number;
  use_tls: boolean;
  transport: TransportProtocol;
  auth_mode?: SipAuthMode;
  username: string;
  auth_username: string | null;
  sip_domain: string | null;
  outbound_proxy: string | null;
  ari_base_url: string | null;
  ari_app: string;
  ari_username: string | null;
  caller_id: string | null;
  allowed_destinations: string[];
  connection_timeout_seconds: number;
  max_concurrent_calls: number;
  supported_codecs: string[];
  enabled: boolean;
  has_password: boolean;
  has_ari_password: boolean;
  has_webhook_secret: boolean;
  capabilities: ProviderCapabilities;
  last_checked_at: string | null;
  last_error: string | null;
  credential_rotated_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SipTrunkRecord {
  id: string;
  name: string;
  provider_id: string;
  host: string;
  port: number;
  transport: TransportProtocol;
  auth_mode?: SipAuthMode;
  username: string;
  caller_id: string;
  register_required: boolean;
  qualify_frequency_seconds?: number;
  options_status?: string;
  allowed_destinations: string[];
  codecs: string[];
  max_concurrent_calls: number;
  preferred: boolean;
  enabled: boolean;
  has_password: boolean;
  status: ProviderConnectionStatus;
  last_error: string | null;
}

export interface InboundRouteRecord {
  id: string;
  name: string;
  phone_number: string;
  sip_destination: string | null;
  agent_id: string;
  business_identity: string;
  working_hours_timezone: string;
  working_hours_start: string;
  working_hours_end: string;
  fallback_destination: string | null;
  enabled: boolean;
}

export interface OutboundRouteRecord {
  id: string;
  name: string;
  provider_id: string;
  trunk_id: string | null;
  caller_id: string;
  destination_pattern: string;
  priority: number;
  require_dlt_template: boolean;
  dlt_entity_id: string | null;
  dlt_template_id: string | null;
  enabled: boolean;
}

export interface GsmGatewayRecord {
  id: string;
  name: string;
  vendor: string;
  mode: string;
  host: string;
  port: number;
  api_base_url: string | null;
  max_channels: number;
  active_channels: number;
  signal_strength: number | null;
  hardware_verified: boolean;
  has_api_token: boolean;
  enabled: boolean;
  status: ProviderConnectionStatus;
  last_error: string | null;
}

export interface TelephonySettings {
  max_concurrent_calls: number;
  audio_buffer_ms: number;
  preferred_codecs: string[];
  connection_timeout_seconds: number;
  retry_limit: number;
  enforce_trai_dlt_compliance: boolean;
  require_caller_id_authorization: boolean;
  block_open_sip_relay: boolean;
  webhook_signature_required: boolean;
}

export interface TelephonyOverview {
  connected_providers: number;
  total_providers: number;
  registered_trunks: number;
  total_trunks: number;
  inbound_routes: number;
  outbound_routes: number;
  active_gateways: number;
  total_gateways: number;
  active_telephony_calls: number;
  failed_telephony_calls: number;
  available_channels: number;
  real_telephony_ready: boolean;
  recent_errors: string[];
}

// --- End-to-End Testing Lab & AI Client Simulator ---

export type TestExecutionMode =
  | "mocked"
  | "local_simulation"
  | "real_microphone"
  | "real_telephony";

export type TestCategory =
  | "unit"
  | "integration"
  | "e2e"
  | "voice"
  | "ai_conversation"
  | "telephony"
  | "compliance"
  | "performance";

export type TestRunStatus =
  | "PENDING"
  | "RUNNING"
  | "PASSED"
  | "FAILED"
  | "REQUIRES_REVIEW"
  | "STOPPED"
  | "ERROR";

export interface CustomerPersona {
  id: string;
  name: string;
  description: string;
  language: string;
  traits: string[];
  sample_utterances: string[];
  interrupt_probability: number;
  silence_probability: number;
  is_builtin: boolean;
}

export interface TestScenario {
  id: string;
  name: string;
  agent_id: string | null;
  persona_id: string;
  language: string;
  objective: string;
  background: string;
  difficulty: "easy" | "medium" | "hard";
  expected_outcome: string;
  max_duration_seconds: number;
  max_turns: number;
  interruption_enabled: boolean;
  kb_questions: string[];
  objection_requirements: string[];
}

export interface EvaluationAssertion {
  rule_id: string;
  category: string;
  passed: boolean;
  critical: boolean;
  description: string;
  evidence: string;
}

export interface ConversationEvaluation {
  overall_score: number;
  passed: boolean;
  requires_review: boolean;
  critical_failures: string[];
  assertions: EvaluationAssertion[];
  criteria_scores: Record<string, number>;
  explanation: string;
  manual_override_score: number | null;
  manual_review_notes: string | null;
}

export interface SimulationTurn {
  turn_number: number;
  customer_text: string;
  agent_text: string;
  customer_audio_generated: boolean;
  agent_audio_generated: boolean;
  stt_ms: number | null;
  llm_ttft_ms: number | null;
  llm_total_ms: number | null;
  tts_ms: number | null;
  end_to_end_ms: number | null;
  interrupted: boolean;
  citations: Record<string, unknown>[];
  timestamp: string;
}

export interface TestRun {
  id: string;
  agent_id: string;
  agent_name: string;
  scenario_id: string | null;
  scenario_name: string;
  persona_id: string;
  category: TestCategory;
  execution_mode: TestExecutionMode;
  status: TestRunStatus;
  model_id: string;
  stt_provider: string;
  tts_provider: string;
  turns: SimulationTurn[];
  evaluation: ConversationEvaluation | null;
  avg_stt_ms: number | null;
  avg_llm_ms: number | null;
  avg_tts_ms: number | null;
  error_logs: string[];
  recommendations: string[];
  started_at: string;
  ended_at: string | null;
}

export interface TestingOverviewStats {
  total_runs: number;
  passed_runs: number;
  failed_runs: number;
  requires_review_runs: number;
  avg_ai_response_ms: number | null;
  avg_stt_ms: number | null;
  avg_tts_ms: number | null;
  completion_rate_percent: number;
  avg_quality_score: number | null;
  voice_pipeline_errors: number;
  telephony_status: string;
  by_category: Record<string, { total: number; passed: number; failed: number }>;
  by_execution_mode: Record<string, number>;
}

// --- Android & iPhone Device Gateway ---

export type DevicePlatform = "android" | "ios";
export type DeviceStatus = "PAIRING" | "ONLINE" | "OFFLINE" | "DEGRADED" | "REVOKED" | "ERROR";

export interface DeviceCapabilityProfile {
  platform: DevicePlatform;
  cellular_call_initiation: boolean;
  cellular_call_state: boolean;
  cellular_audio_capture: boolean;
  cellular_audio_injection: boolean;
  cellular_audio_bridge_status: string;
  voip_supported: boolean;
  callkit_supported: boolean;
  device_health: boolean;
  ai_call_ready: boolean;
}

export interface DeviceHealthSnapshot {
  battery_percent: number | null;
  battery_charging: boolean | null;
  network_type: string;
  connected: boolean;
  sim_present: boolean | null;
  carrier_name: string | null;
  signal_strength_dbm: number | null;
  permissions: Record<string, boolean>;
  last_error: string | null;
  updated_at: string;
}

export interface MobileDevice {
  id: string;
  account_id: string;
  device_name: string;
  platform: DevicePlatform;
  platform_version: string;
  app_version: string;
  device_status: DeviceStatus;
  capability_profile: DeviceCapabilityProfile;
  health: DeviceHealthSnapshot;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PairingCodeRecord {
  code: string;
  account_id: string;
  platform: DevicePlatform;
  used: boolean;
  expires_at: string;
  created_at: string;
}

export interface DeviceEventRecord {
  event_id: string;
  device_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

// --- Internal Asterisk 23 Calling & WebRTC Dialer ---

export type InternalCallMode = "human" | "ai" | "echo";

export type InternalCallStatus =
  | "INITIATING"
  | "RINGING"
  | "ACTIVE"
  | "ENDED"
  | "FAILED";

export interface InternalExtension {
  extension: string;
  label: string;
  transport: string;
  webrtc_enabled: boolean;
  registered: boolean;
  state: string;
  active_channels: number;
}

export interface InternalCallRecord {
  call_id: string;
  provider_id: string;
  channel_id: string;
  live_call_session_id: string | null;
  from_extension: string;
  to_extension: string;
  mode: InternalCallMode;
  agent_id: string | null;
  status: InternalCallStatus;
  is_external: boolean;
  idempotency_key: string | null;
  started_at: string;
  answered_at: string | null;
  ended_at: string | null;
  duration_seconds: number;
  hangup_reason: string | null;
}

export interface InternalCallsHealth {
  ari_connected: boolean;
  provider_id: string | null;
  provider_name: string | null;
  asterisk_version: string | null;
  registered_extensions: number;
  active_calls: number;
  external_telephony_configured: boolean;
  message: string;
}

export interface InternalWebRTCConfig {
  ws_url: string;
  sip_domain: string;
  extensions: string[];
  ice_servers: { urls: string[] }[];
}
