<script setup lang="ts">
import type { CitationDto } from '../api/contracts';

import EmptyState from './EmptyState.vue';
import Card from './ui/card/Card.vue';

const props = defineProps<{
  citations: CitationDto[];
}>();

function shortId(value: string): string {
  return value.slice(0, 8);
}
</script>

<template>
  <Card>
    <h3 class="text-sm font-semibold text-slate-900">Citations</h3>

    <EmptyState
      v-if="props.citations.length === 0"
      title="No citations"
      description="No evidence met the threshold for this answer."
    />

    <ul v-else class="mt-3 space-y-3">
      <li
        v-for="citation in props.citations"
        :key="citation.chunk_id"
        class="rounded-md border border-slate-200 bg-slate-50 p-3"
      >
        <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          <span>doc: {{ shortId(citation.document_id) }}</span>
          <span>chunk: {{ shortId(citation.chunk_id) }}</span>
          <span>score: {{ citation.score.toFixed(3) }}</span>
          <span>span: {{ citation.span.start_char }}-{{ citation.span.end_char }}</span>
        </div>

        <p class="mt-2 whitespace-pre-wrap text-sm text-slate-800">{{ citation.quote }}</p>
      </li>
    </ul>
  </Card>
</template>
