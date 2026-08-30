<template>
  <!-- 05 §5/§38/§39 Toolbar:Search + 高频筛选 | 结果数 + 刷新;与表格卡片一体(上圆角) -->
  <section class="admin-toolbar">
    <div class="tool-left">
      <div v-if="searchPlaceholder" class="search-box">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          :value="search"
          type="text"
          :placeholder="searchPlaceholder"
          :aria-label="searchPlaceholder"
          @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
        >
      </div>
      <slot name="filters" />
      <slot name="extra-actions" />
    </div>
    <div class="tool-right">
      <span v-if="resultCount != null" class="result-count">{{ resultCount }} 条结果</span>
      <button v-if="refreshable" type="button" class="ghost-btn" @click="$emit('refresh')">↻ 刷新</button>
      <slot name="right" />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  search?: string
  /** Placeholder 必须说明搜索范围(05 §6);不传则不渲染搜索框 */
  searchPlaceholder?: string
  resultCount?: number | null
  refreshable?: boolean
}>()

defineEmits<{
  'update:search': [value: string]
  refresh: []
}>()
</script>

<style scoped>
.admin-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container) var(--adm-r-container) 0 0;
  background: var(--adm-surface);
}
.tool-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  flex-wrap: wrap;
}
.search-box {
  position: relative;
  width: min(360px, 38vw);
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 8px;
  color: var(--adm-muted-light);
  font-size: 13px;
  pointer-events: none;
}
.search-box input {
  width: 100%;
  height: 34px;
  padding: 0 12px 0 30px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  outline: none;
  color: var(--adm-text);
  font-size: 13px;
}
.search-box input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}
.tool-right {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--adm-muted);
  font-size: 12px;
  flex-shrink: 0;
}
.result-count {
  font-variant-numeric: tabular-nums;
}
.ghost-btn {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 13px;
  cursor: pointer;
}
.ghost-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}
@media (max-width: 719.98px) {
  .admin-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .search-box {
    width: 100%;
  }
}
</style>
