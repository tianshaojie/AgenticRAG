<script setup lang="ts">
import Skeleton from './ui/skeleton/Skeleton.vue';

defineProps<{
  message?: string;
}>();
</script>

<template>
  <div class="rounded-lg border border-border bg-white p-4">
    <p class="text-sm text-app-text-muted">{{ message ?? 'Loading...' }}</p>
    <div class="mt-3 space-y-2">
      <Skeleton class="h-3 w-2/3" />
      <Skeleton class="h-3 w-full" />
    </div>
  </div>
</template>
