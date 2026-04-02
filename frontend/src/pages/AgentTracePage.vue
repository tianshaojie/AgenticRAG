<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { Route } from 'lucide-vue-next';

import AgentTracePanel from '../components/AgentTracePanel.vue';
import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Button from '../components/ui/button/Button.vue';
import Input from '../components/ui/input/Input.vue';
import { useTrace } from '../features/traces/useTrace';

const { trace, loading, error, load } = useTrace();
const route = useRoute();
const sessionId = ref('');
const localError = ref<string | null>(null);

function normalizeSessionId(value: unknown): string {
  if (Array.isArray(value)) {
    return String(value[0] ?? '').trim();
  }
  return String(value ?? '').trim();
}

async function onLoadTrace() {
  localError.value = null;
  const value = sessionId.value.trim();
  if (!value) {
    localError.value = 'Please input a chat session ID.';
    return;
  }

  await load(value);
}

onMounted(async () => {
  const queryValue = normalizeSessionId(route.query.session_id);
  if (!queryValue) {
    return;
  }
  sessionId.value = queryValue;
  try {
    await onLoadTrace();
  } catch {
    // Error state is already handled in composable.
  }
});
</script>

<template>
  <section class="space-y-4">
    <header>
      <h2 class="inline-flex items-center gap-2 text-xl font-semibold text-app-text">
        <Route class="h-5 w-5" aria-hidden="true" />
        Agent Trace Viewer
      </h2>
      <p class="text-sm text-app-text-muted">Inspect finite-state steps, fallback path, latency, and final decision.</p>
    </header>

    <section class="rounded-lg border border-border bg-card p-4 shadow-soft">
      <h3 class="text-sm font-semibold text-app-text">Load Trace by Session</h3>
      <div class="mt-3 flex flex-col gap-2 md:flex-row">
        <Input
          v-model="sessionId"
          data-testid="trace-session-id-input"
          placeholder="chat session_id (UUID)"
        />
        <Button data-testid="trace-load-button" :disabled="loading" @click="onLoadTrace">
          {{ loading ? 'Loading...' : 'Load Trace' }}
        </Button>
      </div>
      <p v-if="localError" class="mt-2 text-sm text-danger">{{ localError }}</p>
    </section>

    <ErrorState v-if="error" :message="error" title="Trace request failed" />
    <LoadingState v-if="loading" message="Loading trace timeline..." />

    <AgentTracePanel v-else-if="trace" :trace="trace" />
    <EmptyState
      v-else
      title="No trace loaded"
      description="Enter a chat session_id or open this page from chat to load trace timeline."
    />
  </section>
</template>
