import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import ChatPage from '../../src/pages/ChatPage.vue';
import { apiClient } from '../../src/api/client';

vi.mock('../../src/api/client', () => ({
  apiClient: {
    chatQuery: vi.fn(),
    getChatTrace: vi.fn(),
  },
}));

describe('ChatPage', () => {
  it('submits question and renders answer with evidence citations', async () => {
    vi.mocked(apiClient.chatQuery).mockResolvedValueOnce({
      session_id: '11111111-1111-1111-1111-111111111111',
      message_id: '22222222-2222-2222-2222-222222222222',
      answer: 'Based on evidence',
      citations: [
        {
          chunk_id: '33333333-3333-3333-3333-333333333333',
          document_id: '44444444-4444-4444-4444-444444444444',
          quote: 'quoted text',
          score: 0.93,
          span: {
            start_char: 10,
            end_char: 42,
          },
        },
      ],
      retrieval_results: [
        {
          chunk_id: '33333333-3333-3333-3333-333333333333',
          document_id: '44444444-4444-4444-4444-444444444444',
          score: 0.93,
          distance: 0.07,
          content_preview: 'retrieval preview',
        },
      ],
      abstained: false,
      reason: null,
      created_at: '2026-03-30T08:00:00Z',
    });

    const wrapper = mount(ChatPage);

    await wrapper.get('[data-testid="chat-query-input"]').setValue('How does retrieval work?');
    await wrapper.get('[data-testid="chat-submit-button"]').trigger('click');

    await flushPromises();

    expect(apiClient.chatQuery).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('Based on evidence');
    expect(wrapper.text()).toContain('quoted text');
    expect(wrapper.get('[data-testid="evidence-detail"]').text()).toContain('retrieval preview');
  });

  it('runs complete QA flow and loads trace from trace endpoint', async () => {
    vi.mocked(apiClient.chatQuery).mockResolvedValueOnce({
      session_id: '11111111-1111-1111-1111-111111111111',
      message_id: '22222222-2222-2222-2222-222222222222',
      answer: 'Based on evidence',
      citations: [
        {
          chunk_id: '33333333-3333-3333-3333-333333333333',
          document_id: '44444444-4444-4444-4444-444444444444',
          quote: 'quoted text',
          score: 0.93,
          span: {
            start_char: 10,
            end_char: 42,
          },
        },
      ],
      retrieval_results: [],
      abstained: false,
      reason: null,
      created_at: '2026-03-30T08:00:00Z',
    });
    vi.mocked(apiClient.getChatTrace).mockResolvedValueOnce({
      trace_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      session_id: '11111111-1111-1111-1111-111111111111',
      status: 'success',
      start_state: 'INIT',
      end_state: 'COMPLETE',
      started_at: '2026-03-30T08:00:00Z',
      finished_at: '2026-03-30T08:00:01Z',
      steps: [
        {
          step_order: 1,
          state: 'INIT',
          action: 'initialize',
          status: 'success',
          input_payload: {},
          output_payload: {},
          input_summary: 'initialize runtime',
          output_summary: 'ok',
          fallback: false,
          latency_ms: 1,
          error_message: null,
          created_at: '2026-03-30T08:00:00Z',
        },
      ],
    });

    const wrapper = mount(ChatPage);
    await wrapper.get('[data-testid="chat-query-input"]').setValue('show trace');
    await wrapper.get('[data-testid="chat-submit-button"]').trigger('click');
    await flushPromises();

    await wrapper.get('[data-testid="view-trace-button"]').trigger('click');
    await flushPromises();

    expect(apiClient.getChatTrace).toHaveBeenCalledTimes(1);
    expect(apiClient.getChatTrace).toHaveBeenCalledWith('11111111-1111-1111-1111-111111111111');
    expect(wrapper.text()).toContain('Based on evidence');
    expect(wrapper.text()).toContain('quoted text');
    expect(wrapper.text()).toContain('Agent Trace');
    expect(wrapper.text()).toContain('#1 INIT');
  });
});
