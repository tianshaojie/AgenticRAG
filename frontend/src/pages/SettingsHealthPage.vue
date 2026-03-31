<script setup lang="ts">
import { onMounted } from 'vue';

import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import { useHealth } from '../features/settings/useHealth';

const { health, ready, loading, error, refresh } = useHealth();

onMounted(() => {
  void refresh();
});

function toTone(status: 'ok' | 'degraded' | 'failed') {
  if (status === 'ok') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
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

    <ErrorState v-if="error" :message="error" />
    <LoadingState v-if="loading" message="Checking backend status..." />

    <Card v-if="health">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-slate-900">/health</h3>
        <Badge :tone="toTone(health.status)">{{ health.status }}</Badge>
      </div>
      <p class="mt-2 text-sm text-slate-600">service: {{ health.service }}</p>
      <p class="text-sm text-slate-600">timestamp: {{ new Date(health.timestamp).toLocaleString() }}</p>
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
    </Card>
  </section>
</template>
