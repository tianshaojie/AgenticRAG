import { ref } from 'vue';

import { apiClient } from '../../api/client';
import type { ChatQueryResponse, TraceRead, UUID } from '../../api/contracts';
import { parseApiError } from '../../lib/http';

export function useChat() {
  const response = ref<ChatQueryResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const trace = ref<TraceRead | null>(null);
  const traceLoading = ref(false);
  const traceError = ref<string | null>(null);

  async function ask(payload: { query: string; top_k: number; score_threshold: number }) {
    loading.value = true;
    error.value = null;

    try {
      response.value = await apiClient.chatQuery({
        query: payload.query,
        top_k: payload.top_k,
        score_threshold: payload.score_threshold,
        embedding_model: 'deterministic-local-v1',
      });
      trace.value = null;
      traceError.value = null;
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      loading.value = false;
    }
  }

  async function loadTrace(sessionId: UUID) {
    traceLoading.value = true;
    traceError.value = null;

    try {
      trace.value = await apiClient.getChatTrace(sessionId);
    } catch (err) {
      traceError.value = parseApiError(err);
    } finally {
      traceLoading.value = false;
    }
  }

  return {
    response,
    loading,
    error,
    ask,
    trace,
    traceLoading,
    traceError,
    loadTrace,
  };
}
