import { createRouter, createWebHistory } from 'vue-router';

import AgentTracePage from '../pages/AgentTracePage.vue';
import ChatPage from '../pages/ChatPage.vue';
import DocumentManagementPage from '../pages/DocumentManagementPage.vue';
import EvalDashboardPage from '../pages/EvalDashboardPage.vue';
import SettingsHealthPage from '../pages/SettingsHealthPage.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/documents', component: DocumentManagementPage },
    { path: '/chat', component: ChatPage },
    { path: '/traces', component: AgentTracePage },
    { path: '/evals', component: EvalDashboardPage },
    { path: '/settings', component: SettingsHealthPage },
  ],
});

export default router;
