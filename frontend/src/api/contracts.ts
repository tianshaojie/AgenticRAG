export type UUID = string;

export type DocumentStatus = 'received' | 'indexing' | 'indexed' | 'failed';
export type HealthStatus = 'ok' | 'degraded' | 'failed';
export type ErrorCategory = 'validation' | 'dependency' | 'timeout' | 'internal' | 'unavailable';

export interface CitationSpan {
  start_char: number;
  end_char: number;
}

export interface CitationDto {
  chunk_id: UUID;
  document_id: UUID;
  quote: string;
  score: number;
  span: CitationSpan;
}

export interface RetrievalResultDto {
  chunk_id: UUID;
  document_id: UUID;
  score: number;
  distance: number;
  content_preview: string;
}

export interface DocumentRead {
  id: UUID;
  title: string;
  source_uri: string;
  mime_type: string | null;
  status: DocumentStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentRead[];
  total: number;
}

export interface DocumentIndexRequest {
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface DocumentIndexResponse {
  document_id: UUID;
  status: string;
  chunk_count: number;
  vector_count: number;
}

export interface ChatQueryRequest {
  session_id?: UUID | null;
  query: string;
  top_k?: number;
  score_threshold?: number;
  embedding_model?: string;
}

export interface UncertaintySignalDto {
  is_uncertain: boolean;
  reason: string;
  conflict_type?: string | null;
  conflict_chunk_ids: UUID[];
}

export interface ChatQueryResponse {
  session_id: UUID;
  message_id: UUID;
  answer: string;
  citations: CitationDto[];
  retrieval_results: RetrievalResultDto[];
  abstained: boolean;
  reason?: string | null;
  uncertainty?: UncertaintySignalDto | null;
  created_at: string;
}

export interface TraceStepRead {
  step_order: number;
  state: string;
  action: string;
  status: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  input_summary?: string | null;
  output_summary?: string | null;
  fallback: boolean;
  latency_ms?: number | null;
  error_message?: string | null;
  created_at: string;
}

export interface TraceRead {
  trace_id: UUID;
  session_id: UUID;
  status: string;
  start_state: string;
  end_state?: string | null;
  steps: TraceStepRead[];
  started_at: string;
  finished_at?: string | null;
}

export interface HealthResponse {
  status: HealthStatus;
  service: string;
  timestamp: string;
  checks: HealthCheck[];
}

export interface HealthCheck {
  name: string;
  status: HealthStatus;
  detail: string;
}

export interface ReadyResponse {
  status: HealthStatus;
  checks: HealthCheck[];
  summary: Record<string, string>;
}

export type ProviderName = 'llm' | 'reranker';
export type ProviderTarget = ProviderName | 'all';

export interface ProviderRuntimeConfig {
  name: ProviderName;
  provider: string;
  enabled: boolean;
  has_api_key: boolean;
  api_key_last4?: string | null;
  endpoint?: string | null;
  base_url?: string | null;
  model?: string | null;
  timeout_seconds: number;
  max_retries: number;
}

export interface ProviderSettingsResponse {
  llm: ProviderRuntimeConfig;
  reranker: ProviderRuntimeConfig;
  note: string;
}

export interface ProviderSettingsUpdateRequest {
  llm_api_key?: string | null;
  reranker_api_key?: string | null;
  llm_endpoint?: string | null;
  llm_base_url?: string | null;
  llm_model?: string | null;
  reranker_endpoint?: string | null;
  reranker_base_url?: string | null;
  reranker_model?: string | null;
  enable_real_llm_provider?: boolean;
  enable_real_reranker_provider?: boolean;
}

export interface ProviderCheckRequest {
  target?: ProviderTarget;
}

export interface ProviderCheckItem {
  provider: ProviderName;
  status: HealthStatus;
  detail: string;
  checked_at: string;
  latency_ms?: number | null;
  used_real_provider: boolean;
  fallback_used: boolean;
}

export interface ProviderCheckResponse {
  status: HealthStatus;
  checks: ProviderCheckItem[];
}

export interface EvalRunRequest {
  name?: string;
  dataset: string;
  config?: Record<string, unknown>;
}

export interface EvalSummarySection {
  [key: string]: unknown;
}

export interface EvalSummary {
  dataset: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  retrieval: EvalSummarySection;
  answer: EvalSummarySection;
  agent: EvalSummarySection;
  failed_case_samples: Array<{
    case_id: UUID;
    case_name: string;
    query: string;
    reasons: string[];
  }>;
  gate_passed: boolean;
}

export interface EvalRunResponse {
  eval_run_id: UUID;
  status: string;
  accepted: boolean;
  summary: EvalSummary | Record<string, unknown>;
}

export interface FailedEvalCaseDto {
  case_id: UUID;
  case_name: string;
  query: string;
  reasons: string[];
  metrics: Record<string, unknown>;
}

export interface EvalResultRead {
  eval_run_id: UUID;
  name: string;
  dataset: string;
  status: string;
  summary: EvalSummary | Record<string, unknown>;
  failed_cases: FailedEvalCaseDto[];
  started_at: string;
  finished_at?: string | null;
}

export interface ApiErrorDetail {
  code: string;
  category: ErrorCategory;
  message: string;
  request_id: string;
  trace_id: string;
  details: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}
