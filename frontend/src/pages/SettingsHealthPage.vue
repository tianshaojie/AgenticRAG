<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { SlidersHorizontal } from 'lucide-vue-next';

import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import Input from '../components/ui/input/Input.vue';
import Tabs from '../components/ui/tabs/Tabs.vue';
import { useHealth } from '../features/settings/useHealth';
import { useProviderSettings } from '../features/settings/useProviderSettings';
import { API_BASE_URL, API_TIMEOUT_MS } from '../lib/http';

const section = ref<'providers' | 'health'>('providers');

const { health, ready, loading: healthLoading, error: healthError, refresh: refreshHealth } = useHealth();
const {
  settings: providerSettings,
  checks: providerChecks,
  loading: providerLoading,
  saving: providerSaving,
  checking: providerChecking,
  error: providerError,
  success: providerSuccess,
  refreshSettings,
  saveSettings,
  checkConnectivity,
} = useProviderSettings();

const llmApiKeyInput = ref('');
const rerankerApiKeyInput = ref('');
const llmEndpointInput = ref('');
const llmModelInput = ref('');
const rerankerEndpointInput = ref('');
const rerankerModelInput = ref('');
const enableRealLlmProvider = ref(false);
const enableRealRerankerProvider = ref(false);

onMounted(() => {
  void refresh();
});

function toTone(status: 'ok' | 'degraded' | 'failed') {
  if (status === 'ok') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}

const loading = computed(() => healthLoading.value || providerLoading.value);

watch(
  providerSettings,
  (value) => {
    if (!value) {
      return;
    }
    enableRealLlmProvider.value = value.llm.enabled;
    enableRealRerankerProvider.value = value.reranker.enabled;
    llmEndpointInput.value = value.llm.endpoint ?? '';
    llmModelInput.value = value.llm.model ?? '';
    rerankerEndpointInput.value = value.reranker.endpoint ?? '';
    rerankerModelInput.value = value.reranker.model ?? '';
  },
  { immediate: true },
);

const sectionTabs = [
  { value: 'providers', label: 'Provider Runtime Settings' },
  { value: 'health', label: 'System Health & Readiness' },
];

const runtimeConfigRows = computed(() => [
  { key: 'API Base URL', value: API_BASE_URL },
  { key: 'HTTP Timeout', value: `${API_TIMEOUT_MS} ms` },
  { key: 'Environment', value: import.meta.env.MODE },
]);

const dependencySummary = computed(() => {
  const checks = ready.value?.checks ?? health.value?.checks ?? [];
  const database = checks.find((item) => item.name === 'database');
  const pgvector = checks.find((item) => item.name.includes('pgvector'));
  return {
    database,
    pgvector,
  };
});

const providerChecksByName = computed(() => {
  return providerChecks.value.reduce(
    (acc, item) => {
      acc[item.provider] = item;
      return acc;
    },
    {} as Record<string, (typeof providerChecks.value)[number]>,
  );
});

const providerCheckSummary = computed(() => {
  if (providerChecks.value.length === 0) {
    return 'No provider check executed yet.';
  }

  const lastChecked = providerChecks.value
    .map((item) => new Date(item.checked_at).getTime())
    .reduce((max, current) => Math.max(max, current), 0);
  const failedCount = providerChecks.value.filter((item) => item.status === 'failed').length;
  const fallbackCount = providerChecks.value.filter((item) => item.fallback_used).length;

  return `last check ${new Date(lastChecked).toLocaleString()} | failed ${failedCount} | fallback ${fallbackCount}`;
});

async function refresh() {
  await Promise.all([refreshHealth(), refreshSettings()]);
}

async function onSaveProviderSettings() {
  await saveSettings({
    llmApiKey: llmApiKeyInput.value,
    rerankerApiKey: rerankerApiKeyInput.value,
    llmEndpoint: llmEndpointInput.value,
    llmModel: llmModelInput.value,
    rerankerEndpoint: rerankerEndpointInput.value,
    rerankerModel: rerankerModelInput.value,
    enableRealLlmProvider: enableRealLlmProvider.value,
    enableRealRerankerProvider: enableRealRerankerProvider.value,
  });
  llmApiKeyInput.value = '';
  rerankerApiKeyInput.value = '';
}
</script>

