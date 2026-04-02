<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    variant?: 'default' | 'outline' | 'destructive' | 'ghost';
    size?: 'sm' | 'md';
    disabled?: boolean;
    type?: 'button' | 'submit' | 'reset';
  }>(),
  {
    variant: 'default',
    size: 'md',
    disabled: false,
    type: 'button',
  },
);

const classes = computed(() => {
  const base = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60';

  const variantMap: Record<string, string> = {
    default: 'bg-primary text-primary-foreground hover:opacity-90',
    outline: 'border border-border bg-white text-app-text hover:bg-muted',
    destructive: 'bg-danger text-danger-foreground hover:opacity-90',
    ghost: 'bg-transparent text-app-text-muted hover:bg-muted hover:text-app-text',
  };

  const sizeMap: Record<string, string> = {
    sm: 'h-8 px-3 text-sm',
    md: 'h-10 px-4 text-sm',
  };

  return [base, variantMap[props.variant], sizeMap[props.size]].join(' ');
});
</script>

<template>
  <button :class="classes" :disabled="disabled" :type="type">
    <slot />
  </button>
</template>
