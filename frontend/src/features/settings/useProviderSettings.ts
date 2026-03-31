import { ref } from 'vue';

import { apiClient } from '../../api/client';
import type {
  ProviderCheckItem,
  ProviderSettingsResponse,
  ProviderTarget,
} from '../../api/contracts';
import { parseApiError } from '../../lib/http';

export interface SaveProviderSettingsInput {
  llmApiKey?: string;
  rerankerApiKey?: string;
  llmEndpoint?: string;
  llmModel?: string;
  rerankerEndpoint?: string;
  rerankerModel?: string;
  enableRealLlmProvider: boolean;
  enableRealRerankerProvider: boolean;
}

export function useProviderSettings() {
  const settings = ref<ProviderSettingsResponse | null>(null);
  const checks = ref<ProviderCheckItem[]>([]);
  const loading = ref(false);
  const saving = ref(false);
  const checking = ref(false);
  const error = ref<string | null>(null);
  const success = ref<string | null>(null);

  async function refreshSettings() {
    loading.value = true;
    error.value = null;
    try {
      settings.value = await apiClient.getProviderSettings();
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      loading.value = false;
    }
  }

  async function saveSettings(input: SaveProviderSettingsInput) {
    saving.value = true;
    error.value = null;
    success.value = null;

    try {
      const payload: Record<string, unknown> = {
        enable_real_llm_provider: input.enableRealLlmProvider,
        enable_real_reranker_provider: input.enableRealRerankerProvider,
      };
      if (input.llmApiKey && input.llmApiKey.trim().length > 0) {
        payload.llm_api_key = input.llmApiKey.trim();
      }
      if (input.rerankerApiKey && input.rerankerApiKey.trim().length > 0) {
        payload.reranker_api_key = input.rerankerApiKey.trim();
      }
      if (input.llmEndpoint && input.llmEndpoint.trim().length > 0) {
        payload.llm_endpoint = input.llmEndpoint.trim();
      }
      if (input.llmModel && input.llmModel.trim().length > 0) {
        payload.llm_model = input.llmModel.trim();
      }
      if (input.rerankerEndpoint && input.rerankerEndpoint.trim().length > 0) {
        payload.reranker_endpoint = input.rerankerEndpoint.trim();
      }
      if (input.rerankerModel && input.rerankerModel.trim().length > 0) {
        payload.reranker_model = input.rerankerModel.trim();
      }

      settings.value = await apiClient.updateProviderSettings(payload);
      success.value = 'Provider settings updated (runtime only).';
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      saving.value = false;
    }
  }

  async function checkConnectivity(target: ProviderTarget = 'all') {
    checking.value = true;
    error.value = null;
    success.value = null;
    try {
      const response = await apiClient.checkProviderConnectivity({ target });
      checks.value = response.checks;
      success.value = `Provider check status: ${response.status}`;
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      checking.value = false;
    }
  }

  return {
    settings,
    checks,
    loading,
    saving,
    checking,
    error,
    success,
    refreshSettings,
    saveSettings,
    checkConnectivity,
  };
}
