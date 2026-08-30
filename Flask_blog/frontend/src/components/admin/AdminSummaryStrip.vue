<template>
  <!-- 04 §14 / 05 §4:同一容器 + 1px border + 内部分隔,无彩色无 Icon,最多 4 项
       带 to 的条目可点击(如 待审核 → 审核页) -->
  <section class="summary-strip">
    <component
      :is="item.to ? 'router-link' : 'div'"
      v-for="item in items.slice(0, 4)"
      :key="item.label"
      :to="item.to"
      class="summary-item"
      :class="{ link: item.to }"
    >
      <div class="summary-label">{{ item.label }}</div>
      <div class="summary-value">{{ item.value }}</div>
      <div v-if="item.note" class="summary-note">{{ item.note }}</div>
    </component>
  </section>
</template>

<script setup lang="ts">
export interface SummaryItem {
  label: string
  value: string | number
  note?: string
  /** 可选跳转(如 待审核 → 审核页) */
  to?: string
}

defineProps<{
  items: SummaryItem[]
}>()
</script>

<style scoped>
.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
  margin-bottom: 16px;
}
.summary-item {
  padding: 15px 18px;
  border-right: 1px solid var(--adm-border);
}
.summary-item:last-child {
  border-right: 0;
}
.summary-label {
  font-size: 12px;
  color: var(--adm-muted);
}
.summary-value {
  margin-top: 5px;
  font-size: 24px;
  font-weight: 740;
  letter-spacing: -0.03em;
  color: var(--adm-text);
  font-variant-numeric: tabular-nums;
}
.summary-note {
  margin-top: 2px;
  font-size: 12px;
  color: var(--adm-muted);
}
.summary-item.link {
  cursor: pointer;
}
.summary-item.link:hover .summary-value {
  color: var(--adm-primary);
}
.summary-item.link:hover .summary-note {
  color: var(--adm-text-2);
}
@media (max-width: 1050px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .summary-item:nth-child(2) {
    border-right: 0;
  }
  .summary-item:nth-child(-n + 2) {
    border-bottom: 1px solid var(--adm-border);
  }
}
@media (max-width: 719.98px) {
  .summary-strip {
    grid-template-columns: 1fr;
  }
  .summary-item {
    border-right: 0;
    border-bottom: 1px solid var(--adm-border);
  }
  .summary-item:last-child {
    border-bottom: 0;
  }
}
</style>
