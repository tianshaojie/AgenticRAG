<script setup lang="ts">
import type { ChatQueryResponse } from '../api/contracts';

import Badge from './ui/badge/Badge.vue';
import Card from './ui/card/Card.vue';

const props = defineProps<{
  response: ChatQueryResponse | null;
  loading?: boolean;
}>();
</script>

<template>
  <Card data-testid="answer-card">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-slate-900">Answer</h3>
      <Badge v-if="props.loading" tone="default">Streaming Placeholder</Badge>
      <Badge v-else-if="props.response" :tone="props.response.abstained ? 'warning' : 'success'">
        {{ props.response.abstained ? 'Abstained' : 'Answered' }}
      </Badge>
    </div>

    <div v-if="props.loading" class="mt-3 space-y-2">
      <p class="text-sm text-slate-600">Generating answer from retrieved evidence...</p>
      <div class="h-3 w-2/3 animate-pulse rounded bg-slate-200" />
      <div class="h-3 w-full animate-pulse rounded bg-slate-200" />
      <div class="h-3 w-5/6 animate-pulse rounded bg-slate-200" />
    </div>

    <p
      v-else-if="props.response"
      class="mt-3 whitespace-pre-wrap text-sm"
      :class="props.response.abstained ? 'text-amber-800' : 'text-slate-800'"
    >
      {{ props.response.answer }}
    </p>

    <p v-if="!props.loading && props.response?.reason" class="mt-2 text-xs text-slate-500">
      reason: {{ props.response.reason }}
    </p>
  </Card>
</template>
