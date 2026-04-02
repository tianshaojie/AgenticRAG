<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

const open = ref(false);

function toggle() {
  open.value = !open.value;
}

function close() {
  open.value = false;
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    close();
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
});

defineExpose({ close });
</script>

<template>
  <div class="relative inline-block text-left">
    <button type="button" @click="toggle">
      <slot name="trigger" />
    </button>
    <div
      v-if="open"
      class="absolute right-0 z-40 mt-2 min-w-[180px] rounded-md border border-border bg-white p-1 shadow-panel"
      data-testid="dropdown-content"
    >
      <slot :close="close" />
    </div>
  </div>
</template>
