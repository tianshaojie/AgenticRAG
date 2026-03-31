import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import { apiClient } from '../../src/api/client';
import AgentTracePage from '../../src/pages/AgentTracePage.vue';

vi.mock('../../src/api/client', () => ({
  apiClient: {
    getChatTrace: vi.fn(),
  },
}));

describe('AgentTracePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads trace from session_id query and renders timeline', async () => {
    vi.mocked(apiClient.getChatTrace).mockResolvedValueOnce({
      trace_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      session_id: '11111111-1111-1111-1111-111111111111',
      status: 'success',
      start_state: 'INIT',
      end_state: 'COMPLETE',
      started_at: '2026-03-31T08:00:00Z',
      finished_at: '2026-03-31T08:00:01Z',
      steps: [
        {
          step_order: 1,
          state: 'ANALYZE_QUERY',
          action: 'analyze',
          status: 'success',
          input_payload: {},
          output_payload: {},
          input_summary: 'analyze',
          output_summary: 'ok',
          fallback: false,
          latency_ms: 1,
          error_message: null,
          created_at: '2026-03-31T08:00:00Z',
        },
      ],
    });

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/traces', component: AgentTracePage }],
    });
    await router.push('/traces?session_id=11111111-1111-1111-1111-111111111111');
    await router.isReady();

    const wrapper = mount(AgentTracePage, {
      global: {
        plugins: [router],
      },
    });
    await flushPromises();

    expect(apiClient.getChatTrace).toHaveBeenCalledWith('11111111-1111-1111-1111-111111111111');
    expect(wrapper.text()).toContain('Agent Trace');
    expect(wrapper.text()).toContain('ANALYZE_QUERY');
  });
});
