<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { CitationDto, RetrievalResultDto } from '../api/contracts';

import EmptyState from './EmptyState.vue';
import Badge from './ui/badge/Badge.vue';
import Button from './ui/button/Button.vue';
import Card from './ui/card/Card.vue';

const props = defineProps<{
  citations: CitationDto[];
  retrievalResults: RetrievalResultDto[];
}>();

const selectedChunkId = ref<string | null>(null);

watch(
  () => props.citations,
  (citations) => {
    if (!citations.length) {
      selectedChunkId.value = null;
      return;
    }

    if (!selectedChunkId.value || !citations.some((item) => item.chunk_id === selectedChunkId.value)) {
      selectedChunkId.value = citations[0].chunk_id;
    }
  },
  { immediate: true },
);

const retrievalByChunk = computed(() => {
  const index = new Map<string, RetrievalResultDto>();
  for (const item of props.retrievalResults) {
    index.set(item.chunk_id, item);
  }
  return index;
});

const selectedCitation = computed(() => {
  if (!selectedChunkId.value) {
    return null;
  }
  return props.citations.find((item) => item.chunk_id === selectedChunkId.value) ?? null;
});

const selectedRetrieval = computed(() => {
  if (!selectedChunkId.value) {
    return null;
  }
  return retrievalByChunk.value.get(selectedChunkId.value) ?? null;
});

function shortId(value: string): string {
  return value.slice(0, 8);
}

function selectCitation(chunkId: string): void {
  selectedChunkId.value = chunkId;
}

function jumpToSelection(): void {
  if (!selectedChunkId.value) {
    return;
  }

  const target = document.getElementById(`citation-${selectedChunkId.value}`);
  target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
</script>

<template>
  <Card>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-app-text">Evidence / Citation</h3>
      <Badge tone="default">{{ props.citations.length }} citations</Badge>
    </div>

    <EmptyState
      v-if="props.citations.length === 0"
      title="No evidence available"
      description="The answer has no citation above the configured threshold."
    />

    <div v-else class="mt-3 grid gap-4 lg:grid-cols-[300px_1fr]">
      <ul class="space-y-2" data-testid="citation-list">
        <li
          v-for="citation in props.citations"
          :id="`citation-${citation.chunk_id}`"
          :key="citation.chunk_id"
          class="rounded-md border p-3"
          :class="selectedChunkId === citation.chunk_id ? 'border-primary bg-primary/5' : 'border-border bg-muted/30'"
        >
          <button class="w-full text-left" type="button" @click="selectCitation(citation.chunk_id)">
            <div class="flex flex-wrap items-center gap-2">
              <Badge tone="default">doc {{ shortId(citation.document_id) }}</Badge>
              <Badge tone="default">chunk {{ shortId(citation.chunk_id) }}</Badge>
            </div>
            <p class="mt-2 line-clamp-2 text-sm text-app-text">{{ citation.quote }}</p>
            <p class="mt-1 text-xs text-app-text-muted">
              span: {{ citation.span.start_char }}-{{ citation.span.end_char }} | score:
              {{ citation.score.toFixed(3) }}
            </p>
          </button>
        </li>
      </ul>

      <section
        v-if="selectedCitation"
        class="rounded-md border border-border bg-card p-4"
        data-testid="evidence-detail"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="text-sm font-semibold text-app-text">Selected Evidence</h4>
          <Button size="sm" variant="outline" @click="jumpToSelection">Jump to Citation</Button>
        </div>

        <div class="mt-3 grid gap-2 text-sm text-app-text md:grid-cols-2">
          <p>document_id: <span class="font-mono text-xs">{{ selectedCitation.document_id }}</span></p>
          <p>chunk_id: <span class="font-mono text-xs">{{ selectedCitation.chunk_id }}</span></p>
          <p>span: {{ selectedCitation.span.start_char }}-{{ selectedCitation.span.end_char }}</p>
          <p>score: {{ selectedCitation.score.toFixed(3) }}</p>
        </div>

        <div class="mt-3 rounded-md border border-border bg-muted/30 p-3">
          <p class="text-xs uppercase tracking-wide text-app-text-muted">Citation Quote</p>
          <p class="mt-1 whitespace-pre-wrap text-sm text-app-text">{{ selectedCitation.quote }}</p>
        </div>

        <div v-if="selectedRetrieval" class="mt-3 rounded-md border border-border bg-muted/30 p-3">
          <p class="text-xs uppercase tracking-wide text-app-text-muted">Retrieved Chunk Preview</p>
          <p class="mt-1 whitespace-pre-wrap text-sm text-app-text">{{ selectedRetrieval.content_preview }}</p>
        </div>
      </section>
    </div>
  </Card>
</template>
