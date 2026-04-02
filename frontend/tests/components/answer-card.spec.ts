import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import AnswerCard from '../../src/components/AnswerCard.vue';
import type { ChatQueryResponse } from '../../src/api/contracts';

function buildResponse(overrides?: Partial<ChatQueryResponse>): ChatQueryResponse {
  return {
    session_id: '11111111-1111-1111-1111-111111111111',
    message_id: '22222222-2222-2222-2222-222222222222',
    answer: 'Retrieved answer.',
    citations: [],
    retrieval_results: [],
    abstained: false,
    reason: null,
    created_at: '2026-03-30T08:00:00Z',
    ...overrides,
  };
}

describe('AnswerCard', () => {
  it('renders normal answer status', () => {
    const wrapper = mount(AnswerCard, {
      props: {
        response: buildResponse(),
      },
    });

    expect(wrapper.text()).toContain('Answered');
    expect(wrapper.text()).toContain('Retrieved answer.');
  });

  it('renders abstain status with reason', () => {
    const wrapper = mount(AnswerCard, {
      props: {
        response: buildResponse({
          abstained: true,
          answer: 'Insufficient evidence to answer reliably.',
          reason: 'insufficient_citation_count',
        }),
      },
    });

    expect(wrapper.text()).toContain('Abstained');
    expect(wrapper.text()).toContain('insufficient_citation_count');
  });

  it('renders uncertain status when conflict is detected', () => {
    const wrapper = mount(AnswerCard, {
      props: {
        response: buildResponse({
          uncertainty: {
            is_uncertain: true,
            reason: 'conflicting_evidence',
            conflict_type: 'cross_document_conflict',
            conflict_chunk_ids: ['chunk-a', 'chunk-b'],
          },
        }),
      },
    });

    expect(wrapper.text()).toContain('Uncertain');
    expect(wrapper.get('[data-testid="answer-uncertainty"]').text()).toContain('conflicting_evidence');
  });
});
