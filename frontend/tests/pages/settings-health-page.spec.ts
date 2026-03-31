import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../src/api/client';
import SettingsHealthPage from '../../src/pages/SettingsHealthPage.vue';

vi.mock('../../src/api/client', () => ({
  apiClient: {
    health: vi.fn(),
    ready: vi.fn(),
    getProviderSettings: vi.fn(),
    updateProviderSettings: vi.fn(),
    checkProviderConnectivity: vi.fn(),
  },
}));

describe('SettingsHealthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders health, readiness and dependency summaries', async () => {
    vi.mocked(apiClient.health).mockResolvedValueOnce({
      status: 'ok',
      service: 'agentic-rag-backend',
      timestamp: '2026-03-31T08:00:00Z',
      checks: [
        { name: 'database', status: 'ok', detail: 'database reachable' },
        { name: 'pgvector_extension', status: 'ok', detail: 'enabled' },
      ],
    });
    vi.mocked(apiClient.ready).mockResolvedValueOnce({
      status: 'ok',
      checks: [
        { name: 'database', status: 'ok', detail: 'database reachable' },
        { name: 'pgvector_similarity', status: 'ok', detail: 'query ok' },
      ],
      summary: {
        request_count: '10',
        error_count: '0',
        abstain_ratio: '0.1',
        fallback_ratio: '0.0',
      },
    });
    vi.mocked(apiClient.getProviderSettings).mockResolvedValueOnce({
      llm: {
        name: 'llm',
        provider: 'openai_compatible',
        enabled: false,
        has_api_key: false,
        api_key_last4: null,
        endpoint: 'https://agent.cnht.com.cn/v1/chat/completions',
        base_url: null,
        model: 'gpt-4o-mini',
        timeout_seconds: 15,
        max_retries: 2,
      },
      reranker: {
        name: 'reranker',
        provider: 'http',
        enabled: false,
        has_api_key: false,
        api_key_last4: null,
        endpoint: 'https://reranker.example.com/v1/rerank',
        base_url: null,
        model: 'qwen3-reranker-8b',
        timeout_seconds: 8,
        max_retries: 2,
      },
      note: 'runtime only',
    });

    const wrapper = mount(SettingsHealthPage);
    await flushPromises();

    expect(wrapper.text()).toContain('Frontend Config Summary');
    expect(wrapper.text()).toContain('LLM / Reranker Provider Settings');
    expect(wrapper.text()).toContain('Enable real LLM provider');
    expect(wrapper.text()).toContain('Enable real reranker provider');
    expect(wrapper.text()).toContain('/health');
    expect(wrapper.text()).toContain('/ready');
    expect(wrapper.text()).toContain('PostgreSQL');
    expect(wrapper.text()).toContain('pgvector');
  });
});
