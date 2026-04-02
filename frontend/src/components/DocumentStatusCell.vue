<script setup lang="ts">
import type { DocumentStatus } from '../api/contracts';

import Badge from './ui/badge/Badge.vue';

const props = defineProps<{
  status: DocumentStatus;
}>();

function tone(status: DocumentStatus) {
  if (status === 'indexed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'indexing') return 'warning';
  return 'default';
}
</script>

<template>
  <span class="inline-flex items-center gap-2">
    <span
      class="status-dot"
      :class="props.status === 'indexed' ? 'status-dot-ok' : props.status === 'failed' ? 'status-dot-failed' : 'status-dot-degraded'"
    />
    <Badge :tone="tone(props.status)">{{ props.status }}</Badge>
  </span>
</template>
