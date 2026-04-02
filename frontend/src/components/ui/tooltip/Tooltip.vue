<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    text: string;
    side?: 'top' | 'bottom';
  }>(),
  {
    side: 'top',
  },
);
</script>

<template>
  <span class="group relative inline-flex">
    <slot />
    <span
      class="pointer-events-none absolute left-1/2 z-30 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-app-text px-2 py-1 text-xs text-app-bg shadow-soft group-hover:block"
      :class="props.side === 'top' ? '-top-8' : 'top-8'"
    >
      {{ props.text }}
    </span>
  </span>
</template>
