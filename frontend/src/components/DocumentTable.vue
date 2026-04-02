<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { DocumentRead, UUID } from '../api/contracts';

import DocumentStatusCell from './DocumentStatusCell.vue';
import Badge from './ui/badge/Badge.vue';
import Button from './ui/button/Button.vue';
import Input from './ui/input/Input.vue';
import DataTable from './ui/datatable/DataTable.vue';

const props = withDefaults(
  defineProps<{
    items: DocumentRead[];
    indexingMap?: Record<string, boolean>;
    indexErrors?: Record<string, string | null>;
  }>(),
  {
    indexingMap: () => ({}),
    indexErrors: () => ({}),
  },
);

const emit = defineEmits<{
  index: [id: UUID];
  retry: [id: UUID];
  batchIndex: [ids: UUID[]];
  batchRetry: [ids: UUID[]];
}>();

const searchTerm = ref('');
const statusFilter = ref<'all' | DocumentRead['status']>('all');
const createdSort = ref<'desc' | 'asc'>('desc');
const selectedMap = ref<Record<string, boolean>>({});

const columns = [
  { key: 'select', label: '', widthClass: 'w-10' },
  { key: 'title', label: 'Document' },
  { key: 'status', label: 'Status', widthClass: 'w-[140px]' },
  { key: 'error', label: 'Error', widthClass: 'w-[260px]' },
  { key: 'created', label: 'Created', widthClass: 'w-[180px]' },
  { key: 'actions', label: 'Actions', widthClass: 'w-[160px]' },
];

const visibleRows = computed(() => {
  const query = searchTerm.value.trim().toLowerCase();

  return [...props.items]
    .filter((doc) => {
      const matchesStatus = statusFilter.value === 'all' || doc.status === statusFilter.value;
      const matchesQuery =
        !query ||
        doc.title.toLowerCase().includes(query) ||
        doc.id.toLowerCase().includes(query) ||
        doc.source_uri.toLowerCase().includes(query);
      return matchesStatus && matchesQuery;
    })
    .sort((a, b) => {
      const left = new Date(a.created_at).getTime();
      const right = new Date(b.created_at).getTime();
      return createdSort.value === 'desc' ? right - left : left - right;
    });
});

watch(
  () => props.items,
  (nextItems) => {
    const validIds = new Set(nextItems.map((item) => item.id));
    const nextSelected: Record<string, boolean> = {};
    for (const [id, selected] of Object.entries(selectedMap.value)) {
      if (selected && validIds.has(id)) {
        nextSelected[id] = true;
      }
    }
    selectedMap.value = nextSelected;
  },
  { deep: true },
);

const selectedVisibleIds = computed(() => {
  return visibleRows.value.filter((row) => selectedMap.value[row.id]).map((row) => row.id);
});

const allVisibleSelected = computed(() => {
  return visibleRows.value.length > 0 && selectedVisibleIds.value.length === visibleRows.value.length;
});

const indexableIds = computed(() => {
  return selectedVisibleIds.value.filter((id) => {
    const row = visibleRows.value.find((item) => item.id === id);
    if (!row) {
      return false;
    }
    return row.status !== 'indexing';
  });
});

const retryableIds = computed(() => {
  return selectedVisibleIds.value.filter((id) => {
    const row = visibleRows.value.find((item) => item.id === id);
    if (!row) {
      return false;
    }
    return row.status === 'failed';
  });
});

function toggleSelectAll(): void {
  const next = !allVisibleSelected.value;
  const map = { ...selectedMap.value };
  for (const row of visibleRows.value) {
    map[row.id] = next;
  }
  selectedMap.value = map;
}

function toggleRow(id: string): void {
  selectedMap.value = {
    ...selectedMap.value,
    [id]: !selectedMap.value[id],
  };
}

function clearSelection(): void {
  selectedMap.value = {};
}

function batchIndexSelected(): void {
  if (indexableIds.value.length === 0) {
    return;
  }
  emit('batchIndex', indexableIds.value);
}

function batchRetrySelected(): void {
  if (retryableIds.value.length === 0) {
    return;
  }
  emit('batchRetry', retryableIds.value);
}

function getActionLabel(doc: DocumentRead): string {
  if (props.indexingMap?.[doc.id]) {
    return doc.status === 'failed' ? 'Retrying...' : 'Indexing...';
  }
  if (doc.status === 'failed') {
    return 'Retry';
  }
  if (doc.status === 'indexed') {
    return 'Reindex';
  }
  return 'Index';
}

