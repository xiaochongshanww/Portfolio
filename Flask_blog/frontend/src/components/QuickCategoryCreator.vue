<template>
  <el-dialog
    v-model="dialogVisible"
    title="快速创建分类"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    class="quick-creator-dialog"
    @close="handleClose"
  >
    <div class="creator-content">
      <!-- 创建表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        class="creation-form"
      >
        <el-form-item label="分类名称" prop="name" class="form-item-required">
          <el-input
            v-model="form.name"
            placeholder="请输入分类名称"
            size="large"
            clearable
            maxlength="50"
            show-word-limit
            @input="generateSlug"
            :disabled="creating"
          >
            <template #prefix>
              <el-icon><Collection /></el-icon>
            </template>
          </el-input>
          <div class="input-hint">
            分类名称将显示在前台，建议简洁明了
          </div>
        </el-form-item>

        <el-form-item label="URL别名" prop="slug">
          <el-input
            v-model="form.slug"
            placeholder="自动生成或手动输入"
            size="large"
            clearable
            :disabled="creating"
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
          <div class="input-hint">
            URL别名用于生成友好的链接地址，如：frontend-development
          </div>
        </el-form-item>

        <el-form-item label="父分类" prop="parent_id">
          <el-select
            v-model="form.parent_id"
            placeholder="选择父分类（可选）"
            clearable
            filterable
            size="large"
            class="parent-select"
            :disabled="creating"
          >
            <el-option
              value=""
              label="— 设为顶级分类 —"
              class="top-level-option"
            />
            <el-option
              v-for="parent in parentCategories"
              :key="parent.id"
              :label="parent.name"
              :value="parent.id"
            >
              <div class="parent-option">
                <span class="parent-name">{{ parent.name }}</span>
                <span v-if="parent.articleCount" class="parent-count">
                  {{ parent.articleCount }} 篇文章
                </span>
              </div>
            </el-option>
          </el-select>
          <div class="input-hint">
            选择父分类可以创建分类层级结构
          </div>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述这个分类的用途和内容范围（可选）"
            maxlength="200"
            show-word-limit
            resize="vertical"
            :disabled="creating"
          />
          <div class="input-hint">
            描述信息有助于作者选择合适的分类
          </div>
        </el-form-item>
      </el-form>

      <!-- 预览区域 -->
      <div v-if="form.name" class="preview-section">
        <h4 class="preview-title">
          <el-icon><View /></el-icon>
          预览效果
        </h4>
        <div class="preview-card">
          <div class="preview-header">
            <div class="preview-icon">
              <el-icon><Collection /></el-icon>
            </div>
            <div class="preview-info">
              <h5 class="preview-name">{{ form.name }}</h5>
              <p class="preview-path">
                {{ getPreviewPath() }}
              </p>
            </div>
          </div>
          <p v-if="form.description" class="preview-desc">
            {{ form.description }}
          </p>
          <div class="preview-meta">
            <span class="preview-url">
              <el-icon><Link /></el-icon>
              /category/{{ form.slug || 'auto-generated' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 智能建议 -->
      <div v-if="suggestions.length > 0" class="suggestions-section">
        <h4 class="suggestions-title">
          <el-icon><MagicStick /></el-icon>
          智能建议
        </h4>
        <div class="suggestions-list">
          <div
            v-for="suggestion in suggestions"
            :key="suggestion.type"
            class="suggestion-item"
            @click="applySuggestion(suggestion)"
          >
            <div class="suggestion-content">
              <strong>{{ suggestion.title }}</strong>
              <p>{{ suggestion.description }}</p>
            </div>
            <el-button size="small" type="primary" text>
              应用
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" :disabled="creating">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="creating"
          @click="handleCreate"
          :disabled="!form.name.trim()"
        >
          <el-icon v-if="!creating"><Check /></el-icon>
          {{ creating ? '创建中...' : '创建分类' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { 
  Collection, Link, View, MagicStick, Check 
} from '@element-plus/icons-vue';
import message from '../utils/message';
import apiClient from '../apiClient';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  initialName: {
    type: String,
    default: ''
  },
  parentCategories: {
    type: Array,
    default: () => []
  },
  suggestedParent: {
    type: Number,
    default: null
  }
});

// Emits
const emit = defineEmits(['update:visible', 'category-created', 'category-creation-failed']);

// Refs
const formRef = ref(null);

// State
const dialogVisible = ref(props.visible);
const creating = ref(false);
const form = ref({
  name: '',
  slug: '',
  parent_id: null,
  description: ''
});

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { min: 2, max: 50, message: '分类名称长度应在2-50个字符之间', trigger: 'blur' },
    { 
      validator: async (rule, value, callback) => {
        if (!value) return callback();
        
        // 检查分类名称是否已存在
        try {
          const response = await apiClient.get('/taxonomy/categories/');
          const existingCategories = response.data.data || [];
          const isDuplicate = existingCategories.some(cat => 
            cat.name.toLowerCase() === value.toLowerCase()
          );
          
          if (isDuplicate) {
            return callback(new Error('分类名称已存在'));
          }
          callback();
        } catch (error) {
          console.warn('检查分类名称失败:', error);
          callback(); // 忽略检查错误，允许继续
        }
      }, 
      trigger: 'blur' 
    }
  ],
  slug: [
    { 
      pattern: /^[a-zA-Z0-9-_]+$/, 
      message: 'URL别名只能包含字母、数字、连字符和下划线', 
      trigger: 'blur' 
    },
    { 
      min: 2, 
      max: 50, 
      message: 'URL别名长度应在2-50个字符之间', 
      trigger: 'blur' 
    }
  ],
  description: [
    { max: 200, message: '描述不能超过200个字符', trigger: 'blur' }
  ]
};

