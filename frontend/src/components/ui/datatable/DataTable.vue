<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    columns: Array<{ key: string; label: string; widthClass?: string }>;
    rowKey?: string;
    rows: any[];
    emptyText?: string;
  }>(),
  {
    rowKey: 'id',
    emptyText: 'No records',
  },
);
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-border bg-white">
    <table class="min-w-full border-collapse text-sm">
      <thead>
        <tr class="border-b border-border bg-muted/70 text-left text-app-text-muted">
          <th
            v-for="column in props.columns"
            :key="column.key"
            class="px-3 py-2 text-xs font-semibold uppercase tracking-wide"
            :class="column.widthClass"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="props.rows.length === 0">
          <td :colspan="props.columns.length" class="px-3 py-5 text-center text-sm text-app-text-muted">
            {{ props.emptyText }}
          </td>
        </tr>
        <tr
          v-for="(row, index) in props.rows"
          v-else
          :key="String(row[props.rowKey] ?? index)"
          class="border-b border-border/80 last:border-b-0"
        >
          <td v-for="column in props.columns" :key="column.key" class="px-3 py-2 align-top">
            <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]" :index="index">
              {{ row[column.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
