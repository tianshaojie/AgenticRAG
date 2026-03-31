import { ref } from 'vue';

import { apiClient } from '../../api/client';
import type { TraceRead, UUID } from '../../api/contracts';
import { parseApiError } from '../../lib/http';

export function useTrace() {
  const trace = ref<TraceRead | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastSessionId = ref<UUID | null>(null);

  async function load(sessionId: UUID) {
    loading.value = true;
    error.value = null;
    lastSessionId.value = sessionId;

    try {
      trace.value = await apiClient.getChatTrace(sessionId);
    } catch (err) {
      error.value = parseApiError(err);
      trace.value = null;
    } finally {
      loading.value = false;
    }
  }

  return {
    trace,
    loading,
    error,
    lastSessionId,
    load,
  };
}
