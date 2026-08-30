<template>
  <!-- 05 §12 Topic/Tag Pattern:轻量 pill;topic 可带边框,tone 可选强调色 -->
  <span class="adm-tag" :class="[tone, { bordered: bordered }]">{{ label }}</span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    /** neutral(默认灰) | blue(强调) | green | orange */
    tone?: 'neutral' | 'blue' | 'green' | 'orange'
    bordered?: boolean
  }>(),
  {
    tone: 'neutral',
    bordered: false,
  },
);
</script>

<style scoped>
.adm-tag {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 12px;
  white-space: nowrap;
  background: #f4f4f5;
  color: var(--adm-muted);
}
.adm-tag.blue {
  background: var(--adm-primary-soft);
  color: var(--adm-primary);
}
.adm-tag.green {
  background: var(--adm-success-soft);
  color: var(--adm-success);
}
.adm-tag.orange {
  background: var(--adm-warning-soft);
  color: var(--adm-warning);
}
.adm-tag.bordered {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
}
</style>
