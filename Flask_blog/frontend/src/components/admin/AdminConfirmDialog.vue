<template>
  <!-- 05 §33 Confirmation:明确对象 + 后果说明;危险按钮用 danger 语义 -->
  <el-dialog
    :model-value="visible"
    :width="width"
    :close-on-click-modal="false"
    :aria-label="title"
    @update:model-value="$emit('update:visible', $event)"
  >
    <template #header>
      <span class="confirm-title">{{ title }}</span>
    </template>
    <p class="confirm-message">{{ message }}</p>
    <template #footer>
      <div class="confirm-actions">
        <el-button @click="$emit('update:visible', false)">{{ cancelText }}</el-button>
        <el-button
          type="danger"
          :loading="loading"
          data-testid="confirm-danger"
          @click="$emit('confirm')"
        >{{ confirmText }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 05 §33 Confirmation Pattern:危险操作必须明确对象。
 * 用法:title 传「删除文章「xxx」?」,message 传后果说明。
 */
withDefaults(
  defineProps<{
    visible: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    loading?: boolean
    width?: string
  }>(),
  {
    confirmText: '确认',
    cancelText: '取消',
    loading: false,
    width: '440px',
  },
);

defineEmits<{
  'update:visible': [value: boolean]
  confirm: []
}>();
</script>

<style scoped>
.confirm-title {
  font-size: 15px;
  font-weight: 650;
  color: var(--adm-text);
}
.confirm-message {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--adm-text-2);
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
