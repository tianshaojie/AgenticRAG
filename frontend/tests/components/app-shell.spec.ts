import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import AppShell from '../../src/components/AppShell.vue';

describe('AppShell', () => {
  it('renders route title and toggles sidebar collapse', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/documents',
          component: { template: '<div>documents</div>' },
          meta: { title: 'Documents', breadcrumbs: ['Workspace', 'Documents'] },
        },
        { path: '/chat', component: { template: '<div>chat</div>' } },
        { path: '/traces', component: { template: '<div>traces</div>' } },
        { path: '/evals', component: { template: '<div>evals</div>' } },
        { path: '/settings', component: { template: '<div>settings</div>' } },
      ],
    });

    await router.push('/documents');
    await router.isReady();

    const wrapper = mount(AppShell, {
      slots: {
        default: '<div>content</div>',
      },
      global: {
        plugins: [router],
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain('Documents');
    expect(wrapper.find('aside').classes()).toContain('w-[240px]');

    await wrapper.get('[data-testid="sidebar-collapse-button"]').trigger('click');
    expect(wrapper.find('aside').classes()).toContain('w-[74px]');
  });
});
