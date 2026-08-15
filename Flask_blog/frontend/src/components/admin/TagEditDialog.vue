<template>
  <el-dialog
    :model-value="visible"
    :title="mode === 'create' ? '新建标签' : '编辑标签'"
    width="500px"
    class="modern-dialog"
    :show-close="false"
    align-center
    @update:model-value="$emit('update:visible', $event)"
    @close="resetForm"
  >
    <template #header>
      <div class="dialog-header">
        <div class="dialog-title">
          <el-icon size="24" class="dialog-icon"><Document /></el-icon>
          <span>{{ mode === 'create' ? '新建标签' : '编辑标签' }}</span>
        </div>
        <button class="dialog-close" @click="$emit('update:visible', false)">
          <el-icon size="18"><Close /></el-icon>
        </button>
      </div>
    </template>
    <el-form
      ref="formRef"
      :model="form"
      :rules="formRules"
      label-width="80px"
    >
      <el-form-item label="标签名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入标签名称"
          @input="generateSlug"
        />
      </el-form-item>

      <el-form-item label="Slug" prop="slug">
        <el-input
          v-model="form.slug"
          placeholder="URL友好的标识符，留空自动生成"
        >
          <template #suffix>
            <el-tooltip
              content="Slug用于URL中，只能包含小写字母、数字和连字符。中文标签名会自动转换为拼音。"
              placement="top"
            >
              <el-icon class="slug-help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
        </el-input>
        <div v-if="form.slug" class="slug-preview">
          <span class="preview-label">预览URL：</span>
          <code class="preview-url">/tag/{{ form.slug }}</code>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="modern-dialog-footer">
        <button class="dialog-btn secondary" @click="$emit('update:visible', false)">
          <span>取消</span>
        </button>
        <button
          :disabled="loading"
          class="dialog-btn primary"
          @click="handleSubmit"
        >
          <el-icon v-if="loading" size="16" class="loading-icon"><Refresh /></el-icon>
          <el-icon v-else size="16"><Check /></el-icon>
          <span>{{ mode === 'create' ? '创建' : '保存' }}</span>
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import { Document, Close, Check, Refresh, QuestionFilled } from '@element-plus/icons-vue';

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  /** @type {any} */
  tag: { type: Object, default: null },
  loading: { type: Boolean, default: false }
});
const emit = defineEmits(['update:visible', 'confirm']);

// 表单数据
const form = reactive({
  name: '',
  slug: ''
});

/** @type {import('vue').Ref<any>} */
const formRef = ref();

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入标签名称', trigger: 'blur' },
    { min: 1, max: 80, message: '长度在 1 到 80 个字符', trigger: 'blur' }
  ],
  slug: [
    { pattern: /^[a-z0-9-]*$/, message: 'Slug只能包含小写字母、数字和连字符', trigger: 'blur' }
  ]
};

// 打开时初始化表单
watch(() => props.visible, (val) => {
  if (val) {
    if (props.mode === 'edit' && props.tag) {
      form.name = props.tag.name;
      form.slug = props.tag.slug || '';
    } else {
      resetForm();
    }
  }
});

// 重置表单
const resetForm = () => {
  form.name = '';
  form.slug = '';
  if (formRef.value) {
    formRef.value.resetFields();
  }
};

// 根据名称生成Slug
const generateSlug = () => {
  if (!form.slug && form.name) {
    // 中文转拼音的简单映射（可以扩展）
    /** @type {Record<string, string>} */
    const chineseToPinyin = {
      '技术': 'jishu',
      '前端': 'qianduan',
      '后端': 'houduan',
      '开发': 'kaifa',
      '编程': 'biancheng',
      '设计': 'sheji',
      '产品': 'chanpin',
      '运营': 'yunying',
      '数据': 'shuju',
      '算法': 'suanfa',
      '框架': 'kuangjia',
      '工具': 'gongju',
      '教程': 'jiaocheng',
      '入门': 'rumen',
      '进阶': 'jinjie',
      '实战': 'shizhan',
      '基础': 'jichu',
      '高级': 'gaoji',
      '最新': 'zuixin',
      '热门': 'remen'
    };

    let slug = form.name.toLowerCase();

    // 替换常见中文词汇为拼音
    Object.keys(chineseToPinyin).forEach(chinese => {
      slug = slug.replace(new RegExp(chinese, 'g'), chineseToPinyin[chinese]);
    });

    // 处理剩余的中文字符：如果还有中文，则移除或用占位符替换
    slug = slug
      .replace(/[\u4e00-\u9fa5]/g, '') // 移除剩余中文字符
      .replace(/[^a-z0-9]/g, '-')      // 非字母数字替换为连字符
      .replace(/--+/g, '-')            // 多个连字符合并为一个
      .replace(/^-|-$/g, '');          // 去除首尾连字符

    // 如果生成的slug为空，使用时间戳
    if (!slug) {
      slug = 'tag-' + Date.now().toString().slice(-6);
    }

    form.slug = slug;
  }
};

// 校验并提交
const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
  } catch (error) {
    return;
  }

  emit('confirm', {
    name: form.name.trim(),
    slug: form.slug.trim() || undefined
  });
};
</script>

<style scoped>
/* ===== 现代化对话框样式 ===== */
.modern-dialog :deep(.el-dialog) {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 0;
  border: none;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 1.5rem;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 1.5rem 0;
  border-bottom: 1px solid rgba(139, 92, 246, 0.1);
  margin-bottom: 1.5rem;
}

.dialog-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
}

.dialog-icon {
  color: #8b5cf6;
}

.dialog-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog-close:hover {
  background: rgba(139, 92, 246, 0.2);
  transform: scale(1.1);
}

.modern-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(139, 92, 246, 0.1);
  margin-top: 1.5rem;
}

.dialog-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 8px;
  border: 1px solid;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, #8b5cf6, #a855f7);
  color: white;
  border-color: #8b5cf6;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

.dialog-btn.primary:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
  background: linear-gradient(135deg, #a855f7, #9333ea);
}

.dialog-btn.secondary {
  background: rgba(255, 255, 255, 0.8);
  color: #64748b;
  border-color: rgba(139, 92, 246, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.dialog-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  border-color: rgba(139, 92, 246, 0.3);
}

.dialog-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ===== Slug表单增强样式 ===== */
.slug-help-icon {
  color: #94a3b8;
  transition: all 0.3s ease;
  cursor: help;
}

.slug-help-icon:hover {
  color: #3b82f6;
  transform: scale(1.1);
}

.slug-preview {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  font-size: 0.875rem;
}

.preview-label {
  color: #64748b;
  font-weight: 500;
  margin-right: 8px;
}

.preview-url {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
}
</style>
