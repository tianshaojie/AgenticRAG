<script setup lang="ts">
defineProps<{
  title?: string;
  message: string;
}>();
</script>

<template>
  <div class="rounded-lg border border-danger/25 bg-danger/10 p-4">
    <p class="text-sm font-semibold text-danger">{{ title ?? 'Request failed' }}</p>
    <p class="mt-1 text-sm text-danger/90">{{ message }}</p>
  </div>
</template>
