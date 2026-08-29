<template>
  <!-- 05 §29/§31:Empty 与 Error 统一形态;error 提供 reload;不使用大插画 -->
  <div class="adm-state" :class="{ compact }">
    <template v-if="kind === 'empty'">
      <b>{{ title }}</b>
      <p v-if="description">{{ description }}</p>
      <div v-if="$slots.default" class="state-action">
        <slot />
      </div>
    </template>
    <template v-else>
      <b>{{ title || '加载失败' }}</b>
      <p v-if="description">{{ description }}</p>
      <div class="state-action">
        <button type="button" class="retry-btn" @click="$emit('reload')">重新加载</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  kind: 'empty' | 'error'
  title: string
  description?: string
  /** 表格内嵌时压缩留白 */
  compact?: boolean
}>()

defineEmits<{
  reload: []
}>()
</script>

<style scoped>
.adm-state {
  padding: 52px 20px;
  text-align: center;
  color: var(--adm-muted);
}
.adm-state.compact {
  padding: 34px 16px;
}
.adm-state b {
  display: block;
  color: var(--adm-text-2);
  font-size: 13px;
  margin-bottom: 6px;
}
.adm-state p {
  margin: 0;
  font-size: 12px;
}
.state-action {
  margin-top: 14px;
}
.retry-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid var(--adm-border-strong);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text);
  font-size: 12px;
  cursor: pointer;
}
.retry-btn:hover {
  border-color: var(--adm-text);
}
</style>
