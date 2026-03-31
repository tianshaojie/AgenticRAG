export type UUID = string;

export type DocumentStatus = 'received' | 'indexing' | 'indexed' | 'failed';
export type HealthStatus = 'ok' | 'degraded' | 'failed';

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

export interface ChatQueryResponse {
  session_id: UUID;
  message_id: UUID;
  answer: string;
  citations: CitationDto[];
  retrieval_results: RetrievalResultDto[];
  abstained: boolean;
  reason?: string | null;
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
}

export interface HealthCheck {
  name: string;
  status: HealthStatus;
  detail: string;
}

export interface ReadyResponse {
  status: HealthStatus;
  checks: HealthCheck[];
}
