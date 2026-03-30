<template>
  <div class="min-h-screen bg-gradient-to-b from-sky-50 to-white text-slate-900">
    <header class="border-b border-slate-200 px-6 py-4">
      <h1 class="text-xl font-semibold">Agentic RAG Console (Step 1 Scaffold)</h1>
      <nav class="mt-3 flex flex-wrap gap-3 text-sm">
        <RouterLink class="rounded bg-slate-100 px-3 py-1" to="/documents">Documents</RouterLink>
        <RouterLink class="rounded bg-slate-100 px-3 py-1" to="/chat">Chat</RouterLink>
        <RouterLink class="rounded bg-slate-100 px-3 py-1" to="/traces">Traces</RouterLink>
        <RouterLink class="rounded bg-slate-100 px-3 py-1" to="/evals">Evals</RouterLink>
        <RouterLink class="rounded bg-slate-100 px-3 py-1" to="/settings">Settings/Health</RouterLink>
      </nav>
    </header>

    <main class="grid gap-4 p-6 md:grid-cols-[2fr_1fr]">
      <section class="rounded border border-slate-200 bg-white p-4">
        <RouterView />
      </section>
      <EvidenceCitationPanel />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
import EvidenceCitationPanel from './components/EvidenceCitationPanel.vue';
</script>
