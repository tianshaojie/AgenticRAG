import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import EvidenceCitationPanel from '../../src/components/EvidenceCitationPanel.vue';

describe('EvidenceCitationPanel', () => {
  it('renders citation list and switches selected evidence', async () => {
    const wrapper = mount(EvidenceCitationPanel, {
      props: {
        citations: [
          {
            chunk_id: '11111111-1111-1111-1111-111111111111',
            document_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            quote: 'first citation quote',
            score: 0.91,
            span: { start_char: 0, end_char: 20 },
          },
          {
            chunk_id: '22222222-2222-2222-2222-222222222222',
            document_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
            quote: 'second citation quote',
            score: 0.87,
            span: { start_char: 10, end_char: 35 },
          },
        ],
        retrievalResults: [
          {
            chunk_id: '11111111-1111-1111-1111-111111111111',
            document_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            score: 0.91,
            distance: 0.08,
            content_preview: 'preview one',
          },
          {
            chunk_id: '22222222-2222-2222-2222-222222222222',
            document_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
            score: 0.87,
            distance: 0.13,
            content_preview: 'preview two',
          },
        ],
      },
    });

    expect(wrapper.get('[data-testid="citation-list"]').text()).toContain('first citation quote');
    expect(wrapper.get('[data-testid="evidence-detail"]').text()).toContain('first citation quote');

    await wrapper.findAll('button').find((node) => node.text().includes('second citation quote'))?.trigger('click');

    expect(wrapper.get('[data-testid="evidence-detail"]').text()).toContain('second citation quote');
    expect(wrapper.text()).toContain('preview two');
  });

  it('shows empty state when no citation exists', () => {
    const wrapper = mount(EvidenceCitationPanel, {
      props: {
        citations: [],
        retrievalResults: [],
      },
    });

    expect(wrapper.text()).toContain('No evidence available');
  });
});
