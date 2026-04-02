<script setup lang="ts">
import { computed } from 'vue';

interface TabItem {
  value: string;
  label: string;
}

const props = defineProps<{
  modelValue: string;
  items: TabItem[];
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const active = computed(() => props.modelValue);
</script>

<template>
  <div class="inline-flex items-center rounded-md border border-border bg-muted p-1">
    <button
      v-for="tab in props.items"
      :key="tab.value"
      type="button"
      class="rounded-sm px-3 py-1.5 text-xs font-medium transition"
      :class="active === tab.value ? 'bg-white text-app-text shadow-soft' : 'text-app-text-muted hover:text-app-text'"
      @click="emit('update:modelValue', tab.value)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
