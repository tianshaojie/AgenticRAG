<script setup lang="ts">
import type { TraceRead } from '../api/contracts';

import EmptyState from './EmptyState.vue';
import Badge from './ui/badge/Badge.vue';
import Card from './ui/card/Card.vue';

const props = defineProps<{
  trace: TraceRead | null;
}>();

function statusTone(status: string) {
  if (status === 'success' || status === 'ok') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}
</script>

<template>
  <Card>
    <h3 class="text-sm font-semibold text-slate-900">Agent Trace</h3>

    <EmptyState
      v-if="!props.trace"
      title="No trace loaded"
      description="Run a query and click 'View Trace' to inspect agent steps."
    />

    <template v-else>
      <div class="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-600">
        <span>trace: {{ props.trace.trace_id }}</span>
        <Badge :tone="statusTone(props.trace.status)">{{ props.trace.status }}</Badge>
        <span>start: {{ props.trace.start_state }}</span>
        <span>end: {{ props.trace.end_state ?? '-' }}</span>
      </div>

      <ul class="mt-4 space-y-2">
        <li
          v-for="step in props.trace.steps"
          :key="`${step.step_order}-${step.state}`"
          class="rounded-md border border-slate-200 bg-slate-50 p-3"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium text-slate-800">#{{ step.step_order }} {{ step.state }}</span>
            <Badge :tone="statusTone(step.status)">{{ step.status }}</Badge>
            <span class="text-xs text-slate-500">{{ step.latency_ms ?? 0 }} ms</span>
            <Badge v-if="step.fallback" tone="warning">fallback</Badge>
          </div>

          <p class="mt-2 text-xs text-slate-600">in: {{ step.input_summary ?? '-' }}</p>
          <p class="text-xs text-slate-600">out: {{ step.output_summary ?? '-' }}</p>
          <p v-if="step.error_message" class="mt-1 text-xs text-rose-600">error: {{ step.error_message }}</p>
        </li>
      </ul>
    </template>
  </Card>
</template>
