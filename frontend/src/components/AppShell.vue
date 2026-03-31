<script setup lang="ts">
import SidebarNav from './SidebarNav.vue';
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-white text-slate-900">
    <div class="mx-auto grid max-w-7xl gap-6 p-6 md:grid-cols-[220px_1fr]">
      <aside class="h-fit rounded-lg border border-border bg-white p-4 shadow-sm">
        <h1 class="mb-4 text-base font-semibold">Agentic RAG</h1>
        <SidebarNav />
      </aside>

      <main class="space-y-4">
        <slot />
      </main>
    </div>
  </div>
</template>
