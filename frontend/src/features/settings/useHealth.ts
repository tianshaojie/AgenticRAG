import { ref } from 'vue';

import { apiClient } from '../../api/client';
import type { HealthResponse, ReadyResponse } from '../../api/contracts';
import { parseApiError } from '../../lib/http';

export function useHealth() {
  const health = ref<HealthResponse | null>(null);
  const ready = ref<ReadyResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function refresh() {
    loading.value = true;
    error.value = null;

    try {
      const [healthValue, readyValue] = await Promise.all([apiClient.health(), apiClient.ready()]);
      health.value = healthValue;
      ready.value = readyValue;
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      loading.value = false;
    }
  }

  return {
    health,
    ready,
    loading,
    error,
    refresh,
  };
}
