<script setup lang="ts">
import { ref } from 'vue';

import Button from './ui/button/Button.vue';
import Input from './ui/input/Input.vue';

interface UploadPayload {
  title: string;
  file: File;
  metadata?: Record<string, unknown>;
}

const props = withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  submit: [payload: UploadPayload];
}>();

const title = ref('');
const source = ref('');
const tags = ref('');
const selectedFile = ref<File | null>(null);
const localError = ref<string | null>(null);

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
}

function onSubmit() {
  localError.value = null;

  if (!title.value.trim()) {
    localError.value = 'Please input a document title.';
    return;
  }

  if (!selectedFile.value) {
    localError.value = 'Please select a txt or markdown file.';
    return;
  }

  const metadata: Record<string, unknown> = {};
  if (source.value.trim()) {
    metadata.source = source.value.trim();
  }

  if (tags.value.trim()) {
    metadata.tags = tags.value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  emit('submit', {
    title: title.value.trim(),
    file: selectedFile.value,
    metadata,
  });
}
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4 shadow-soft">
    <h3 class="text-sm font-semibold text-app-text">Upload Document</h3>

    <div class="mt-3 grid gap-3 md:grid-cols-2">
      <label class="space-y-1">
        <span class="text-xs text-app-text-muted">Title</span>
        <Input v-model="title" placeholder="Document title" />
      </label>

      <label class="space-y-1">
        <span class="text-xs text-app-text-muted">Source (optional)</span>
        <Input v-model="source" placeholder="policy-wiki" />
      </label>

      <label class="space-y-1">
        <span class="text-xs text-app-text-muted">Tags (optional, comma-separated)</span>
        <Input v-model="tags" placeholder="ops, runbook" />
      </label>

      <label class="space-y-1">
        <span class="text-xs text-app-text-muted">File (.txt/.md)</span>
        <Input accept=".txt,.md,text/plain,text/markdown" type="file" @change="onFileChange" />
      </label>
    </div>

    <p v-if="localError" class="mt-3 text-sm text-danger">{{ localError }}</p>

    <div class="mt-4">
      <Button :disabled="props.loading" @click="onSubmit">
        {{ props.loading ? 'Uploading...' : 'Upload' }}
      </Button>
    </div>
  </section>
</template>
