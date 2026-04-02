import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../src/api/client';
import DocumentManagementPage from '../../src/pages/DocumentManagementPage.vue';

vi.mock('../../src/api/client', () => ({
  apiClient: {
    listDocuments: vi.fn(),
    uploadDocument: vi.fn(),
    indexDocument: vi.fn(),
  },
}));

describe('DocumentManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders documents and retries failed indexing', async () => {
    vi.mocked(apiClient.listDocuments).mockResolvedValue({
      items: [
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
      ],
      total: 1,
    });
    vi.mocked(apiClient.indexDocument).mockResolvedValue({
      document_id: '11111111-1111-1111-1111-111111111111',
      status: 'indexed',
      chunk_count: 1,
      vector_count: 1,
    });

    const wrapper = mount(DocumentManagementPage);
    await flushPromises();

    expect(wrapper.text()).toContain('Policy');
    expect(wrapper.text()).toContain('Failed Indexing Summary');
    expect(wrapper.text()).toContain('Retry');

    await wrapper.get('[data-testid="retry-index-11111111-1111-1111-1111-111111111111"]').trigger('click');
    await flushPromises();

    expect(apiClient.indexDocument).toHaveBeenCalledWith('11111111-1111-1111-1111-111111111111', {});
  });
});
