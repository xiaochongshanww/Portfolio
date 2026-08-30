<template>
  <!-- 05 V2 补充 §5 驳回 Dialog:原因 select + 审核意见(原则上必填) -->
  <el-dialog
    :model-value="visible"
    title="驳回文章"
    width="480px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="reject-form">
      <label class="field-label">驳回原因 <span class="req">*</span></label>
      <select v-model="reason" class="reject-select" aria-label="驳回原因">
        <option value="内容需要补充">内容需要补充</option>
        <option value="标题与内容不符">标题与内容不符</option>
        <option value="结构需要调整">结构需要调整</option>
        <option value="质量不达标">质量不达标</option>
        <option value="其他">其他</option>
      </select>

      <label class="field-label">审核意见 <span class="req">*</span></label>
      <textarea
        v-model="comment"
        class="reject-textarea"
        rows="4"
        placeholder="请说明需要修改的内容……"
        aria-label="审核意见"
      />
    </div>
    <template #footer>
      <div class="reject-actions">
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button type="danger" :loading="loading" data-testid="reject-confirm" @click="confirm">
          确认驳回
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 05 V2 补充 §5:驳回必须带原因与审核意见。
 * 提交时合并为一段 reason 文本传给后端(reject_reason 字段)。
 */
import { ref, watch } from 'vue';
import { ElMessage } from 'element-plus';

const props = defineProps<{
  visible: boolean
  loading: boolean
}>();

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** @param {string} combined 原因 + 意见 合并文本 */
  confirm: [reason: string]
}>();

const reason = ref('内容需要补充');
const comment = ref('');

watch(
  () => props.visible,
  (v) => {
    if (v) {
      reason.value = '内容需要补充';
      comment.value = '';
    }
  },
);

function confirm() {
  if (!comment.value.trim()) {
    ElMessage.warning('请填写审核意见');
    return;
  }
  emit('confirm', `${reason.value}：${comment.value.trim()}`);
}
</script>

<style scoped>
.reject-form {
  display: grid;
  gap: 8px;
}
.field-label {
  font-size: 13px;
  font-weight: 650;
  color: var(--adm-text-2);
  margin-top: 4px;
}
.req {
  color: var(--adm-danger);
}
.reject-select {
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text);
  font-size: 13px;
  outline: none;
}
.reject-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}
.reject-textarea {
  padding: 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text);
  font-size: 13px;
  line-height: 1.7;
  outline: none;
  resize: vertical;
  font-family: inherit;
}
.reject-textarea:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}
.reject-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
