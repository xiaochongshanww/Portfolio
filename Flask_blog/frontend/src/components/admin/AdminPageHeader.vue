<template>
  <section class="page-head">
    <div class="page-title">
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <!-- 04 §8:每页最多一个 Primary Action,业务动作属于 PageHeader -->
    <div v-if="$slots.default" class="page-actions">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
/** PageHeader Pattern(05 §3):Title + Description + Primary Action,不进 Card */
defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped>
/* 04 V2 §7:Page Title 26-28px,Description 13-14px(原型 pagehead) */
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}
.page-title h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: -0.04em;
  color: var(--adm-text);
}
.page-title p {
  margin: 8px 0 0;
  color: var(--adm-muted);
  font-size: 14px;
}
.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
@media (max-width: 719.98px) {
  .page-title p {
    display: none;
  }
}
</style>
