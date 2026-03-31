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
    default: 'bg-slate-100 text-slate-700',
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-800',
    danger: 'bg-rose-100 text-rose-700',
  };

  return [base, toneMap[props.tone]].join(' ');
});
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
