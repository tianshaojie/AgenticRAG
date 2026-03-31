import { createRouter, createWebHistory } from 'vue-router';

import ChatPage from '../pages/ChatPage.vue';
import DocumentManagementPage from '../pages/DocumentManagementPage.vue';
import SettingsHealthPage from '../pages/SettingsHealthPage.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/documents' },
    { path: '/documents', component: DocumentManagementPage },
    { path: '/chat', component: ChatPage },
    { path: '/settings', component: SettingsHealthPage },
  ],
});

export default router;
