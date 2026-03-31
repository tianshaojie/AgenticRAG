<script setup lang="ts">
defineProps<{
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
    <h3 class="text-sm font-semibold text-slate-700">{{ title }}</h3>
    <p class="mt-2 text-sm text-slate-500">{{ description }}</p>
  </div>
</template>
