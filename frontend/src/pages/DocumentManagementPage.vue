<script setup lang="ts">
import { onMounted } from 'vue';

import DocumentTable from '../components/DocumentTable.vue';
import DocumentUploadForm from '../components/DocumentUploadForm.vue';
import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import { useDocuments } from '../features/documents/useDocuments';

const { documents, loading, uploading, error, indexingMap, refresh, upload, indexDocument } = useDocuments();

onMounted(() => {
  void refresh();
});

async function onUpload(payload: { title: string; file: File; metadata?: Record<string, unknown> }) {
  await upload(payload);
}

async function onIndex(documentId: string) {
  await indexDocument(documentId);
}
</script>

<template>
  <section class="space-y-4">
    <header>
      <h2 class="text-lg font-semibold">Document Management</h2>
      <p class="text-sm text-slate-600">Upload txt/markdown files, view documents, and trigger indexing.</p>
    </header>

    <ErrorState v-if="error" :message="error" />

    <DocumentUploadForm :loading="uploading" @submit="onUpload" />

    <LoadingState v-if="loading && documents.length === 0" message="Loading documents..." />

    <EmptyState
      v-else-if="!loading && documents.length === 0"
      title="No documents yet"
      description="Upload a txt or markdown document to start indexing and QA."
    />

    <DocumentTable v-else :indexing-map="indexingMap" :items="documents" @index="onIndex" />
  </section>
</template>
