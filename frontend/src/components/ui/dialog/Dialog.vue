<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
  }>(),
  {
    open: false,
  },
);

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <teleport to="body">
    <div v-if="props.open" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <button class="absolute inset-0 bg-app-text/45" type="button" aria-label="Close" @click="emit('close')" />
      <section class="relative z-10 w-full max-w-lg rounded-lg border border-border bg-white p-4 shadow-panel">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-app-text">{{ props.title }}</h3>
          <button type="button" class="rounded px-2 py-1 text-xs hover:bg-muted" @click="emit('close')">Close</button>
        </div>
        <slot />
      </section>
    </div>
  </teleport>
</template>
