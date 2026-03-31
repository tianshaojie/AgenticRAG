<script setup lang="ts">
import { onMounted } from 'vue';

import DocumentTable from '../components/DocumentTable.vue';
import DocumentUploadForm from '../components/DocumentUploadForm.vue';
import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Button from '../components/ui/button/Button.vue';
import { useDocuments } from '../features/documents/useDocuments';

const { documents, loading, uploading, error, indexingMap, indexErrors, refresh, upload, indexDocument, retryIndex } =
  useDocuments();

onMounted(() => {
  void refresh();
});

async function onUpload(payload: { title: string; file: File; metadata?: Record<string, unknown> }) {
  await upload(payload);
}

async function onIndex(documentId: string) {
  await indexDocument(documentId);
}

async function onRetry(documentId: string) {
  await retryIndex(documentId);
}
</script>

<template>
  <section class="space-y-4">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Document Management</h2>
        <p class="text-sm text-slate-600">Upload txt/markdown files, view documents, and trigger indexing.</p>
      </div>
      <Button variant="outline" :disabled="loading" @click="refresh">Refresh</Button>
    </header>

    <div v-if="error" class="space-y-2">
      <ErrorState :message="error" />
      <Button variant="outline" size="sm" @click="refresh">Retry Load</Button>
    </div>

    <DocumentUploadForm :loading="uploading" @submit="onUpload" />

    <LoadingState v-if="loading && documents.length === 0" message="Loading documents..." />

    <EmptyState
      v-else-if="!loading && documents.length === 0"
      title="No documents yet"
      description="Upload a txt or markdown document to start indexing and QA."
    />

    <DocumentTable
      v-else
      :index-errors="indexErrors"
      :indexing-map="indexingMap"
      :items="documents"
      @index="onIndex"
      @retry="onRetry"
    />
  </section>
</template>
