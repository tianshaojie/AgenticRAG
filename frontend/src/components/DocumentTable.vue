<script setup lang="ts">
import type { DocumentRead, UUID } from '../api/contracts';

import Badge from './ui/badge/Badge.vue';
import Button from './ui/button/Button.vue';

const props = withDefaults(
  defineProps<{
    items: DocumentRead[];
    indexingMap?: Record<string, boolean>;
  }>(),
  {
    indexingMap: () => ({}),
  },
);

const emit = defineEmits<{
  index: [id: UUID];
}>();

function badgeTone(status: DocumentRead['status']) {
  if (status === 'indexed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'indexing') return 'warning';
  return 'default';
}
</script>

<template>
  <section class="rounded-lg border border-border bg-white p-4 shadow-sm">
    <h3 class="text-sm font-semibold text-slate-900">Documents</h3>

    <div class="mt-3 overflow-x-auto">
      <table class="min-w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-slate-200 text-left text-slate-500">
            <th class="px-2 py-2 font-medium">Title</th>
            <th class="px-2 py-2 font-medium">Status</th>
            <th class="px-2 py-2 font-medium">Created</th>
            <th class="px-2 py-2 font-medium">Action</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="doc in props.items" :key="doc.id" class="border-b border-slate-100">
            <td class="px-2 py-2">
              <p class="font-medium text-slate-800">{{ doc.title }}</p>
              <p class="text-xs text-slate-500">{{ doc.id }}</p>
            </td>
            <td class="px-2 py-2">
              <Badge :tone="badgeTone(doc.status)">{{ doc.status }}</Badge>
            </td>
            <td class="px-2 py-2 text-slate-600">{{ new Date(doc.created_at).toLocaleString() }}</td>
            <td class="px-2 py-2">
              <Button
                size="sm"
                variant="outline"
                :disabled="Boolean(props.indexingMap?.[doc.id])"
                @click="emit('index', doc.id)"
              >
                {{ props.indexingMap?.[doc.id] ? 'Indexing...' : 'Index' }}
              </Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