<template>
  <section class="space-y-4">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="inline-flex items-center gap-2 text-xl font-semibold text-app-text">
          <SlidersHorizontal class="h-5 w-5" aria-hidden="true" />
          Settings / Health
        </h2>
        <p class="text-sm text-app-text-muted">Manage runtime providers and inspect system dependency readiness.</p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" @click="refresh">Refresh</Button>
      </div>
    </header>

    <Tabs v-model="section" :items="sectionTabs" />

    <ErrorState v-if="healthError" :message="healthError" />
    <ErrorState v-if="providerError" :message="providerError" />
    <div v-if="providerSuccess" class="rounded-md border border-success/30 bg-success/10 p-3 text-sm text-success">
      {{ providerSuccess }}
    </div>
    <LoadingState v-if="loading" message="Checking backend status..." />

    <template v-if="section === 'providers'">
      <Card>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-app-text">Provider Runtime Settings</h3>
            <p class="mt-1 text-sm text-app-text-muted">
              API keys are independent and runtime-only. Restart backend to reset keys.
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button variant="outline" :disabled="providerChecking" @click="checkConnectivity('llm')">
              Check LLM
            </Button>
            <Button variant="outline" :disabled="providerChecking" @click="checkConnectivity('reranker')">
              Check Reranker
            </Button>
            <Button variant="outline" :disabled="providerChecking" @click="checkConnectivity('all')">
              Check Both
            </Button>
          </div>
        </div>

        <p class="mt-3 text-xs text-app-text-muted">{{ providerCheckSummary }}</p>

        <div class="mt-3 grid gap-4 md:grid-cols-2">
          <section class="rounded-md border border-border bg-muted/20 p-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold text-app-text">LLM Provider</p>
              <Badge :tone="toTone(providerChecksByName.llm?.status ?? 'degraded')">
                {{ providerChecksByName.llm?.status ?? 'not_checked' }}
              </Badge>
            </div>
            <p class="mt-1 text-xs text-app-text-muted">
              provider: {{ providerSettings?.llm.provider ?? 'unknown' }} | model: {{ providerSettings?.llm.model ?? '-' }}
            </p>
            <p class="text-xs text-app-text-muted">
              key: {{ providerSettings?.llm.has_api_key ? `set (${providerSettings?.llm.api_key_last4})` : 'not set' }}
            </p>
            <label class="mt-2 flex items-center gap-2 text-sm text-app-text">
              <input v-model="enableRealLlmProvider" type="checkbox" class="h-4 w-4 rounded border-border" />
              Enable real LLM provider
            </label>
            <Input
              v-model="llmApiKeyInput"
              class="mt-2"
              type="password"
              autocomplete="off"
              placeholder="New LLM API key (leave empty to keep)"
            />
            <Input
              v-model="llmEndpointInput"
              class="mt-2"
              type="text"
              autocomplete="off"
              placeholder="LLM endpoint URL"
            />
            <Input
              v-model="llmModelInput"
              class="mt-2"
              type="text"
              autocomplete="off"
              placeholder="LLM model name"
            />
            <p v-if="providerChecksByName.llm" class="mt-2 text-xs text-app-text-muted">
              {{ providerChecksByName.llm.detail }}
            </p>
          </section>

          <section class="rounded-md border border-border bg-muted/20 p-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold text-app-text">Reranker Provider</p>
              <Badge :tone="toTone(providerChecksByName.reranker?.status ?? 'degraded')">
                {{ providerChecksByName.reranker?.status ?? 'not_checked' }}
              </Badge>
            </div>
            <p class="mt-1 text-xs text-app-text-muted">
              provider: {{ providerSettings?.reranker.provider ?? 'unknown' }} | model:
              {{ providerSettings?.reranker.model ?? '-' }}
            </p>
            <p class="text-xs text-app-text-muted">
              key:
              {{
                providerSettings?.reranker.has_api_key
                  ? `set (${providerSettings?.reranker.api_key_last4})`
                  : 'not set'
              }}
            </p>
            <label class="mt-2 flex items-center gap-2 text-sm text-app-text">
              <input v-model="enableRealRerankerProvider" type="checkbox" class="h-4 w-4 rounded border-border" />
              Enable real reranker provider
            </label>
            <Input
              v-model="rerankerApiKeyInput"
              class="mt-2"
              type="password"
              autocomplete="off"
              placeholder="New reranker API key (leave empty to keep)"
            />
            <Input
              v-model="rerankerEndpointInput"
              class="mt-2"
              type="text"
              autocomplete="off"
              placeholder="Reranker endpoint URL"
            />
            <Input
              v-model="rerankerModelInput"
              class="mt-2"
              type="text"
              autocomplete="off"
              placeholder="Reranker model name"
            />
            <p v-if="providerChecksByName.reranker" class="mt-2 text-xs text-app-text-muted">
              {{ providerChecksByName.reranker.detail }}
            </p>
          </section>
        </div>

        <Button class="mt-3" :disabled="providerSaving" @click="onSaveProviderSettings">
          Save Runtime Provider Settings
        </Button>
        <p v-if="providerSettings" class="mt-2 text-xs text-app-text-muted">{{ providerSettings.note }}</p>
      </Card>

      <Card>
        <h3 class="text-sm font-semibold text-app-text">Recent Check Details</h3>
        <ul v-if="providerChecks.length > 0" class="mt-3 grid gap-2 md:grid-cols-2">
          <li v-for="item in providerChecks" :key="item.provider" class="rounded-md border border-border p-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-medium text-app-text">{{ item.provider }}</p>
              <Badge :tone="toTone(item.status)">{{ item.status }}</Badge>
            </div>
            <p class="mt-1 text-xs text-app-text-muted">{{ item.detail }}</p>
            <p class="mt-1 text-xs text-app-text-muted">latency: {{ item.latency_ms ?? '-' }} ms</p>
            <p class="text-xs text-app-text-muted">fallback: {{ item.fallback_used ? 'yes' : 'no' }}</p>
          </li>
        </ul>
        <p v-else class="mt-2 text-sm text-app-text-muted">No check details available yet.</p>
      </Card>
    </template>

    <template v-else>
      <Card>
        <h3 class="text-sm font-semibold text-app-text">Frontend Config Summary</h3>
        <ul class="mt-3 space-y-2">
          <li v-for="row in runtimeConfigRows" :key="row.key" class="rounded-md border border-border p-3">
            <p class="text-xs uppercase tracking-wide text-app-text-muted">{{ row.key }}</p>
            <p class="mt-1 text-sm text-app-text">{{ row.value }}</p>
          </li>
        </ul>
      </Card>

      <div class="grid gap-4 xl:grid-cols-2">
        <Card v-if="health">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-app-text">/health</h3>
            <Badge :tone="toTone(health.status)">{{ health.status }}</Badge>
          </div>
          <p class="mt-2 text-sm text-app-text-muted">service: {{ health.service }}</p>
          <p class="text-sm text-app-text-muted">timestamp: {{ new Date(health.timestamp).toLocaleString() }}</p>
          <ul v-if="health.checks.length > 0" class="mt-3 space-y-2">
            <li v-for="check in health.checks" :key="`health-${check.name}`" class="rounded-md border border-border p-3">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-app-text">{{ check.name }}</p>
                <Badge :tone="toTone(check.status)">{{ check.status }}</Badge>
              </div>
              <p class="mt-1 text-sm text-app-text-muted">{{ check.detail }}</p>
            </li>
          </ul>
        </Card>

        <Card v-if="ready">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-app-text">/ready</h3>
            <Badge :tone="toTone(ready.status)">{{ ready.status }}</Badge>
          </div>

          <ul class="mt-3 space-y-2">
            <li v-for="check in ready.checks" :key="check.name" class="rounded-md border border-border p-3">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-app-text">{{ check.name }}</p>
                <Badge :tone="toTone(check.status)">{{ check.status }}</Badge>
              </div>
              <p class="mt-1 text-sm text-app-text-muted">{{ check.detail }}</p>
            </li>
          </ul>

          <div v-if="Object.keys(ready.summary).length > 0" class="mt-3 rounded-md border border-border p-3">
            <p class="text-sm font-medium text-app-text">Runtime Summary</p>
            <p class="mt-1 text-sm text-app-text-muted">requests: {{ ready.summary.request_count }}</p>
            <p class="text-sm text-app-text-muted">errors: {{ ready.summary.error_count }}</p>
            <p class="text-sm text-app-text-muted">abstain ratio: {{ ready.summary.abstain_ratio }}</p>
            <p class="text-sm text-app-text-muted">fallback ratio: {{ ready.summary.fallback_ratio }}</p>
          </div>
        </Card>
      </div>

      <Card>
        <h3 class="text-sm font-semibold text-app-text">Dependency Summary</h3>
        <div class="mt-3 grid gap-2 md:grid-cols-2">
          <section class="rounded-md border border-border p-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-medium text-app-text">PostgreSQL</p>
              <Badge :tone="toTone(dependencySummary.database?.status ?? 'degraded')">
                {{ dependencySummary.database?.status ?? 'unknown' }}
              </Badge>
            </div>
            <p class="mt-1 text-sm text-app-text-muted">{{ dependencySummary.database?.detail ?? 'No database check yet.' }}</p>
          </section>

          <section class="rounded-md border border-border p-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-medium text-app-text">pgvector</p>
              <Badge :tone="toTone(dependencySummary.pgvector?.status ?? 'degraded')">
                {{ dependencySummary.pgvector?.status ?? 'unknown' }}
              </Badge>
            </div>
            <p class="mt-1 text-sm text-app-text-muted">{{ dependencySummary.pgvector?.detail ?? 'No pgvector check yet.' }}</p>
          </section>
        </div>
      </Card>
    </template>
  </section>
</template>
