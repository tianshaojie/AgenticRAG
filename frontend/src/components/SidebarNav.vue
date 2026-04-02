<script setup lang="ts">
import type { Component } from 'vue';
import { RouterLink } from 'vue-router';
import { BarChart3, FileText, MessageSquareText, Route, Settings2 } from 'lucide-vue-next';

const props = withDefaults(
  defineProps<{
    compact?: boolean;
  }>(),
  {
    compact: false,
  },
);

const emit = defineEmits<{
  navigate: [];
}>();

interface SidebarNavItem {
  label: string;
  to: string;
  icon: Component;
}

interface SidebarNavGroup {
  label: string;
  items: SidebarNavItem[];
}

const groups: SidebarNavGroup[] = [
  {
    label: 'Workspace',
    items: [
      { label: 'Documents', to: '/documents', icon: FileText },
      { label: 'Chat', to: '/chat', icon: MessageSquareText },
    ],
  },
  {
    label: 'Observability',
    items: [
      { label: 'Traces', to: '/traces', icon: Route },
      { label: 'Evals', to: '/evals', icon: BarChart3 },
    ],
  },
  {
    label: 'System',
    items: [{ label: 'Settings', to: '/settings', icon: Settings2 }],
  },
];
</script>

<template>
  <nav class="space-y-4 px-2 py-2">
    <section
      v-for="(group, groupIndex) in groups"
      :key="group.label"
      class="space-y-1.5"
      :class="groupIndex > 0 ? 'pt-2' : ''"
    >
      <p
        v-if="!props.compact"
        class="flex h-8 items-center rounded-md px-2 text-xs font-medium text-app-text-muted/60"
      >
        {{ group.label }}
      </p>

      <RouterLink v-for="item in group.items" :key="item.to" :to="item.to" custom>
        <template #default="{ href, navigate, isActive }">
          <a
            :href="href"
            :data-active="isActive"
            :title="props.compact ? item.label : undefined"
            class="peer/menu-button flex w-full items-center overflow-hidden border border-transparent text-left text-sm text-app-text/90 outline-hidden transition-[width,height,padding,colors] hover:bg-muted/55 hover:text-app-text data-[active=true]:border-border data-[active=true]:bg-muted/85 data-[active=true]:font-medium data-[active=true]:text-app-text data-[active=true]:shadow-soft"
            :class="props.compact ? 'justify-center rounded-md p-2' : 'h-10 gap-2 rounded-md px-2.5'"
            @click="
              (event) => {
                navigate(event);
                emit('navigate');
              }
            "
          >
            <span class="inline-flex h-4 w-4 shrink-0 items-center justify-center">
              <component :is="item.icon" class="h-4 w-4 shrink-0" aria-hidden="true" />
            </span>
            <span v-if="!props.compact" class="truncate">{{ item.label }}</span>
          </a>
        </template>
      </RouterLink>
    </section>
  </nav>
</template>
