<script setup lang="ts">
import { computed, onMounted } from 'vue';

import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import { useEvals } from '../features/evals/useEvals';

const { latest, loading, running, error, refreshLatest, runEval } = useEvals();

const summary = computed(() => {
  const value = latest.value?.summary;
  if (!value || typeof value !== 'object') {
    return null;
  }
  return value as Record<string, unknown>;
});

const answerSummary = computed(() => {
  const value = summary.value?.answer;
  if (!value || typeof value !== 'object') {
    return null;
  }
  return value as Record<string, unknown>;
});

const retrievalSummary = computed(() => {
  const value = summary.value?.retrieval;
  if (!value || typeof value !== 'object') {
    return null;
  }
  return value as Record<string, unknown>;
});

function toNumber(value: unknown): number {
  return typeof value === 'number' ? value : 0;
}

const recallAtK = computed(() => toNumber(retrievalSummary.value?.recall_at_k));
const hitRateAtK = computed(() => toNumber(retrievalSummary.value?.hit_rate_at_k));
const mrr = computed(() => toNumber(retrievalSummary.value?.mrr));
const citationIntegrityFailures = computed(() => toNumber(answerSummary.value?.citation_integrity_failures));

const unsupportedRate = computed(() => {
  return toNumber(answerSummary.value?.unsupported_answer_rate);
});

const unsupportedThreshold = computed(() => {
  return toNumber(answerSummary.value?.unsupported_answer_rate_warning_threshold);
});

const unsupportedOverThreshold = computed(() => unsupportedRate.value > unsupportedThreshold.value);

async function onRunEval() {
  await runEval({ dataset: 'golden_v1' });
}

onMounted(() => {
  void refreshLatest();
});
</script>

<template>
  <section class="space-y-4">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Eval Dashboard</h2>
        <p class="text-sm text-slate-600">Run regression evals and inspect retrieval/answer/agent quality gates.</p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" :disabled="loading || running" @click="refreshLatest">Refresh</Button>
        <Button data-testid="run-eval-button" :disabled="running" @click="onRunEval">
          {{ running ? 'Running...' : 'Run Eval' }}
        </Button>
      </div>
    </header>

    <ErrorState v-if="error" :message="error" title="Eval request failed" />
    <LoadingState v-if="loading" message="Loading eval summary..." />

    <EmptyState
      v-if="!loading && !latest"
      title="No eval run yet"
      description="Run eval to generate retrieval/answer/agent regression metrics."
    />

    <template v-else-if="latest && summary">
      <Card>
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-sm font-semibold text-slate-900">Latest Run</h3>
          <Badge :tone="summary.gate_passed ? 'success' : 'danger'">
            {{ summary.gate_passed ? 'Gate Passed' : 'Gate Failed' }}
          </Badge>
        </div>
        <p class="mt-2 text-sm text-slate-600">run: {{ latest.name }}</p>
        <p class="text-sm text-slate-600">dataset: {{ latest.dataset }}</p>
        <p class="text-sm text-slate-600">status: {{ latest.status }}</p>
        <p class="text-sm text-slate-600">total cases: {{ summary.total_cases }}</p>
        <p class="text-sm text-slate-600">pass rate: {{ Number(summary.pass_rate ?? 0).toFixed(2) }}</p>
      </Card>

      <Card>
        <h3 class="text-sm font-semibold text-slate-900">Key Metrics</h3>
        <p class="mt-2 text-sm text-slate-600">recall@k: {{ recallAtK.toFixed(3) }}</p>
        <p class="text-sm text-slate-600">hit rate@k: {{ hitRateAtK.toFixed(3) }}</p>
        <p class="text-sm text-slate-600">MRR: {{ mrr.toFixed(3) }}</p>
        <p class="text-sm text-slate-600">citation integrity failures: {{ citationIntegrityFailures }}</p>
        <p class="text-sm" :class="unsupportedOverThreshold ? 'text-red-600 font-medium' : 'text-slate-600'">
          unsupported answer rate: {{ unsupportedRate.toFixed(3) }}
          (warn threshold: {{ unsupportedThreshold.toFixed(3) }})
        </p>
      </Card>

      <Card>
        <h3 class="text-sm font-semibold text-slate-900">Failed Cases</h3>
        <ul v-if="latest.failed_cases.length > 0" class="mt-3 space-y-2">
          <li
            v-for="item in latest.failed_cases"
            :key="item.case_id"
            class="rounded-md border border-rose-200 bg-rose-50 p-3"
          >
            <p class="text-sm font-medium text-rose-900">{{ item.case_name }}</p>
            <p class="mt-1 text-sm text-rose-800">query: {{ item.query }}</p>
            <p class="mt-1 text-sm text-rose-800">reasons: {{ item.reasons.join(', ') }}</p>
          </li>
        </ul>
        <p v-else class="mt-2 text-sm text-slate-600">No failed cases in the latest run.</p>
      </Card>
    </template>
  </section>
</template>
