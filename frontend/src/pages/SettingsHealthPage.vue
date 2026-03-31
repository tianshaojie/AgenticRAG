<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import Input from '../components/ui/input/Input.vue';
import { useHealth } from '../features/settings/useHealth';
import { useProviderSettings } from '../features/settings/useProviderSettings';
import { API_BASE_URL, API_TIMEOUT_MS } from '../lib/http';

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
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Settings / Health</h2>
        <p class="text-sm text-slate-600">Basic system status from FastAPI health endpoints.</p>
      </div>
      <Button variant="outline" @click="refresh">Refresh</Button>
    </header>

    <ErrorState v-if="healthError" :message="healthError" />
    <ErrorState v-if="providerError" :message="providerError" />
    <div v-if="providerSuccess" class="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
      {{ providerSuccess }}
    </div>
    <LoadingState v-if="loading" message="Checking backend status..." />

    <Card>
      <h3 class="text-sm font-semibold text-slate-900">Frontend Config Summary</h3>
      <ul class="mt-3 space-y-2">
        <li v-for="row in runtimeConfigRows" :key="row.key" class="rounded-md border border-slate-200 p-3">
          <p class="text-xs uppercase tracking-wide text-slate-500">{{ row.key }}</p>
          <p class="mt-1 text-sm text-slate-800">{{ row.value }}</p>
        </li>
      </ul>
    </Card>

    <Card>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-slate-900">LLM / Reranker Provider Settings</h3>
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

      <p class="mt-2 text-sm text-slate-600">
        API keys are independent and runtime-only. Restart backend if you want to reset them.
      </p>

      <div class="mt-3 grid gap-4 md:grid-cols-2">
        <section class="rounded-md border border-slate-200 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-semibold text-slate-900">LLM Provider</p>
            <Badge :tone="toTone(providerChecksByName.llm?.status ?? 'degraded')">
              {{ providerChecksByName.llm?.status ?? 'not_checked' }}
            </Badge>
          </div>
          <p class="mt-1 text-xs text-slate-500">
            provider: {{ providerSettings?.llm.provider ?? 'unknown' }} | model: {{ providerSettings?.llm.model ?? '-' }}
          </p>
          <p class="text-xs text-slate-500">
            key: {{ providerSettings?.llm.has_api_key ? `set (${providerSettings?.llm.api_key_last4})` : 'not set' }}
          </p>
          <label class="mt-2 flex items-center gap-2 text-sm text-slate-700">
            <input v-model="enableRealLlmProvider" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
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
          <p v-if="providerChecksByName.llm" class="mt-2 text-xs text-slate-600">
            {{ providerChecksByName.llm.detail }}
          </p>
        </section>

        <section class="rounded-md border border-slate-200 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-semibold text-slate-900">Reranker Provider</p>
            <Badge :tone="toTone(providerChecksByName.reranker?.status ?? 'degraded')">
              {{ providerChecksByName.reranker?.status ?? 'not_checked' }}
            </Badge>
          </div>
          <p class="mt-1 text-xs text-slate-500">
            provider: {{ providerSettings?.reranker.provider ?? 'unknown' }} | model:
            {{ providerSettings?.reranker.model ?? '-' }}
          </p>
          <p class="text-xs text-slate-500">
            key:
            {{
              providerSettings?.reranker.has_api_key
                ? `set (${providerSettings?.reranker.api_key_last4})`
                : 'not set'
            }}
          </p>
          <label class="mt-2 flex items-center gap-2 text-sm text-slate-700">
            <input v-model="enableRealRerankerProvider" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
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
          <p v-if="providerChecksByName.reranker" class="mt-2 text-xs text-slate-600">
            {{ providerChecksByName.reranker.detail }}
          </p>
        </section>
      </div>

      <Button class="mt-3" :disabled="providerSaving" @click="onSaveProviderSettings">
        Save Runtime Provider Settings
      </Button>

      <p v-if="providerSettings" class="mt-2 text-xs text-slate-500">{{ providerSettings.note }}</p>
    </Card>

    <Card v-if="health">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-slate-900">/health</h3>
        <Badge :tone="toTone(health.status)">{{ health.status }}</Badge>
      </div>
      <p class="mt-2 text-sm text-slate-600">service: {{ health.service }}</p>
      <p class="text-sm text-slate-600">timestamp: {{ new Date(health.timestamp).toLocaleString() }}</p>
      <ul v-if="health.checks.length > 0" class="mt-3 space-y-2">
        <li v-for="check in health.checks" :key="`health-${check.name}`" class="rounded-md border border-slate-200 p-3">
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium text-slate-800">{{ check.name }}</p>
            <Badge :tone="toTone(check.status)">{{ check.status }}</Badge>
          </div>
          <p class="mt-1 text-sm text-slate-600">{{ check.detail }}</p>
        </li>
      </ul>
    </Card>

    <Card v-if="ready">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-slate-900">/ready</h3>
        <Badge :tone="toTone(ready.status)">{{ ready.status }}</Badge>
      </div>

      <ul class="mt-3 space-y-2">
        <li v-for="check in ready.checks" :key="check.name" class="rounded-md border border-slate-200 p-3">
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium text-slate-800">{{ check.name }}</p>
            <Badge :tone="toTone(check.status)">{{ check.status }}</Badge>
          </div>
          <p class="mt-1 text-sm text-slate-600">{{ check.detail }}</p>
        </li>
      </ul>

      <div v-if="Object.keys(ready.summary).length > 0" class="mt-3 rounded-md border border-slate-200 p-3">
        <p class="text-sm font-medium text-slate-800">Runtime Summary</p>
        <p class="mt-1 text-sm text-slate-600">requests: {{ ready.summary.request_count }}</p>
        <p class="text-sm text-slate-600">errors: {{ ready.summary.error_count }}</p>
        <p class="text-sm text-slate-600">abstain ratio: {{ ready.summary.abstain_ratio }}</p>
        <p class="text-sm text-slate-600">fallback ratio: {{ ready.summary.fallback_ratio }}</p>
      </div>
    </Card>

    <Card>
      <h3 class="text-sm font-semibold text-slate-900">Dependency Summary</h3>
      <div class="mt-3 grid gap-2 md:grid-cols-2">
        <section class="rounded-md border border-slate-200 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium text-slate-800">PostgreSQL</p>
            <Badge :tone="toTone(dependencySummary.database?.status ?? 'degraded')">
              {{ dependencySummary.database?.status ?? 'unknown' }}
            </Badge>
          </div>
          <p class="mt-1 text-sm text-slate-600">{{ dependencySummary.database?.detail ?? 'No database check yet.' }}</p>
        </section>

        <section class="rounded-md border border-slate-200 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium text-slate-800">pgvector</p>
            <Badge :tone="toTone(dependencySummary.pgvector?.status ?? 'degraded')">
              {{ dependencySummary.pgvector?.status ?? 'unknown' }}
            </Badge>
          </div>
          <p class="mt-1 text-sm text-slate-600">{{ dependencySummary.pgvector?.detail ?? 'No pgvector check yet.' }}</p>
        </section>
      </div>
    </Card>
  </section>
</template>