// 智能建议
const suggestions = computed(() => {
  const suggestions = [];
  
  // 基于名称的URL别名建议
  if (form.value.name && !form.value.slug) {
    suggestions.push({
      type: 'slug',
      title: '自动生成URL别名',
      description: `建议使用：${generateSlugFromName(form.value.name)}`,
      action: () => {
        form.value.slug = generateSlugFromName(form.value.name);
      }
    });
  }
  
  // 基于名称的父分类建议
  if (form.value.name && !form.value.parent_id) {
    const suggestedParent = findSuggestedParent(form.value.name);
    if (suggestedParent) {
      suggestions.push({
        type: 'parent',
        title: '推荐父分类',
        description: `建议归类到：${suggestedParent.name}`,
        action: () => {
          form.value.parent_id = suggestedParent.id;
        }
      });
    }
  }
  
  // 基于名称的描述建议
  if (form.value.name && !form.value.description) {
    const suggestedDesc = generateDescriptionSuggestion(form.value.name);
    if (suggestedDesc) {
      suggestions.push({
        type: 'description',
        title: '自动生成描述',
        description: `建议描述：${suggestedDesc}`,
        action: () => {
          form.value.description = suggestedDesc;
        }
      });
    }
  }
  
  return suggestions;
});

// 生成URL别名
const generateSlugFromName = (name) => {
  return name
    .toLowerCase()
    .replace(/[^\w\s\u4e00-\u9fa5]/g, '') // 移除特殊字符
    .replace(/\s+/g, '-') // 空格替换为连字符
    .replace(/[\u4e00-\u9fa5]/g, match => { // 中文转拼音（简化版）
      const pinyinMap = {
        '前端': 'frontend',
        '后端': 'backend', 
        '全栈': 'fullstack',
        '移动': 'mobile',
        '开发': 'development',
        '设计': 'design',
        '产品': 'product',
        '运营': 'operation',
        '数据': 'data',
        '算法': 'algorithm',
        '人工智能': 'ai',
        '机器学习': 'ml',
        '深度学习': 'dl'
      };
      return pinyinMap[match] || match;
    })
    .substring(0, 30); // 限制长度
};

// 自动生成slug
const generateSlug = () => {
  if (form.value.name && !form.value.slug) {
    form.value.slug = generateSlugFromName(form.value.name);
  }
};

// 查找建议的父分类
const findSuggestedParent = (name) => {
  const keywords = {
    'Vue': ['前端开发', 'Frontend'],
    'React': ['前端开发', 'Frontend'], 
    'Angular': ['前端开发', 'Frontend'],
    'Python': ['后端开发', 'Backend'],
    'Java': ['后端开发', 'Backend'],
    'Node': ['后端开发', 'Backend'],
    'AI': ['人工智能', 'Artificial Intelligence'],
    '机器学习': ['人工智能', 'Artificial Intelligence'],
    '深度学习': ['人工智能', 'Artificial Intelligence'],
    '移动': ['移动开发', 'Mobile'],
    'Android': ['移动开发', 'Mobile'],
    'iOS': ['移动开发', 'Mobile'],
    '设计': ['设计', 'Design'],
    'UI': ['设计', 'Design'],
    'UX': ['设计', 'Design']
  };
  
  for (const [keyword, parentNames] of Object.entries(keywords)) {
    if (name.includes(keyword)) {
      for (const parentName of parentNames) {
        const parent = props.parentCategories.find(cat => 
          cat.name.includes(parentName)
        );
        if (parent) return parent;
      }
    }
  }
  
  return null;
};

