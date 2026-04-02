import { createRouter, createWebHistory } from 'vue-router';

import AgentTracePage from '../pages/AgentTracePage.vue';
import ChatPage from '../pages/ChatPage.vue';
import DocumentManagementPage from '../pages/DocumentManagementPage.vue';
import EvalDashboardPage from '../pages/EvalDashboardPage.vue';
import SettingsHealthPage from '../pages/SettingsHealthPage.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/documents' },
    {
      path: '/documents',
      name: 'documents',
      component: DocumentManagementPage,
      meta: { title: 'Documents', breadcrumbs: ['Workspace', 'Documents'] },
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatPage,
      meta: { title: 'Chat', breadcrumbs: ['Workspace', 'Chat'] },
    },
    {
      path: '/traces',
      name: 'traces',
      component: AgentTracePage,
      meta: { title: 'Traces', breadcrumbs: ['Observability', 'Traces'] },
    },
    {
      path: '/evals',
      name: 'evals',
      component: EvalDashboardPage,
      meta: { title: 'Evals', breadcrumbs: ['Observability', 'Evals'] },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsHealthPage,
      meta: { title: 'Settings', breadcrumbs: ['System', 'Settings'] },
    },
  ],
});

export default router;
