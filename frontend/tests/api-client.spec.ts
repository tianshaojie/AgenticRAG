import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../src/api/client';
import { http } from '../src/lib/http';

vi.mock('../src/lib/http', () => ({
  http: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uploads document with multipart form', async () => {
    const file = new File(['hello'], 'doc.md', { type: 'text/markdown' });
    vi.mocked(http.post).mockResolvedValueOnce({
      data: {
        id: 'doc-1',
        title: 'Doc',
      },
    } as never);

    await apiClient.uploadDocument({
      title: 'Doc',
      file,
      metadata: { source: 'test' },
    });

    expect(http.post).toHaveBeenCalledTimes(1);
    const [path, formData] = vi.mocked(http.post).mock.calls[0];
    expect(path).toBe('/documents');
    expect(formData).toBeInstanceOf(FormData);

    const form = formData as FormData;
    expect(form.get('title')).toBe('Doc');
    expect((form.get('file') as File).name).toBe('doc.md');
    expect(form.get('metadata_json')).toBe(JSON.stringify({ source: 'test' }));
  });

  it('sends chat query payload', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: {
        session_id: 's1',
        message_id: 'm1',
        answer: 'a',
        citations: [],
        retrieval_results: [],
        abstained: false,
        reason: null,
        created_at: '2026-03-30T08:00:00Z',
      },
    } as never);

    await apiClient.chatQuery({
      query: 'what is this',
      top_k: 5,
      score_threshold: 0.2,
    });

    expect(http.post).toHaveBeenCalledWith('/chat/query', {
      query: 'what is this',
      top_k: 5,
      score_threshold: 0.2,
    });
  });
});
