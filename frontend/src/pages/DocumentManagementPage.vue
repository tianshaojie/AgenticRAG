<script setup lang="ts">
import type { Component } from 'vue';
import { computed, onMounted } from 'vue';
import { AlertTriangle, CheckCircle2, FileStack, LoaderCircle } from 'lucide-vue-next';

import DocumentTable from '../components/DocumentTable.vue';
import DocumentUploadForm from '../components/DocumentUploadForm.vue';
import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import { useDocuments } from '../features/documents/useDocuments';

const { documents, loading, uploading, error, indexingMap, indexErrors, refresh, upload, indexDocument, retryIndex } =
  useDocuments();

const summaryCards = computed(() => {
  const total = documents.value.length;
  const indexed = documents.value.filter((item) => item.status === 'indexed').length;
  const indexing = documents.value.filter((item) => item.status === 'indexing').length;
  const failed = documents.value.filter((item) => item.status === 'failed').length;
  return [
    { label: 'Total', value: total, tone: 'default' as const, icon: FileStack as Component },
    { label: 'Indexed', value: indexed, tone: 'success' as const, icon: CheckCircle2 as Component },
    { label: 'Indexing', value: indexing, tone: 'warning' as const, icon: LoaderCircle as Component },
    {
      label: 'Failed',
      value: failed,
      tone: failed > 0 ? ('danger' as const) : ('default' as const),
      icon: AlertTriangle as Component,
    },
  ];
});

const failedRows = computed(() => {
  return documents.value
    .filter((doc) => doc.status === 'failed' || Boolean(indexErrors.value[doc.id]))
    .map((doc) => ({
      id: doc.id,
      title: doc.title,
      error: indexErrors.value[doc.id] ?? 'Indexing failed without detailed error message.',
    }));
});

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

async function onBatchIndex(ids: string[]) {
  for (const id of ids) {
    await indexDocument(id);
  }
}

async function onBatchRetry(ids: string[]) {
  for (const id of ids) {
    await retryIndex(id);
  }
}

async function retryAllFailed() {
  const ids = failedRows.value.map((item) => item.id);
  if (ids.length === 0) {
    return;
  }
  await onBatchRetry(ids);
}
</script>

<template>
  <section class="space-y-4">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="inline-flex items-center gap-2 text-xl font-semibold text-app-text">
          <FileStack class="h-5 w-5" aria-hidden="true" />
          Document Management
        </h2>
        <p class="text-sm text-app-text-muted">Upload files, monitor indexing status, and recover failed jobs.</p>
      </div>
      <Button variant="outline" :disabled="loading" @click="refresh">Refresh</Button>
    </header>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card v-for="item in summaryCards" :key="item.label">
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs uppercase tracking-wide text-app-text-muted">{{ item.label }}</p>
          <component :is="item.icon" class="h-4 w-4 text-app-text-muted" aria-hidden="true" />
        </div>
        <div class="mt-2 flex items-center justify-between gap-2">
          <p class="text-2xl font-semibold text-app-text">{{ item.value }}</p>
          <Badge :tone="item.tone">{{ item.label }}</Badge>
        </div>
      </Card>
    </section>

    <div v-if="error" class="space-y-2">
      <ErrorState :message="error" />
      <Button variant="outline" size="sm" @click="refresh">Retry Load</Button>
    </div>

    <DocumentUploadForm :loading="uploading" @submit="onUpload" />

    <Card v-if="failedRows.length > 0" class="border-danger/30 bg-danger/5">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-sm font-semibold text-app-text">Failed Indexing Summary</h3>
        <Button variant="destructive" size="sm" :disabled="loading" @click="retryAllFailed">Retry All Failed</Button>
      </div>
      <ul class="mt-3 space-y-2">
        <li v-for="item in failedRows" :key="item.id" class="rounded-md border border-danger/30 bg-card px-3 py-2">
          <p class="text-sm font-medium text-app-text">{{ item.title }}</p>
          <p class="text-xs text-app-text-muted">{{ item.id }}</p>
          <p class="mt-1 text-xs text-danger">{{ item.error }}</p>
        </li>
      </ul>
    </Card>

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
      @batch-index="onBatchIndex"
      @batch-retry="onBatchRetry"
    />
  </section>
</template>
