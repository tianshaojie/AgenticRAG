<script setup lang="ts">
import { computed, useAttrs } from 'vue';

const props = defineProps<{
  modelValue?: string | number | null;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const attrs = useAttrs();
const isFileInput = computed(() => attrs.type === 'file');

function onInput(event: Event) {
  if (isFileInput.value) {
    return;
  }

  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
}
</script>

<template>
  <input
    class="flex h-10 w-full rounded-md border border-input bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
    :value="isFileInput ? undefined : props.modelValue ?? ''"
    v-bind="attrs"
    @input="onInput"
  />
</template>
