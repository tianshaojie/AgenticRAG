<script setup lang="ts">
import { computed } from 'vue';

import type { ChatQueryResponse } from '../api/contracts';

import Badge from './ui/badge/Badge.vue';
import Card from './ui/card/Card.vue';

const props = defineProps<{
  response: ChatQueryResponse | null;
  loading?: boolean;
}>();

const answerState = computed(() => {
  const response = props.response;
  if (!response) {
    return 'default';
  }
  if (response.abstained) {
    return 'abstained';
  }
  if (response.uncertainty?.is_uncertain) {
    return 'uncertain';
  }
  return 'answered';
});
</script>

<template>
  <Card data-testid="answer-card">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold">Answer</h3>
      <Badge v-if="props.loading" tone="default">Streaming Placeholder</Badge>
      <Badge
        v-else-if="props.response"
        :tone="answerState === 'abstained' ? 'warning' : answerState === 'uncertain' ? 'danger' : 'success'"
      >
        {{ answerState === 'abstained' ? 'Abstained' : answerState === 'uncertain' ? 'Uncertain' : 'Answered' }}
      </Badge>
    </div>

    <div v-if="props.loading" class="mt-3 space-y-2">
      <p class="text-sm text-app-text-muted">Generating answer from retrieved evidence...</p>
      <div class="h-3 w-2/3 animate-pulse rounded bg-muted" />
      <div class="h-3 w-full animate-pulse rounded bg-muted" />
      <div class="h-3 w-5/6 animate-pulse rounded bg-muted" />
    </div>

    <p
      v-else-if="props.response"
      class="mt-3 whitespace-pre-wrap text-sm"
      :class="props.response.abstained ? 'text-warning-foreground' : 'text-app-text'"
    >
      {{ props.response.answer }}
    </p>

    <p v-if="!props.loading && props.response?.reason" class="mt-2 text-xs text-app-text-muted">
      reason: {{ props.response.reason }}
    </p>
    <p
      v-if="!props.loading && props.response?.uncertainty?.is_uncertain"
      class="mt-1 text-xs text-danger"
      data-testid="answer-uncertainty"
    >
      uncertainty: {{ props.response.uncertainty.reason }}
    </p>
  </Card>
</template>
