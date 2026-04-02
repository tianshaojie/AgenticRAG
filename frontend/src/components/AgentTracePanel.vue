<script setup lang="ts">
import { computed, ref } from 'vue';

import type { TraceRead } from '../api/contracts';

import EmptyState from './EmptyState.vue';
import TraceStepItem from './TraceStepItem.vue';
import Badge from './ui/badge/Badge.vue';
import Card from './ui/card/Card.vue';
import Input from './ui/input/Input.vue';
import Tabs from './ui/tabs/Tabs.vue';

const props = defineProps<{
  trace: TraceRead | null;
}>();

const stateFilter = ref('');
const statusTab = ref('all');
const onlyFallback = ref(false);
const onlyError = ref(false);
const expandedSteps = ref<Record<number, boolean>>({});

function statusTone(status: string) {
  if (status === 'success' || status === 'ok') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}

const statusTabs = [
  { value: 'all', label: 'All' },
  { value: 'success', label: 'Success' },
  { value: 'failed', label: 'Failed' },
  { value: 'warning', label: 'Warning' },
];

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

const routeStep = computed(() => props.trace?.steps.find((step) => step.state === 'ROUTE') ?? null);
const critiqueStep = computed(() => props.trace?.steps.find((step) => step.state === 'CRITIQUE') ?? null);

const finalDecision = computed(() => {
  if (!props.trace) {
    return '-';
  }
  if (props.trace.end_state === 'ABSTAIN') {
    return 'abstain';
  }
  if (props.trace.end_state === 'COMPLETE') {
    return 'complete';
  }
  if (props.trace.status === 'failed' || props.trace.end_state === 'FAILED') {
    return 'failed';
  }
  return props.trace.end_state ?? 'unknown';
});

const filteredSteps = computed(() => {
  if (!props.trace) {
    return [];
  }

  return props.trace.steps.filter((step) => {
    const matchesState = !stateFilter.value || step.state.toLowerCase().includes(stateFilter.value.toLowerCase());
    const matchesStatus = statusTab.value === 'all' || step.status === statusTab.value;
    const matchesFallback = !onlyFallback.value || step.fallback;
    const matchesError = !onlyError.value || Boolean(step.error_message);
    return matchesState && matchesStatus && matchesFallback && matchesError;
  });
});

function toggleExpand(stepOrder: number) {
  expandedSteps.value[stepOrder] = !expandedSteps.value[stepOrder];
}
</script>

<template>
  <Card>
    <h3 class="text-sm font-semibold text-app-text">Agent Trace</h3>

    <EmptyState
      v-if="!props.trace"
      title="No trace loaded"
      description="Run a query and click 'View Trace' to inspect agent steps."
    />

    <template v-else>
      <div class="mt-3 flex flex-wrap items-center gap-2 text-sm text-app-text-muted">
        <span>trace: {{ props.trace.trace_id }}</span>
        <Badge :tone="statusTone(props.trace.status)">{{ props.trace.status }}</Badge>
      </div>

      <div class="mt-3 grid gap-2 rounded-md border border-border bg-muted/20 p-3 text-sm text-app-text md:grid-cols-2">
        <p>start_state: {{ props.trace.start_state }}</p>
        <p>end_state: {{ props.trace.end_state ?? '-' }}</p>
        <p>step_count: {{ props.trace.steps.length }}</p>
        <p>latency_total_ms: {{ totalLatencyMs }}</p>
        <p>fallback_steps: {{ fallbackCount }}</p>
        <p>error_steps: {{ errorCount }}</p>
        <p>final_decision: {{ finalDecision }}</p>
        <p>critique_reason: {{ critiqueStep?.output_payload.reason ?? '-' }}</p>
        <p>route_selected: {{ routeStep?.output_payload.selected_route ?? '-' }}</p>
        <p>route_provider: {{ routeStep?.output_payload.route_provider ?? '-' }}</p>
      </div>

      <div class="mt-4 space-y-2 rounded-md border border-border bg-muted/20 p-3">
        <div class="flex flex-wrap items-center gap-2">
          <Input v-model="stateFilter" class="w-full md:w-[220px]" placeholder="Filter by state" />
          <Tabs v-model="statusTab" :items="statusTabs" />
        </div>
        <div class="flex items-center gap-4 text-xs text-app-text-muted">
          <label class="inline-flex items-center gap-2">
            <input v-model="onlyFallback" type="checkbox" />
            Fallback only
          </label>
          <label class="inline-flex items-center gap-2">
            <input v-model="onlyError" type="checkbox" />
            Error only
          </label>
        </div>
      </div>

      <ul class="mt-4 space-y-3" data-testid="trace-timeline">
        <TraceStepItem
          v-for="step in filteredSteps"
          :key="`${step.step_order}-${step.state}`"
          :step="step"
          :expanded="Boolean(expandedSteps[step.step_order])"
          @toggle="toggleExpand(step.step_order)"
        />
      </ul>
    </template>
  </Card>
</template>
