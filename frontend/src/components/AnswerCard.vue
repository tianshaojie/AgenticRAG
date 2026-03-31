<script setup lang="ts">
import type { ChatQueryResponse } from '../api/contracts';

import Badge from './ui/badge/Badge.vue';
import Card from './ui/card/Card.vue';

const props = defineProps<{
  response: ChatQueryResponse;
}>();
</script>

<template>
  <Card data-testid="answer-card">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-slate-900">Answer</h3>
      <Badge :tone="props.response.abstained ? 'warning' : 'success'">
        {{ props.response.abstained ? 'Abstained' : 'Answered' }}
      </Badge>
    </div>

    <p
      class="mt-3 whitespace-pre-wrap text-sm"
      :class="props.response.abstained ? 'text-amber-800' : 'text-slate-800'"
    >
      {{ props.response.answer }}
    </p>

    <p v-if="props.response.reason" class="mt-2 text-xs text-slate-500">
      reason: {{ props.response.reason }}
    </p>
  </Card>
</template>
