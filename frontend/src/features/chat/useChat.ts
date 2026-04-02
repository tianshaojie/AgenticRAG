import { ref } from 'vue';

import { apiClient } from '../../api/client';
import type { ChatQueryResponse, TraceRead, UUID } from '../../api/contracts';
import { parseApiError } from '../../lib/http';
import type { RecentSessionItem } from '../../types';

const RECENT_SESSIONS_KEY = 'agentic-rag:recent-sessions';
const MAX_RECENT_SESSIONS = 8;

function readRecentSessions(): RecentSessionItem[] {
  if (typeof window === 'undefined') {
    return [];
  }

  const raw = window.localStorage.getItem(RECENT_SESSIONS_KEY);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is RecentSessionItem => {
      return Boolean(item && typeof item === 'object' && typeof item.sessionId === 'string');
    });
  } catch {
    return [];
  }
}

function writeRecentSessions(value: RecentSessionItem[]): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(RECENT_SESSIONS_KEY, JSON.stringify(value));
}

export function useChat() {
  const response = ref<ChatQueryResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const trace = ref<TraceRead | null>(null);
  const traceLoading = ref(false);
  const traceError = ref<string | null>(null);

  const recentSessions = ref<RecentSessionItem[]>(readRecentSessions());

  function upsertRecentSession(item: RecentSessionItem): void {
    const deduped = recentSessions.value.filter((session) => session.sessionId !== item.sessionId);
    const next = [item, ...deduped].slice(0, MAX_RECENT_SESSIONS);
    recentSessions.value = next;
    writeRecentSessions(next);
  }

  function clearRecentSessions(): void {
    recentSessions.value = [];
    writeRecentSessions([]);
  }

  async function ask(payload: { query: string; top_k: number; score_threshold: number }) {
    loading.value = true;
    error.value = null;

    try {
      const next = await apiClient.chatQuery({
        query: payload.query,
        top_k: payload.top_k,
        score_threshold: payload.score_threshold,
        embedding_model: 'deterministic-local-v1',
      });
      response.value = next;
      trace.value = null;
      traceError.value = null;

      upsertRecentSession({
        sessionId: next.session_id,
        query: payload.query,
        createdAt: next.created_at,
        abstained: next.abstained,
        reason: next.reason ?? null,
      });
    } catch (err) {
      error.value = parseApiError(err);
    } finally {
      loading.value = false;
    }
  }

  async function loadTrace(sessionId: UUID) {
    traceLoading.value = true;
    traceError.value = null;

    try {
      trace.value = await apiClient.getChatTrace(sessionId);
    } catch (err) {
      traceError.value = parseApiError(err);
    } finally {
      traceLoading.value = false;
    }
  }

  return {
    response,
    loading,
    error,
    ask,
    trace,
    traceLoading,
    traceError,
    loadTrace,
    recentSessions,
    clearRecentSessions,
  };
}
