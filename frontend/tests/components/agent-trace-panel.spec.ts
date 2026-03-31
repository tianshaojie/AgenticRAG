import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import AgentTracePanel from '../../src/components/AgentTracePanel.vue';

describe('AgentTracePanel', () => {
  it('renders timeline, fallback and final decision summary', () => {
    const wrapper = mount(AgentTracePanel, {
      props: {
        trace: {
          trace_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
          session_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
          status: 'success',
          start_state: 'INIT',
          end_state: 'ABSTAIN',
          started_at: '2026-03-31T01:00:00Z',
          finished_at: '2026-03-31T01:00:02Z',
          steps: [
            {
              step_order: 1,
              state: 'RETRIEVE',
              action: 'retrieve_chunks',
              status: 'success',
              input_payload: {},
              output_payload: {},
              input_summary: 'retrieve',
              output_summary: 'ok',
              fallback: false,
              latency_ms: 20,
              error_message: null,
              created_at: '2026-03-31T01:00:00Z',
            },
            {
              step_order: 2,
              state: 'GENERATE_ANSWER',
              action: 'generate_answer',
              status: 'failed',
              input_payload: {},
              output_payload: {
                fallback: true,
                fallback_stage: 'generation',
              },
              input_summary: 'generate',
              output_summary: 'fallback',
              fallback: true,
              latency_ms: 35,
              error_message: 'timeout',
              created_at: '2026-03-31T01:00:01Z',
            },
          ],
        },
      },
    });

    expect(wrapper.get('[data-testid="trace-timeline"]').text()).toContain('#1 RETRIEVE');
    expect(wrapper.text()).toContain('fallback');
    expect(wrapper.text()).toContain('final_decision: abstain');
    expect(wrapper.text()).toContain('latency_total_ms: 55');
  });
});
