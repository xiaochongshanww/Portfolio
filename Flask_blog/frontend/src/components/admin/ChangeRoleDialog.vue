<template>
  <el-dialog
    :model-value="visible"
    title="修改用户角色"
    width="400px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form :model="form" label-width="80px">
      <el-form-item label="用户">
        <span>{{ user?.nickname || user?.email }}</span>
      </el-form-item>
      <el-form-item label="当前角色">
        <el-tag :type="getRoleType(user?.role)">
          {{ getRoleText(user?.role) }}
        </el-tag>
      </el-form-item>
      <el-form-item label="新角色" required>
        <el-select v-model="form.role" placeholder="选择新角色">
          <el-option label="作者" value="author" />
          <el-option label="编辑" value="editor" />
          <el-option label="管理员" value="admin" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button
        type="primary"
        :loading="loading"
        @click="confirm"
      >
        确认修改
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, watch } from 'vue';

const props = defineProps({
  visible: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  /** @type {any} */
  user: { type: Object, default: null }
});
const emit = defineEmits(['update:visible', 'confirm']);

const form = reactive({ role: '' });

// 打开时同步当前角色
watch(() => props.visible, (val) => {
  if (val && props.user) {
    form.role = props.user.role;
  }
});

function confirm() {
  if (!form.role) return;
  emit('confirm', form.role);
}

/**
 * @param {string | undefined} role
 * @returns {'info' | 'success' | 'primary' | 'warning' | 'danger'}
 */
function getRoleType(role) {
  switch (role) {
    case 'admin': return 'danger';
    case 'editor': return 'warning';
    case 'author': return 'info';
    default: return 'info';
  }
}

/** @param {string | undefined} role */
function getRoleText(role) {
  switch (role) {
    case 'admin': return '管理员';
    case 'editor': return '编辑';
    case 'author': return '作者';
    default: return role;
  }
}
</script>