// 生成描述建议
const generateDescriptionSuggestion = (name) => {
  const templates = {
    '前端': '包含前端开发相关的技术文章，如框架使用、界面设计、用户体验等',
    '后端': '涵盖后端开发技术，包括服务器开发、数据库设计、API构建等',
    '全栈': '全栈开发相关内容，涵盖前后端技术栈和项目实践',
    '移动': '移动应用开发相关技术，包括原生开发、跨平台方案等',
    '人工智能': '人工智能领域的技术分享，包括机器学习、深度学习等',
    '设计': '设计相关内容，包括UI/UX设计、视觉设计、交互设计等',
    '产品': '产品管理和设计相关内容，包括需求分析、产品规划等',
    '运营': '产品运营、内容运营、用户增长等运营相关内容',
    '创业': '创业经验分享、商业模式探讨、创新思维等',
    '生活': '生活方式、个人成长、工作生活平衡等内容'
  };
  
  for (const [keyword, template] of Object.entries(templates)) {
    if (name.includes(keyword)) {
      return template;
    }
  }
  
  return null;
};

// 获取预览路径
const getPreviewPath = () => {
  if (!form.value.parent_id) {
    return '顶级分类';
  }
  
  const parent = props.parentCategories.find(cat => cat.id === form.value.parent_id);
  return parent ? `${parent.name} > ${form.value.name}` : form.value.name;
};

// 应用建议
const applySuggestion = (suggestion) => {
  suggestion.action();
  message.success(`已应用建议：${suggestion.title}`);
};

// 创建分类
const handleCreate = async () => {
  if (!formRef.value) return;
  
  try {
    // 验证表单
    await formRef.value.validate();
    
    creating.value = true;
    
    const categoryData = {
      name: form.value.name.trim(),
      slug: form.value.slug || generateSlugFromName(form.value.name),
      parent_id: form.value.parent_id || null,
      description: form.value.description?.trim() || null
    };
    
    const response = await apiClient.post('/taxonomy/categories/', categoryData);
    
    if (response.data && response.data.code === 0) {
      const newCategory = response.data.data;
      message.success('分类创建成功');
      emit('category-created', newCategory);
      handleClose();
    } else {
      throw new Error(response.data?.message || '创建失败');
    }
    
  } catch (error) {
    console.error('创建分类失败:', error);
    
    let errorMessage = '创建分类失败';
    
    if (error.response?.data?.message) {
      errorMessage = error.response.data.message;
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    message.critical(errorMessage);
    emit('category-creation-failed', error);
  } finally {
    creating.value = false;
  }
};

// 关闭对话框
const handleClose = () => {
  dialogVisible.value = false;
  emit('update:visible', false);
  
  // 重置表单
  nextTick(() => {
    if (formRef.value) {
      formRef.value.resetFields();
    }
    form.value = {
      name: '',
      slug: '',
      parent_id: null,
      description: ''
    };
  });
};

// 监听visible变化
watch(() => props.visible, (newValue) => {
  dialogVisible.value = newValue;
  
  if (newValue) {
    // 初始化表单数据
    form.value.name = props.initialName || '';
    form.value.parent_id = props.suggestedParent || null;
    
    // 如果有初始名称，自动生成slug
    if (props.initialName) {
      nextTick(() => {
        generateSlug();
      });
    }
  }
});

// 监听对话框显示状态
watch(dialogVisible, (newValue) => {
  emit('update:visible', newValue);
});
</script>

<style scoped>
.quick-creator-dialog {
  --el-dialog-border-radius: 16px;
}

.creator-content {
  max-height: 70vh;
  overflow-y: auto;
}

.creation-form {
  margin-bottom: 24px;
}

.form-item-required :deep(.el-form-item__label::before) {
  content: '*';
  color: #f56c6c;
  margin-right: 4px;
}

.input-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

.parent-select {
  width: 100%;
}

.top-level-option {
  font-style: italic;
  color: #909399;
}

.parent-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.parent-name {
  font-weight: 500;
}

.parent-count {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 10px;
}

/* 预览区域 */
.preview-section {
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.preview-card {
  background: white;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.preview-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #409eff 0%, #1890ff 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
}

.preview-info {
  flex: 1;
}

.preview-name {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.preview-path {
  margin: 0;
  font-size: 12px;
  color: #909399;
}

.preview-desc {
  margin: 0 0 12px;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

.preview-meta {
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
}

.preview-url {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #909399;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

/* 智能建议 */
.suggestions-section {
  background: linear-gradient(135deg, #fff7e6 0%, #ffffff 100%);
  border: 1px solid #ffd591;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.suggestions-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #d46b08;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: white;
  border: 1px solid #ffd591;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.suggestion-item:hover {
  border-color: #faad14;
  box-shadow: 0 2px 8px rgba(250, 173, 20, 0.2);
  transform: translateY(-1px);
}

.suggestion-content {
  flex: 1;
}

.suggestion-content strong {
  display: block;
  color: #d46b08;
  margin-bottom: 4px;
}

.suggestion-content p {
  margin: 0;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.4;
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .quick-creator-dialog {
    --el-dialog-width: 90vw;
  }
  
  .preview-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .suggestion-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}

/* 滚动条样式 */
.creator-content::-webkit-scrollbar {
  width: 6px;
}

.creator-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.creator-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.creator-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>