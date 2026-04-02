<script setup lang="ts">
import { computed } from 'vue';

import { useToast } from '../../../lib/toast';

const { items, remove } = useToast();

const toneClass = computed(() => {
  return {
    default: 'border-border bg-white text-app-text',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
    danger: 'border-rose-200 bg-rose-50 text-rose-900',
  } as const;
});
</script>

<template>
  <div class="pointer-events-none fixed bottom-4 right-4 z-[120] flex w-[360px] max-w-[calc(100vw-2rem)] flex-col gap-2">
    <div
      v-for="item in items"
      :key="item.id"
      class="pointer-events-auto rounded-lg border p-3 shadow-soft"
      :class="toneClass[item.tone]"
      data-testid="toast-item"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="text-sm font-semibold">{{ item.title }}</p>
          <p v-if="item.description" class="mt-1 text-xs opacity-85">{{ item.description }}</p>
        </div>
        <button
          type="button"
          class="rounded px-1 text-xs opacity-70 hover:opacity-100"
          @click="remove(item.id)"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>
