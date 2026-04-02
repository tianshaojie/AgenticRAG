<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { BookOpenText, BriefcaseBusiness, ChevronsUpDown, PanelLeft, RefreshCw } from 'lucide-vue-next';

import SidebarNav from './SidebarNav.vue';
import DropdownMenu from './ui/dropdown/DropdownMenu.vue';
import Sheet from './ui/sheet/Sheet.vue';
import Toaster from './ui/toast/Toaster.vue';
import Tooltip from './ui/tooltip/Tooltip.vue';
import { API_BASE_URL } from '../lib/http';

const route = useRoute();
const sidebarCollapsed = ref(false);
const mobileSidebarOpen = ref(false);

const pageTitle = computed(() => String(route.meta.title ?? 'Agentic RAG'));
const breadcrumbs = computed(() => {
  const value = route.meta.breadcrumbs;
  if (!Array.isArray(value) || value.length === 0) {
    return ['Workspace'];
  }
  return value.map((item) => String(item));
});
const shellHeaderHeightClass = 'h-[60px]';
const headerBreadcrumbs = computed(() => breadcrumbs.value);

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
}

function refreshCurrentPage() {
  window.location.reload();
}

function openApiDocs() {
  const target = `${API_BASE_URL.replace(/\/$/, '')}/docs`;
  window.open(target, '_blank');
}
</script>

<template>
  <div class="min-h-screen bg-app-bg text-app-text">
    <div class="flex min-h-screen">
      <aside
        class="sticky top-0 hidden h-screen border-r border-border bg-app-panel transition-all md:flex md:flex-col"
        :class="sidebarCollapsed ? 'w-[74px]' : 'w-[240px]'"
      >
        <div class="flex shrink-0 items-center border-b border-border px-3" :class="shellHeaderHeightClass">
          <div
            class="flex w-full items-center gap-2 rounded-xl px-2 py-2 transition-colors hover:bg-muted/45"
            :class="sidebarCollapsed ? 'justify-center' : 'justify-between'"
          >
            <div class="flex items-center gap-2">
              <span class="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-app-text text-app-bg">
                <BriefcaseBusiness class="h-4 w-4" aria-hidden="true" />
              </span>
              <div v-if="!sidebarCollapsed">
                <p class="text-sm font-semibold">Agentic RAG</p>
              </div>
            </div>
            <ChevronsUpDown v-if="!sidebarCollapsed" class="h-4 w-4 text-app-text-muted" aria-hidden="true" />
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-2">
          <SidebarNav :compact="sidebarCollapsed" />
        </div>
      </aside>

      <div class="flex min-w-0 flex-1 flex-col">
        <header class="sticky top-0 z-20 bg-app-panel/95 backdrop-blur">
          <div class="flex items-center justify-between gap-2 border-b border-border px-4" :class="shellHeaderHeightClass">
            <div class="flex items-center gap-2">
              <button
                class="rounded-md border border-border px-2 py-1 text-xs hover:bg-muted md:hidden"
                type="button"
                @click="mobileSidebarOpen = true"
              >
                <span class="inline-flex items-center gap-1">
                  <PanelLeft class="h-3.5 w-3.5" aria-hidden="true" />
                  Menu
                </span>
              </button>
              <Tooltip text="Collapse Sidebar">
                <button
                  class="hidden rounded-md border border-border p-2 text-xs hover:bg-muted md:inline-flex"
                  type="button"
                  data-testid="sidebar-collapse-button"
                  @click="toggleSidebar"
                >
                  <PanelLeft class="h-4 w-4" aria-hidden="true" />
                </button>
              </Tooltip>
              <div class="flex items-center gap-2" :aria-label="`Current section: ${pageTitle}`">
                <p v-if="headerBreadcrumbs.length > 0" class="text-sm text-app-text-muted whitespace-nowrap">
                  <span v-for="(item, idx) in headerBreadcrumbs" :key="`${item}-${idx}`">
                    <span v-if="idx > 0" class="mx-1">/</span>{{ item }}
                  </span>
                </p>
              </div>
            </div>

            <DropdownMenu>
              <template #trigger>
                <span class="inline-flex rounded-md border border-border px-2 py-1 text-xs hover:bg-muted">Quick Actions</span>
              </template>
              <template #default="{ close }">
                <button
                  class="block w-full rounded px-2 py-1 text-left text-xs hover:bg-muted"
                  @click="
                    refreshCurrentPage();
                    close();
                  "
                >
                  <span class="inline-flex items-center gap-1">
                    <RefreshCw class="h-3.5 w-3.5" aria-hidden="true" />
                    Refresh Current Page
                  </span>
                </button>
                <button
                  class="mt-1 block w-full rounded px-2 py-1 text-left text-xs hover:bg-muted"
                  @click="
                    openApiDocs();
                    close();
                  "
                >
                  <span class="inline-flex items-center gap-1">
                    <BookOpenText class="h-3.5 w-3.5" aria-hidden="true" />
                    Open API Docs
                  </span>
                </button>
              </template>
            </DropdownMenu>
          </div>
        </header>

        <main class="flex-1 p-4 md:p-6">
          <slot />
        </main>
      </div>
    </div>

    <Sheet :open="mobileSidebarOpen" title="Navigation" @close="mobileSidebarOpen = false">
      <SidebarNav @navigate="mobileSidebarOpen = false" />
    </Sheet>
    <Toaster />
  </div>
</template>
