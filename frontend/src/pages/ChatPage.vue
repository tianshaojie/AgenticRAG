<script setup lang="ts">
import AgentTracePanel from '../components/AgentTracePanel.vue';
import AnswerCard from '../components/AnswerCard.vue';
import ChatInput from '../components/ChatInput.vue';
import CitationList from '../components/CitationList.vue';
import EmptyState from '../components/EmptyState.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Button from '../components/ui/button/Button.vue';
import { useChat } from '../features/chat/useChat';

const { response, loading, error, ask, trace, traceLoading, traceError, loadTrace } = useChat();

async function onSubmit(payload: { query: string; top_k: number; score_threshold: number }) {
  await ask(payload);
}

async function onViewTrace() {
  if (!response.value) {
    return;
  }
  await loadTrace(response.value.session_id);
}
</script>

<template>
  <section class="space-y-4">
    <header>
      <h2 class="text-lg font-semibold">Chat</h2>
      <p class="text-sm text-slate-600">Submit a query, inspect answer status, and verify citations.</p>
    </header>

    <ChatInput :loading="loading" @submit="onSubmit" />

    <ErrorState v-if="error" :message="error" />
    <LoadingState v-if="loading" message="Querying backend..." />

    <template v-if="response">
      <AnswerCard :response="response" />
      <CitationList :citations="response.citations" />

      <div class="flex items-center gap-3">
        <Button data-testid="view-trace-button" variant="outline" @click="onViewTrace">
          {{ traceLoading ? 'Loading Trace...' : 'View Agent Trace' }}
        </Button>
      </div>

      <ErrorState v-if="traceError" :message="traceError" title="Trace load failed" />
      <LoadingState v-if="traceLoading" message="Loading trace..." />
      <AgentTracePanel v-else :trace="trace" />
    </template>

    <EmptyState
      v-else-if="!loading"
      title="No answer yet"
      description="Submit your first query to view answer and evidence citations."
    />
  </section>
</template>
