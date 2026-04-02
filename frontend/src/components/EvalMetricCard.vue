<script setup lang="ts">
import Badge from './ui/badge/Badge.vue';
import Card from './ui/card/Card.vue';

withDefaults(
  defineProps<{
    label: string;
    value: string | number;
    hint?: string;
    tone?: 'default' | 'success' | 'warning' | 'danger';
  }>(),
  {
    hint: '',
    tone: 'default',
  },
);
</script>

<template>
  <Card>
    <div class="flex items-center justify-between gap-2">
      <p class="text-xs uppercase tracking-wide text-app-text-muted">{{ label }}</p>
      <Badge :tone="tone">{{ tone }}</Badge>
    </div>
    <p class="mt-2 text-2xl font-semibold text-app-text">{{ value }}</p>
    <p v-if="hint" class="mt-1 text-xs text-app-text-muted">{{ hint }}</p>
  </Card>
</template>
