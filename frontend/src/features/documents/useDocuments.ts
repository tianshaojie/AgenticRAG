import { ref } from 'vue';

import { apiClient, type DocumentUploadPayload } from '../../api/client';
import type { DocumentRead, UUID } from '../../api/contracts';
import { parseApiError } from '../../lib/http';

export function useDocuments() {
  const documents = ref<DocumentRead[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const uploading = ref(false);
  const error = ref<string | null>(null);
  const indexingMap = ref<Record<string, boolean>>({});
  const indexErrors = ref<Record<string, string | null>>({});

  async function refresh() {
    loading.value = true;
    error.value = null;

    try {
      const response = await apiClient.listDocuments({ limit: 100, offset: 0 });
      documents.value = response.items;
      total.value = response.total;
      const nextErrors: Record<string, string | null> = {};
      for (const doc of response.items) {
        nextErrors[doc.id] = indexErrors.value[doc.id] ?? null;
      }
      indexErrors.value = nextErrors;
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      loading.value = false;
    }
  }

  async function upload(payload: DocumentUploadPayload) {
    uploading.value = true;
    error.value = null;

    try {
      await apiClient.uploadDocument(payload);
      await refresh();
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      uploading.value = false;
    }
  }

  async function indexDocument(id: UUID) {
    indexingMap.value[id] = true;
    indexErrors.value[id] = null;

    try {
      await apiClient.indexDocument(id, {});
      await refresh();
    } catch (err) {
      const message = parseApiError(err);
      indexErrors.value[id] = message;
      error.value = message;
    } finally {
      indexingMap.value[id] = false;
    }
  }

  async function retryIndex(id: UUID) {
    await indexDocument(id);
  }

  return {
    documents,
    total,
    loading,
    uploading,
    error,
    indexingMap,
    indexErrors,
    refresh,
    upload,
    indexDocument,
    retryIndex,
  };
}
