import { computed, ref } from 'vue';

export type ToastTone = 'default' | 'success' | 'warning' | 'danger';

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
  createdAt: number;
}

const toasts = ref<ToastItem[]>([]);

function nextId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useToast() {
  const items = computed(() => toasts.value);

  function push(input: Omit<ToastItem, 'id' | 'createdAt'> & { durationMs?: number }) {
    const item: ToastItem = {
      id: nextId(),
      title: input.title,
      description: input.description,
      tone: input.tone,
      createdAt: Date.now(),
    };
    toasts.value = [item, ...toasts.value].slice(0, 6);

    const duration = Math.max(1200, input.durationMs ?? 3200);
    window.setTimeout(() => remove(item.id), duration);
    return item.id;
  }

  function remove(id: string) {
    toasts.value = toasts.value.filter((item) => item.id !== id);
  }

  return {
    items,
    push,
    remove,
  };
}
