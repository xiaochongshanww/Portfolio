<template>
  <!-- 05 §11 Status Pattern:Dot + Text,四类语义;状态不只靠颜色(带文字) -->
  <span class="adm-status" :class="kind">
    <i class="dot" aria-hidden="true" />
    <span>{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
/** 05 §11:success / warning / neutral / danger 四类,统一 Dot+Text */
defineProps<{
  kind: 'success' | 'warning' | 'neutral' | 'danger'
  label: string
}>()
</script>

<style scoped>
.adm-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: block;
  flex-shrink: 0;
}
.adm-status.success { color: var(--adm-success); }
.adm-status.success .dot { background: var(--adm-dot-success); }
.adm-status.warning { color: var(--adm-warning); }
.adm-status.warning .dot { background: var(--adm-dot-warning); }
.adm-status.neutral { color: var(--adm-muted); }
.adm-status.neutral .dot { background: var(--adm-dot-neutral); }
.adm-status.danger { color: var(--adm-danger); }
.adm-status.danger .dot { background: var(--adm-dot-danger); }
</style>
