import { describe, expect, it } from 'vitest';

import { apiClient } from '../src/api/client';

describe('frontend scaffold', () => {
  it('exposes api client methods', () => {
    expect(typeof apiClient.createDocument).toBe('function');
    expect(typeof apiClient.chatQuery).toBe('function');
    expect(typeof apiClient.health).toBe('function');
  });
});
