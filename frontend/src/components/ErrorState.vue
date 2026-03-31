<script setup lang="ts">
defineProps<{
  title?: string;
  message: string;
}>();
</script>

<template>
  <div class="rounded-lg border border-rose-200 bg-rose-50 p-4">
    <p class="text-sm font-semibold text-rose-700">{{ title ?? 'Request failed' }}</p>
    <p class="mt-1 text-sm text-rose-600">{{ message }}</p>
  </div>
</template>
