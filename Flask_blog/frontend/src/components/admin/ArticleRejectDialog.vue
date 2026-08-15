<template>
  <el-dialog 
    :model-value="visible" 
    title="拒绝发布" 
    width="500px"
    class="modern-dialog"
    @update:model-value="emit('update:visible', $event)"
  >
    <el-form :model="form" label-width="80px">
      <el-form-item label="拒绝原因" required>
        <el-input
          v-model="form.reason"
          type="textarea"
          :rows="4"
          placeholder="请输入拒绝发布的原因，这将帮助作者了解如何改进文章..."
          maxlength="500"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button 
        type="danger" 
        :loading="loading"
        @click="confirm"
      >
        确认拒绝
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, watch } from 'vue';
import { ElMessage } from 'element-plus';

const props = defineProps({
  visible: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
});
const emit = defineEmits(['update:visible', 'confirm']);

const form = reactive({ reason: '' });

// 打开时清空上一次的拒绝原因
watch(() => props.visible, (val) => {
  if (val) {
    form.reason = '';
  }
});

function confirm() {
  if (!form.reason.trim()) {
    ElMessage.warning('请输入拒绝原因');
    return;
  }
  emit('confirm', form.reason);
}
</script>
