<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { BarChart3 } from 'lucide-vue-next';

import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import EvalMetricCard from '../components/EvalMetricCard.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import DataTable from '../components/ui/datatable/DataTable.vue';
import { useEvals } from '../features/evals/useEvals';
import { toEvalSummaryVM } from '../types';

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

const agentSummary = computed(() => {
  const value = summary.value?.agent;
  if (!value || typeof value !== 'object') {
    return null;
  }
  return value as Record<string, unknown>;
});

const expandedFailed = ref<Record<string, boolean>>({});

function toNumber(value: unknown): number {
  return typeof value === 'number' ? value : 0;
}

const vm = computed(() => (latest.value ? toEvalSummaryVM(latest.value) : null));

const recallAtK = computed(() => toNumber(retrievalSummary.value?.recall_at_k));
const hitRateAtK = computed(() => toNumber(retrievalSummary.value?.hit_rate_at_k));
const mrr = computed(() => toNumber(retrievalSummary.value?.mrr));
const citationIntegrityFailures = computed(() => toNumber(answerSummary.value?.citation_integrity_failures));
const unsupportedRate = computed(() => toNumber(answerSummary.value?.unsupported_answer_rate));
const unsupportedThreshold = computed(() => toNumber(answerSummary.value?.unsupported_answer_rate_warning_threshold));
const stepLimitViolations = computed(() => toNumber(agentSummary.value?.step_limit_violations));
const rewriteLimitViolations = computed(() => toNumber(agentSummary.value?.rewrite_limit_violations));

const unsupportedOverThreshold = computed(() => unsupportedRate.value > unsupportedThreshold.value);

const gateFailures = computed(() => {
  const rows: string[] = [];
  if (citationIntegrityFailures.value > 0) {
    rows.push(`citation integrity failures: ${citationIntegrityFailures.value}`);
  }
  if (unsupportedOverThreshold.value) {
    rows.push(
      `unsupported answer rate ${unsupportedRate.value.toFixed(3)} above threshold ${unsupportedThreshold.value.toFixed(3)}`,
    );
  }
  if (stepLimitViolations.value > 0) {
    rows.push(`agent step limit violations: ${stepLimitViolations.value}`);
  }
  if (rewriteLimitViolations.value > 0) {
    rows.push(`agent rewrite limit violations: ${rewriteLimitViolations.value}`);
  }
  return rows;
});

const failedRows = computed(() => latest.value?.failed_cases ?? []);

const failedCaseColumns = [
  { key: 'case_name', label: 'Case' },
  { key: 'query', label: 'Query' },
  { key: 'reasons', label: 'Reasons' },
  { key: 'actions', label: 'Details', widthClass: 'w-[220px]' },
];

function toggleFailedCase(caseId: string): void {
  expandedFailed.value[caseId] = !expandedFailed.value[caseId];
}

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
        <h2 class="inline-flex items-center gap-2 text-xl font-semibold text-app-text">
          <BarChart3 class="h-5 w-5" aria-hidden="true" />
          Eval Dashboard
        </h2>
        <p class="text-sm text-app-text-muted">Track regression gate, retrieval quality, and citation integrity.</p>
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

    <template v-else-if="latest && summary && vm">
      <Card class="border-2" :class="vm.gatePassed ? 'border-success/40 bg-success/5' : 'border-danger/40 bg-danger/5'">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-app-text">Gate Status</h3>
            <p class="mt-1 text-sm text-app-text-muted">run {{ latest.name }} | dataset {{ latest.dataset }}</p>
            <p class="text-sm text-app-text-muted">
              {{ latest.started_at ? new Date(latest.started_at).toLocaleString() : '-' }}
            </p>
          </div>
          <Badge :tone="vm.gatePassed ? 'success' : 'danger'">
            {{ vm.gatePassed ? 'Gate Passed' : 'Gate Failed' }}
          </Badge>
        </div>

        <ul v-if="gateFailures.length > 0" class="mt-3 space-y-1">
          <li v-for="item in gateFailures" :key="item" class="text-sm text-danger">{{ item }}</li>
        </ul>
        <p v-else class="mt-3 text-sm text-success">No gate violations in latest run.</p>
      </Card>

      <section class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <EvalMetricCard label="Total Cases" :value="vm.totalCases" />
        <EvalMetricCard label="Pass Rate" :value="vm.passRate.toFixed(3)" :tone="vm.gatePassed ? 'success' : 'warning'" />
        <EvalMetricCard label="Recall@K" :value="recallAtK.toFixed(3)" hint="retrieval" />
        <EvalMetricCard label="Hit Rate@K" :value="hitRateAtK.toFixed(3)" hint="retrieval" />
        <EvalMetricCard label="MRR" :value="mrr.toFixed(3)" hint="retrieval" />
        <EvalMetricCard
          label="Citation Integrity Failures"
          :value="citationIntegrityFailures"
          :tone="citationIntegrityFailures > 0 ? 'danger' : 'success'"
        />
        <EvalMetricCard
          label="Unsupported Answer Rate"
          :value="unsupportedRate.toFixed(3)"
          :tone="unsupportedOverThreshold ? 'danger' : 'success'"
          :hint="`threshold ${unsupportedThreshold.toFixed(3)}`"
        />
        <EvalMetricCard
          label="Step Limit Violations"
          :value="stepLimitViolations"
          :tone="stepLimitViolations > 0 ? 'danger' : 'success'"
        />
        <EvalMetricCard
          label="Rewrite Limit Violations"
          :value="rewriteLimitViolations"
          :tone="rewriteLimitViolations > 0 ? 'danger' : 'success'"
        />
      </section>

      <Card>
        <h3 class="text-sm font-semibold text-app-text">Failed Cases</h3>
        <DataTable :columns="failedCaseColumns" :rows="failedRows" empty-text="No failed cases in latest run.">
          <template #cell-case_name="{ row }">
            <p class="text-sm font-medium text-app-text">{{ row.case_name }}</p>
            <p class="text-xs text-app-text-muted">{{ row.case_id }}</p>
          </template>

          <template #cell-query="{ row }">
            <p class="line-clamp-2 text-sm text-app-text-muted">{{ row.query }}</p>
          </template>

          <template #cell-reasons="{ row }">
            <p class="text-sm text-danger">{{ row.reasons.join(', ') }}</p>
          </template>

          <template #cell-actions="{ row }">
            <Button size="sm" variant="outline" @click="toggleFailedCase(row.case_id)">
              {{ expandedFailed[row.case_id] ? 'Hide' : 'Expand' }}
            </Button>
          </template>
        </DataTable>

        <ul class="mt-3 space-y-2">
          <li
            v-for="row in failedRows"
            v-show="expandedFailed[row.case_id]"
            :key="`${row.case_id}-details`"
            class="rounded-md border border-border bg-muted/30 p-3"
          >
            <p class="text-sm font-medium text-app-text">{{ row.case_name }}</p>
            <p class="mt-1 text-xs text-app-text-muted">reasons: {{ row.reasons.join(', ') }}</p>
            <pre class="mt-2 overflow-x-auto rounded bg-card p-2 text-xs text-app-text">{{ row.metrics }}</pre>
          </li>
        </ul>
      </Card>
    </template>
  </section>
</template>
