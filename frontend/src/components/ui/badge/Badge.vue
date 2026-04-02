<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    tone?: 'default' | 'success' | 'warning' | 'danger';
  }>(),
  {
    tone: 'default',
  },
);

const classes = computed(() => {
  const base = 'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium';
  const toneMap: Record<string, string> = {
    default: 'bg-muted text-app-text-muted',
    success: 'bg-success/15 text-success',
    warning: 'bg-warning/20 text-warning-foreground',
    danger: 'bg-danger/15 text-danger',
  };

  return [base, toneMap[props.tone]].join(' ');
});
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
