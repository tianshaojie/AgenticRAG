import type {
  ChatQueryResponse,
  DocumentRead,
  EvalResultRead,
  TraceRead,
  UUID,
} from '../api/contracts';

export interface DocumentRowVM {
  id: UUID;
  title: string;
  status: DocumentRead['status'];
  createdAtLabel: string;
  sourceLabel: string;
  hasIndexError: boolean;
}

export interface ChatAnswerVM {
  sessionId: UUID;
  messageId: UUID;
  answer: string;
  abstained: boolean;
  reason: string | null;
  uncertain: boolean;
  uncertaintyReason: string | null;
  citationCount: number;
}

export interface TraceStepVM {
  stepOrder: number;
  state: string;
  status: string;
  action: string;
  latencyMs: number;
  fallback: boolean;
  hasError: boolean;
  inputSummary: string;
  outputSummary: string;
}

export interface EvalSummaryVM {
  runId: UUID;
  name: string;
  gatePassed: boolean;
  totalCases: number;
  passRate: number;
  unsupportedAnswerRate: number;
  citationIntegrityFailures: number;
}

export interface RecentSessionItem {
  sessionId: UUID;
  query: string;
  createdAt: string;
  abstained: boolean;
  reason: string | null;
}

export interface AppThemeConfig {
  name: string;
  radius: 'md' | 'lg';
  density: 'comfortable' | 'compact';
}

export interface NavItem {
  label: string;
  to: string;
  icon?: string;
  badge?: string;
}

export type StatusToneMap = Record<
  'ok' | 'degraded' | 'failed' | 'success' | 'warning' | 'danger' | 'default',
  'default' | 'success' | 'warning' | 'danger'
>;

export function toChatAnswerVM(response: ChatQueryResponse): ChatAnswerVM {
  return {
    sessionId: response.session_id,
    messageId: response.message_id,
    answer: response.answer,
    abstained: response.abstained,
    reason: response.reason ?? null,
    uncertain: Boolean(response.uncertainty?.is_uncertain),
    uncertaintyReason: response.uncertainty?.reason ?? null,
    citationCount: response.citations.length,
  };
}

export function toTraceStepVM(trace: TraceRead): TraceStepVM[] {
  return trace.steps.map((step) => ({
    stepOrder: step.step_order,
    state: step.state,
    status: step.status,
    action: step.action,
    latencyMs: step.latency_ms ?? 0,
    fallback: step.fallback,
    hasError: Boolean(step.error_message),
    inputSummary: step.input_summary ?? '-',
    outputSummary: step.output_summary ?? '-',
  }));
}

export function toEvalSummaryVM(result: EvalResultRead): EvalSummaryVM {
  const summary = (result.summary ?? {}) as Record<string, unknown>;
  const answer = (summary.answer ?? {}) as Record<string, unknown>;
  return {
    runId: result.eval_run_id,
    name: result.name,
    gatePassed: Boolean(summary.gate_passed),
    totalCases: Number(summary.total_cases ?? 0),
    passRate: Number(summary.pass_rate ?? 0),
    unsupportedAnswerRate: Number(answer.unsupported_answer_rate ?? 0),
    citationIntegrityFailures: Number(answer.citation_integrity_failures ?? 0),
  };
}
