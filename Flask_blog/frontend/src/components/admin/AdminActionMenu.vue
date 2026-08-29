<template>
  <!-- 05 §9/§28 Row Action Pattern:[主操作][···];菜单层级 Normal→State→sep→Danger -->
  <div class="row-actions">
    <slot />
    <el-dropdown
      v-if="$slots.menu"
      trigger="click"
      placement="bottom-end"
      :width="170"
      @visible-change="onVisible"
    >
      <button
        type="button"
        class="more-btn"
        :data-testid="`more-${testId}`"
        :aria-label="`更多操作:${testId}`"
        :aria-expanded="open"
      >···</button>
      <template #dropdown>
        <el-dropdown-menu class="action-menu">
          <slot name="menu" />
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  /** 用于测试与 aria-label 的实体标识 */
  testId: string
}>()

const open = ref(false)
function onVisible(v: boolean) {
  open.value = v
}
</script>

<style scoped>
.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.more-btn {
  width: 29px;
  height: 29px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-muted);
  font-size: 14px;
  letter-spacing: 1px;
  cursor: pointer;
}
.more-btn:hover {
  color: var(--adm-text-2);
  border-color: var(--adm-border-strong);
}
</style>

<style>
/* 菜单项 danger 语义(teleport 到 body,需全局) */
.action-menu .el-dropdown-menu__item.danger {
  color: var(--adm-danger, #b91c1c);
}
.action-menu .el-dropdown-menu__item.danger:not(.is-disabled):hover {
  color: var(--adm-danger, #b91c1c);
  background: var(--adm-danger-soft, #fef2f2);
}
</style>
