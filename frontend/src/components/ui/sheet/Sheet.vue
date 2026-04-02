<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    open: boolean;
    side?: 'left' | 'right';
    title?: string;
  }>(),
  {
    side: 'left',
    title: '',
  },
);

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <teleport to="body">
    <div v-if="props.open" class="fixed inset-0 z-50">
      <button class="absolute inset-0 bg-app-text/50" type="button" aria-label="Close" @click="emit('close')" />
      <aside
        class="absolute top-0 h-full w-[300px] bg-white p-4 shadow-panel"
        :class="props.side === 'left' ? 'left-0' : 'right-0'"
      >
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-app-text">{{ props.title }}</h3>
          <button type="button" class="rounded px-2 py-1 text-xs hover:bg-muted" @click="emit('close')">Close</button>
        </div>
        <slot />
      </aside>
    </div>
  </teleport>
</template>
