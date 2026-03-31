import { describe, expect, it } from 'vitest';

import { apiClient } from '../src/api/client';

describe('frontend scaffold', () => {
  it('exposes minimal step3 api methods', () => {
    expect(typeof apiClient.uploadDocument).toBe('function');
    expect(typeof apiClient.listDocuments).toBe('function');
    expect(typeof apiClient.indexDocument).toBe('function');
    expect(typeof apiClient.chatQuery).toBe('function');
    expect(typeof apiClient.getChatTrace).toBe('function');
    expect(typeof apiClient.health).toBe('function');
    expect(typeof apiClient.ready).toBe('function');
  });
});
