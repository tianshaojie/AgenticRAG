<script setup lang="ts">
import { computed } from 'vue';

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

const totalLatencyMs = computed(() => {
  if (!props.trace) {
    return 0;
  }
  return props.trace.steps.reduce((acc, step) => acc + (step.latency_ms ?? 0), 0);
});

const fallbackCount = computed(() => {
  if (!props.trace) {
    return 0;
  }
  return props.trace.steps.filter((step) => step.fallback).length;
});

const errorCount = computed(() => {
  if (!props.trace) {
    return 0;
  }
  return props.trace.steps.filter((step) => Boolean(step.error_message)).length;
});

const finalDecision = computed(() => {
  if (!props.trace) {
    return '-';
  }
  if (props.trace.end_state === 'ABSTAIN') {
    return 'abstain';
  }
  if (props.trace.end_state === 'COMPLETE') {
    return 'answer_or_fallback_completed';
  }
  if (props.trace.status === 'failed' || props.trace.end_state === 'FAILED') {
    return 'failed';
  }
  return props.trace.end_state ?? 'unknown';
});
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
      <div class="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
        <span>trace: {{ props.trace.trace_id }}</span>
        <Badge :tone="statusTone(props.trace.status)">{{ props.trace.status }}</Badge>
      </div>

      <div class="mt-3 grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 md:grid-cols-2">
        <p>start_state: {{ props.trace.start_state }}</p>
        <p>end_state: {{ props.trace.end_state ?? '-' }}</p>
        <p>step_count: {{ props.trace.steps.length }}</p>
        <p>latency_total_ms: {{ totalLatencyMs }}</p>
        <p>fallback_steps: {{ fallbackCount }}</p>
        <p>error_steps: {{ errorCount }}</p>
        <p class="md:col-span-2">final_decision: {{ finalDecision }}</p>
      </div>

      <ul class="mt-4 space-y-3" data-testid="trace-timeline">
        <li
          v-for="step in props.trace.steps"
          :key="`${step.step_order}-${step.state}`"
          class="rounded-md border-l-4 border-slate-300 bg-slate-50 p-3"
          :class="step.fallback ? 'border-l-amber-400' : step.error_message ? 'border-l-rose-400' : 'border-l-sky-400'"
        >
          <div class="flex flex-wrap items-center gap-2 text-sm">
            <span class="text-sm font-medium text-slate-800">#{{ step.step_order }} {{ step.state }}</span>
            <Badge :tone="statusTone(step.status)">{{ step.status }}</Badge>
            <Badge tone="default">{{ step.action }}</Badge>
            <span class="text-xs text-slate-500">{{ step.latency_ms ?? 0 }} ms</span>
            <Badge v-if="step.fallback" tone="warning">fallback</Badge>
          </div>

          <p class="mt-2 text-xs text-slate-600">in: {{ step.input_summary ?? '-' }}</p>
          <p class="text-xs text-slate-600">out: {{ step.output_summary ?? '-' }}</p>
          <p v-if="step.fallback" class="text-xs text-amber-700">
            fallback: {{ step.output_payload.fallback_stage ?? 'generic' }}
            ({{ step.output_payload.fallback_reason ?? 'fallback_used' }})
          </p>
          <p v-if="step.error_message" class="mt-1 text-xs text-rose-600">error: {{ step.error_message }}</p>
        </li>
      </ul>
    </template>
  </Card>
</template>
