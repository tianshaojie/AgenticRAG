<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { MessageSquareText } from 'lucide-vue-next';

import AgentTracePanel from '../components/AgentTracePanel.vue';
import AnswerCard from '../components/AnswerCard.vue';
import ChatInput from '../components/ChatInput.vue';
import EmptyState from '../components/EmptyState.vue';
import EvidenceCitationPanel from '../components/EvidenceCitationPanel.vue';
import ErrorState from '../components/ErrorState.vue';
import LoadingState from '../components/LoadingState.vue';
import Badge from '../components/ui/badge/Badge.vue';
import Button from '../components/ui/button/Button.vue';
import Card from '../components/ui/card/Card.vue';
import { useChat } from '../features/chat/useChat';
import { toChatAnswerVM } from '../types';

const router = useRouter();
const { response, loading, error, ask, trace, traceLoading, traceError, loadTrace, recentSessions, clearRecentSessions } =
  useChat();

const hasResponse = computed(() => Boolean(response.value));
const responseSessionId = computed(() => response.value?.session_id ?? null);
const answerVm = computed(() => (response.value ? toChatAnswerVM(response.value) : null));

async function onSubmit(payload: { query: string; top_k: number; score_threshold: number }) {
  await ask(payload);
}

async function onViewTrace() {
  if (!responseSessionId.value) {
    return;
  }
  await loadTrace(responseSessionId.value);
}

async function onLoadRecentTrace(sessionId: string) {
  await loadTrace(sessionId);
}

function onOpenTracePage(sessionId?: string) {
  const target = sessionId ?? responseSessionId.value;
  if (!target) {
    return;
  }
  void router.push({ path: '/traces', query: { session_id: target } });
}

function toSessionLabel(id: string): string {
  return id.slice(0, 8);
}
</script>

<template>
  <section class="space-y-4">
    <header>
      <h2 class="inline-flex items-center gap-2 text-xl font-semibold text-app-text">
        <MessageSquareText class="h-5 w-5" aria-hidden="true" />
        Chat Workspace
      </h2>
      <p class="text-sm text-app-text-muted">Ask questions, validate citations, and inspect agent trace quickly.</p>
    </header>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(360px,1fr)]">
      <section class="space-y-4">
        <ChatInput :loading="loading" @submit="onSubmit" />

        <ErrorState v-if="error" :message="error" />

        <Card v-if="loading">
          <LoadingState message="Retrieving evidence and preparing response..." />
          <p class="mt-2 text-xs text-app-text-muted">Streaming placeholder: response card updates after retrieval completes.</p>
        </Card>

        <template v-if="hasResponse">
          <AnswerCard :loading="loading" :response="response" />
          <Card v-if="answerVm" class="bg-muted/20">
            <div class="grid gap-2 text-xs text-app-text-muted md:grid-cols-2">
              <p>session_id: {{ answerVm.sessionId }}</p>
              <p>message_id: {{ answerVm.messageId }}</p>
              <p>citation_count: {{ answerVm.citationCount }}</p>
              <p>state: {{ answerVm.abstained ? 'abstained' : answerVm.uncertain ? 'uncertain' : 'answered' }}</p>
            </div>
          </Card>
        </template>

        <EmptyState
          v-else-if="!loading"
          title="No answer yet"
          description="Submit your first query to view answer and evidence citations."
        />
      </section>

      <section class="space-y-4">
        <Card>
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-app-text">Recent Sessions</h3>
            <Button variant="ghost" size="sm" :disabled="recentSessions.length === 0" @click="clearRecentSessions">
              Clear
            </Button>
          </div>

          <ul v-if="recentSessions.length > 0" class="mt-3 space-y-2">
            <li
              v-for="item in recentSessions"
              :key="item.sessionId"
              class="rounded-md border border-border bg-muted/20 p-2"
            >
              <div class="flex items-center justify-between gap-2">
                <p class="text-xs font-medium text-app-text">#{{ toSessionLabel(item.sessionId) }}</p>
                <Badge :tone="item.abstained ? 'warning' : 'success'">
                  {{ item.abstained ? 'abstained' : 'answered' }}
                </Badge>
              </div>
              <p class="mt-1 line-clamp-2 text-xs text-app-text-muted">{{ item.query }}</p>
              <p class="text-[11px] text-app-text-muted">{{ new Date(item.createdAt).toLocaleString() }}</p>

              <div class="mt-2 flex items-center gap-2">
                <Button size="sm" variant="outline" @click="onLoadRecentTrace(item.sessionId)">Load Trace</Button>
                <Button size="sm" variant="ghost" @click="onOpenTracePage(item.sessionId)">Open</Button>
              </div>
            </li>
          </ul>
          <p v-else class="mt-3 text-sm text-app-text-muted">No recent sessions yet.</p>
        </Card>

        <EvidenceCitationPanel
          v-if="hasResponse"
          :citations="response?.citations ?? []"
          :retrieval-results="response?.retrieval_results ?? []"
        />
        <Card v-else>
          <EmptyState
            title="Evidence Panel"
            description="Citations and retrieval snippets will appear here after a successful query."
          />
        </Card>

        <Card>
          <div class="flex flex-wrap items-center gap-2">
            <Button data-testid="view-trace-button" variant="outline" :disabled="!responseSessionId" @click="onViewTrace">
              {{ traceLoading ? 'Loading Trace...' : 'View Trace' }}
            </Button>
            <Button
              data-testid="open-trace-page-button"
              variant="outline"
              :disabled="!responseSessionId"
              @click="onOpenTracePage()"
            >
              Open Trace Page
            </Button>
          </div>
          <ErrorState v-if="traceError" class="mt-3" :message="traceError" title="Trace load failed" />
          <LoadingState v-if="traceLoading" class="mt-3" message="Loading trace..." />
          <AgentTracePanel v-else class="mt-3" :trace="trace" />
        </Card>
      </section>
    </div>
  </section>
</template>