function toCreatedLabel(value: string): string {
  return new Date(value).toLocaleString();
}
</script>

<template>
  <section class="space-y-3 rounded-lg border border-border bg-card p-4 shadow-soft">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-sm font-semibold text-app-text">Documents</h3>
      <Badge tone="default">{{ visibleRows.length }} / {{ props.items.length }}</Badge>
    </div>

    <div class="grid gap-2 md:grid-cols-[1fr_180px_180px]">
      <Input
        v-model="searchTerm"
        data-testid="document-search-input"
        placeholder="Search by title, id, source"
      />

      <select
        v-model="statusFilter"
        class="h-10 rounded-md border border-border bg-card px-3 text-sm text-app-text"
        data-testid="document-status-filter"
      >
        <option value="all">All status</option>
        <option value="received">Received</option>
        <option value="indexing">Indexing</option>
        <option value="indexed">Indexed</option>
        <option value="failed">Failed</option>
      </select>

      <select
        v-model="createdSort"
        class="h-10 rounded-md border border-border bg-card px-3 text-sm text-app-text"
        data-testid="document-created-sort"
      >
        <option value="desc">Newest first</option>
        <option value="asc">Oldest first</option>
      </select>
    </div>

    <div class="flex flex-wrap items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-2">
      <p class="text-xs text-app-text-muted">{{ selectedVisibleIds.length }} selected</p>
      <Button size="sm" variant="ghost" data-testid="documents-select-visible" @click="toggleSelectAll">
        {{ allVisibleSelected ? 'Unselect Visible' : 'Select Visible' }}
      </Button>
      <Button
        size="sm"
        variant="outline"
        data-testid="documents-batch-index"
        :disabled="indexableIds.length === 0"
        @click="batchIndexSelected"
      >
        Batch Index ({{ indexableIds.length }})
      </Button>
      <Button
        size="sm"
        variant="destructive"
        data-testid="documents-batch-retry"
        :disabled="retryableIds.length === 0"
        @click="batchRetrySelected"
      >
        Batch Retry ({{ retryableIds.length }})
      </Button>
      <Button size="sm" variant="ghost" :disabled="selectedVisibleIds.length === 0" @click="clearSelection">
        Clear
      </Button>
    </div>

    <DataTable :columns="columns" :rows="visibleRows" empty-text="No documents match current filters.">
      <template #cell-select="{ row }">
        <input
          type="checkbox"
          :checked="Boolean(selectedMap[row.id])"
          :aria-label="`select-${row.id}`"
          @change="toggleRow(row.id)"
        />
      </template>

      <template #cell-title="{ row }">
        <div>
          <p class="font-medium text-app-text">{{ row.title }}</p>
          <p class="text-xs text-app-text-muted">{{ row.id }}</p>
          <p class="text-xs text-app-text-muted">{{ row.source_uri }}</p>
        </div>
      </template>

      <template #cell-status="{ row }">
        <DocumentStatusCell :status="row.status" />
      </template>

      <template #cell-error="{ row }">
        <div v-if="props.indexErrors?.[row.id]" class="space-y-1">
          <p class="line-clamp-2 text-xs text-danger">{{ props.indexErrors?.[row.id] }}</p>
          <details class="text-xs text-app-text-muted">
            <summary>details</summary>
            <p class="mt-1 whitespace-pre-wrap">{{ props.indexErrors?.[row.id] }}</p>
          </details>
        </div>
        <p v-else class="text-xs text-app-text-muted">-</p>
      </template>

      <template #cell-created="{ row }">
        <p class="text-sm text-app-text-muted">{{ toCreatedLabel(row.created_at) }}</p>
      </template>

      <template #cell-actions="{ row }">
        <Button
          :data-testid="row.status === 'failed' ? `retry-index-${row.id}` : `index-document-${row.id}`"
          size="sm"
          :variant="row.status === 'failed' ? 'destructive' : 'outline'"
          :disabled="Boolean(props.indexingMap?.[row.id])"
          @click="row.status === 'failed' ? emit('retry', row.id) : emit('index', row.id)"
        >
          {{ getActionLabel(row) }}
        </Button>
      </template>
    </DataTable>
  </section>
</template>
