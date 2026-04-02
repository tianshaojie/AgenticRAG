<script setup lang="ts">
import type { TraceStepRead } from '../api/contracts';

import Badge from './ui/badge/Badge.vue';

const props = defineProps<{
  step: TraceStepRead;
  expanded: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
}>();

function statusTone(status: string) {
  if (status === 'success' || status === 'ok') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}
</script>

<template>
  <li
    class="rounded-md border bg-white p-3"
    :class="step.fallback ? 'border-warning/30' : step.error_message ? 'border-danger/30' : 'border-border'"
  >
    <button
      type="button"
      class="flex w-full flex-wrap items-center gap-2 text-left"
      data-testid="trace-step-toggle"
      @click="emit('toggle')"
    >
      <span class="text-sm font-medium text-app-text">#{{ step.step_order }} {{ step.state }}</span>
      <Badge :tone="statusTone(step.status)">{{ step.status }}</Badge>
      <Badge tone="default">{{ step.action }}</Badge>
      <span class="text-xs text-app-text-muted">{{ step.latency_ms ?? 0 }} ms</span>
      <Badge v-if="step.fallback" tone="warning">fallback</Badge>
      <span class="ml-auto text-xs text-primary">{{ expanded ? 'Collapse' : 'Expand' }}</span>
    </button>

    <div class="mt-2 text-xs text-app-text-muted">
      <p>in: {{ step.input_summary ?? '-' }}</p>
      <p>out: {{ step.output_summary ?? '-' }}</p>
      <p v-if="step.error_message" class="text-danger">error: {{ step.error_message }}</p>
    </div>

    <div v-if="expanded" class="mt-3 space-y-2 rounded-md border border-border bg-muted/20 p-2 text-xs">
      <p class="font-semibold text-app-text">Input Payload</p>
      <pre class="overflow-x-auto whitespace-pre-wrap text-app-text-muted">{{ JSON.stringify(step.input_payload, null, 2) }}</pre>
      <p class="font-semibold text-app-text">Output Payload</p>
      <pre class="overflow-x-auto whitespace-pre-wrap text-app-text-muted">{{ JSON.stringify(step.output_payload, null, 2) }}</pre>
    </div>
  </li>
</template>
