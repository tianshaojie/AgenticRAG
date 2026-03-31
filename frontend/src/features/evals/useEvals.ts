import { ref } from 'vue';

import { apiClient } from '../../api/client';
import type { EvalResultRead, EvalRunResponse } from '../../api/contracts';
import { parseApiError } from '../../lib/http';

const LAST_EVAL_RUN_ID_KEY = 'agentic-rag:last-eval-run-id';

function saveLastRunId(id: string) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(LAST_EVAL_RUN_ID_KEY, id);
}

function readLastRunId(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem(LAST_EVAL_RUN_ID_KEY);
}

export function useEvals() {
  const latest = ref<EvalResultRead | null>(null);
  const lastRun = ref<EvalRunResponse | null>(null);
  const loading = ref(false);
  const running = ref(false);
  const error = ref<string | null>(null);

  async function refreshLatest() {
    loading.value = true;
    error.value = null;

    try {
      latest.value = await apiClient.getLatestEvalResult();
      saveLastRunId(latest.value.eval_run_id);
      return;
    } catch {
      const lastRunId = readLastRunId();
      if (!lastRunId) {
        latest.value = null;
        return;
      }

      try {
        latest.value = await apiClient.getEvalResult(lastRunId);
      } catch (err) {
        latest.value = null;
        error.value = parseApiError(err);
      }
    } finally {
      loading.value = false;
    }
  }

  async function runEval(payload?: { name?: string; dataset?: string; config?: Record<string, unknown> }) {
    running.value = true;
    error.value = null;

    try {
      lastRun.value = await apiClient.runEval({
        name: payload?.name,
        dataset: payload?.dataset ?? 'golden_v1',
        config: payload?.config ?? {},
      });
      saveLastRunId(lastRun.value.eval_run_id);
      latest.value = await apiClient.getEvalResult(lastRun.value.eval_run_id);
    } catch (err) {
      error.value = parseApiError(err);
      throw err;
    } finally {
      running.value = false;
    }
  }

  return {
    latest,
    lastRun,
    loading,
    running,
    error,
    refreshLatest,
    runEval,
  };
}
