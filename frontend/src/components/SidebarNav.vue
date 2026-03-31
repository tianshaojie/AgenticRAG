<script setup lang="ts">
import { RouterLink } from 'vue-router';

const items = [
  { label: 'Documents', to: '/documents' },
  { label: 'Chat', to: '/chat' },
  { label: 'Settings / Health', to: '/settings' },
];
</script>

<template>
  <nav class="space-y-2">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="block rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
      active-class="bg-slate-900 text-white hover:bg-slate-800"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>
