<script setup lang="ts">
import { ref } from 'vue';

import Button from './ui/button/Button.vue';
import Input from './ui/input/Input.vue';
import Textarea from './ui/textarea/Textarea.vue';

const props = withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  submit: [payload: { query: string; top_k: number; score_threshold: number }];
}>();

const query = ref('');
const topK = ref(5);
const scoreThreshold = ref(0.25);
const localError = ref<string | null>(null);

function onSubmit() {
  localError.value = null;
  const cleaned = query.value.trim();

  if (!cleaned) {
    localError.value = 'Please input a question.';
    return;
  }

  emit('submit', {
    query: cleaned,
    top_k: topK.value,
    score_threshold: scoreThreshold.value,
  });
}
</script>

<template>
  <section class="rounded-lg border border-border bg-card p-4 shadow-soft">
    <h3 class="text-sm font-semibold text-app-text">Ask a Question</h3>

    <div class="mt-3 space-y-3">
      <label class="space-y-1">
        <span class="text-xs text-app-text-muted">Query</span>
        <Textarea
          data-testid="chat-query-input"
          v-model="query"
          placeholder="Ask with enough detail to retrieve relevant evidence"
        />
      </label>

      <div class="grid gap-3 md:grid-cols-2">
        <label class="space-y-1">
          <span class="text-xs text-app-text-muted">Top K</span>
          <Input v-model.number="topK" min="1" max="50" step="1" type="number" />
        </label>

        <label class="space-y-1">
          <span class="text-xs text-app-text-muted">Score Threshold</span>
          <Input v-model.number="scoreThreshold" min="0" max="1" step="0.01" type="number" />
        </label>
      </div>
    </div>

    <p v-if="localError" class="mt-3 text-sm text-danger">{{ localError }}</p>

    <div class="mt-4">
      <Button data-testid="chat-submit-button" :disabled="props.loading" @click="onSubmit">
        {{ props.loading ? 'Querying...' : 'Submit Query' }}
      </Button>
    </div>
  </section>
</template>
