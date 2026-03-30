export type UUID = string;

export interface CitationDto {
  chunk_id: UUID;
  document_id: UUID;
  quote: string;
  score: number;
}

export interface DocumentCreateRequest {
  title: string;
  source_uri: string;
  mime_type?: string | null;
  metadata?: Record<string, unknown>;
}

export interface DocumentRead {
  id: UUID;
  title: string;
  source_uri: string;
  mime_type?: string | null;
  status: 'received' | 'indexing' | 'indexed' | 'failed';
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DocumentListResponse {
  items: DocumentRead[];
  total: number;
}

export interface DocumentIndexRequest {
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
}

export interface DocumentIndexResponse {
  document_id: UUID;
  status: string;
  accepted: boolean;
}

export interface ChatQueryRequest {
  session_id?: UUID;
  query: string;
  top_k?: number;
  rerank_k?: number;
}

export interface ChatQueryResponse {
  session_id: UUID;
  message_id: UUID;
  trace_id: UUID;
  answer: string;
  citations: CitationDto[];
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

export interface EvalRunRequest {
  name: string;
  dataset: string;
  config?: Record<string, unknown>;
}

export interface EvalRunResponse {
  eval_run_id: UUID;
  status: string;
  accepted: boolean;
}

export interface EvalResultRead {
  eval_run_id: UUID;
  status: string;
  summary: Record<string, unknown>;
  started_at: string;
  finished_at?: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
}

export interface ReadyResponse {
  status: string;
  checks: Record<string, string>;
}
