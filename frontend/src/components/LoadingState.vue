<script setup lang="ts">
defineProps<{
  message?: string;
}>();
</script>

<template>
  <div class="rounded-lg border border-border bg-white p-4">
    <p class="text-sm text-slate-600">{{ message ?? 'Loading...' }}</p>
  </div>
</template>
