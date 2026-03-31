import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../src/api/client';
import EvalDashboardPage from '../../src/pages/EvalDashboardPage.vue';

vi.mock('../../src/api/client', () => ({
  apiClient: {
    getLatestEvalResult: vi.fn(),
    getEvalResult: vi.fn(),
    runEval: vi.fn(),
  },
}));

describe('EvalDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it('renders latest eval summary', async () => {
    vi.mocked(apiClient.getLatestEvalResult).mockResolvedValueOnce({
      eval_run_id: '11111111-1111-1111-1111-111111111111',
      name: 'latest-run',
      dataset: 'golden_v1',
      status: 'succeeded',
      summary: {
        dataset: 'golden_v1',
        total_cases: 3,
        passed_cases: 3,
        failed_cases: 0,
        pass_rate: 1,
        retrieval: {
          recall_at_k: 1,
          hit_rate_at_k: 1,
          mrr: 1,
        },
        answer: {
          unsupported_answer_rate: 0,
          unsupported_answer_rate_warning_threshold: 0.05,
          citation_integrity_failures: 0,
        },
        agent: {
          step_limit_violations: 0,
          rewrite_limit_violations: 0,
          fallback_visibility_failures: 0,
        },
        failed_case_samples: [],
        gate_passed: true,
      },
      failed_cases: [],
      started_at: '2026-03-31T01:00:00Z',
      finished_at: '2026-03-31T01:01:00Z',
    });

    const wrapper = mount(EvalDashboardPage);
    await flushPromises();

    expect(apiClient.getLatestEvalResult).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('latest-run');
    expect(wrapper.text()).toContain('Gate Passed');
    expect(wrapper.text()).toContain('recall@k');
  });

  it('runs eval and reloads result', async () => {
    vi.mocked(apiClient.getLatestEvalResult).mockRejectedValueOnce(new Error('no latest'));
    vi.mocked(apiClient.runEval).mockResolvedValueOnce({
      eval_run_id: '22222222-2222-2222-2222-222222222222',
      status: 'succeeded',
      accepted: true,
      summary: {
        gate_passed: true,
      },
    });
    vi.mocked(apiClient.getEvalResult).mockResolvedValueOnce({
      eval_run_id: '22222222-2222-2222-2222-222222222222',
      name: 'run-after-click',
      dataset: 'golden_v1',
      status: 'succeeded',
      summary: {
        dataset: 'golden_v1',
        total_cases: 1,
        passed_cases: 1,
        failed_cases: 0,
        pass_rate: 1,
        retrieval: { recall_at_k: 1, hit_rate_at_k: 1, mrr: 1 },
        answer: {
          unsupported_answer_rate: 0,
          unsupported_answer_rate_warning_threshold: 0.05,
          citation_integrity_failures: 0,
        },
        agent: {
          step_limit_violations: 0,
          rewrite_limit_violations: 0,
          fallback_visibility_failures: 0,
        },
        failed_case_samples: [],
        gate_passed: true,
      },
      failed_cases: [],
      started_at: '2026-03-31T01:00:00Z',
      finished_at: '2026-03-31T01:01:00Z',
    });

    const wrapper = mount(EvalDashboardPage);
    await flushPromises();

    await wrapper.get('[data-testid="run-eval-button"]').trigger('click');
    await flushPromises();

    expect(apiClient.runEval).toHaveBeenCalledTimes(1);
    expect(apiClient.getEvalResult).toHaveBeenCalledWith('22222222-2222-2222-2222-222222222222');
    expect(wrapper.text()).toContain('run-after-click');
  });
});
