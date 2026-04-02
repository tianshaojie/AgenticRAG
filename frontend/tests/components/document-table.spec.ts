import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import DocumentTable from '../../src/components/DocumentTable.vue';
import type { DocumentRead } from '../../src/api/contracts';

const docs: DocumentRead[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    title: 'Policy',
    source_uri: 'upload://policy.md',
    mime_type: 'text/markdown',
    status: 'failed',
    metadata: {},
    created_at: '2026-03-31T01:00:00Z',
    updated_at: '2026-03-31T01:00:00Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    title: 'Runbook',
    source_uri: 'upload://runbook.md',
    mime_type: 'text/markdown',
    status: 'indexed',
    metadata: {},
    created_at: '2026-03-31T02:00:00Z',
    updated_at: '2026-03-31T02:00:00Z',
  },
];

describe('DocumentTable', () => {
  it('filters by status and emits batch retry for selected rows', async () => {
    const wrapper = mount(DocumentTable, {
      props: {
        items: docs,
        indexErrors: {
          '11111111-1111-1111-1111-111111111111': 'index failed',
        },
      },
    });

    await wrapper.get('[data-testid="document-status-filter"]').setValue('failed');
    await wrapper.get('[data-testid="documents-select-visible"]').trigger('click');
    await wrapper.get('[data-testid="documents-batch-retry"]').trigger('click');

    expect(wrapper.emitted('batchRetry')).toBeTruthy();
    expect(wrapper.emitted('batchRetry')?.[0]?.[0]).toEqual(['11111111-1111-1111-1111-111111111111']);
  });

  it('filters by search keyword', async () => {
    const wrapper = mount(DocumentTable, {
      props: {
        items: docs,
      },
    });

    await wrapper.get('[data-testid="document-search-input"]').setValue('Runbook');

    expect(wrapper.text()).toContain('Runbook');
    expect(wrapper.text()).not.toContain('Policy');
  });
});
