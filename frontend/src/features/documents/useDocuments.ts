import { ref } from 'vue';

import { apiClient, type DocumentUploadPayload } from '../../api/client';
import type { DocumentRead, UUID } from '../../api/contracts';

function normalizeError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unknown error';
}

export function useDocuments() {
  const documents = ref<DocumentRead[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const uploading = ref(false);
  const error = ref<string | null>(null);
  const indexingMap = ref<Record<string, boolean>>({});

  async function refresh() {
    loading.value = true;
    error.value = null;

    try {
      const response = await apiClient.listDocuments({ limit: 100, offset: 0 });
      documents.value = response.items;
      total.value = response.total;
    } catch (err) {
      error.value = normalizeError(err);
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
      error.value = normalizeError(err);
      throw err;
    } finally {
      uploading.value = false;
    }
  }

  async function indexDocument(id: UUID) {
    indexingMap.value[id] = true;
    error.value = null;

    try {
      await apiClient.indexDocument(id, {});
      await refresh();
    } catch (err) {
      error.value = normalizeError(err);
      throw err;
    } finally {
      indexingMap.value[id] = false;
    }
  }

  return {
    documents,
    total,
    loading,
    uploading,
    error,
    indexingMap,
    refresh,
    upload,
    indexDocument,
  };
}
