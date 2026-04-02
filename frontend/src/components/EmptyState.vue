<script setup lang="ts">
defineProps<{
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="rounded-lg border border-dashed border-border bg-app-panel-muted p-6 text-center">
    <h3 class="text-sm font-semibold text-app-text">{{ title }}</h3>
    <p class="mt-2 text-sm text-app-text-muted">{{ description }}</p>
  </div>
</template>
