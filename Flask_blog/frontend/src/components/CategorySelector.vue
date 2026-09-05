<template>
  <div class="category-selector">
    <!-- 主要选择区域 -->
    <div class="selector-main">
      <el-select
        v-model="selectedCategoryId"
        placeholder="选择文章分类"
        clearable
        filterable
        :filter-method="handleFilter"
        size="large"
        class="category-select"
        @change="handleSelectionChange"
        @visible-change="handleDropdownVisibleChange"
      >
        <template #empty>
          <div class="empty-state">
            <el-icon class="empty-icon"><FolderOpened /></el-icon>
            <p>暂无匹配的分类</p>
            <el-button 
              v-if="userStore.hasRole(['editor', 'admin']) && searchKeyword"
              size="small" 
              type="primary" 
              @click="showQuickCreator = true"
            >
              创建 "{{ searchKeyword }}" 分类
            </el-button>
          </div>
        </template>
        
        <template #prefix>
          <el-icon class="select-icon"><Collection /></el-icon>
        </template>
        
        <!-- 分类选项 -->
        <el-option-group
          v-for="group in filteredCategoryGroups"
          :key="group.label"
          :label="group.label"
        >
          <el-option
            v-for="category in group.options"
            :key="category.id"
            :label="category.displayName"
            :value="category.id"
            :class="['category-option', `level-${category.level}`]"
          >
            <div class="option-content">
              <span class="option-label">{{ category.displayName }}</span>
              <span v-if="category.article_count" class="option-count">{{ category.article_count }}</span>
            </div>
          </el-option>
        </el-option-group>
      </el-select>

      <!-- 智能推荐按钮 -->
      <el-button
        v-if="!hideRecommendations && (articleData.title || articleData.content || articleData.tags?.length)"
        type="primary"
        :icon="MagicStick"
        size="large"
        :loading="recommendationLoading"
        class="ai-recommend-btn"
        title="AI智能推荐分类"
        @click="showRecommendations"
      >
        智能推荐
      </el-button>
    </div>

    <!-- 推荐分类面板 -->
    <Transition name="recommendations" appear>
      <div v-if="showRecommendationPanel" class="recommendations-panel">
        <div class="panel-header">
          <h4 class="panel-title">
            <el-icon><MagicStick /></el-icon>
            AI推荐分类
          </h4>
          <el-button 
            text 
            size="small" 
            class="close-btn"
            @click="showRecommendationPanel = false"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        
        <div v-if="recommendationLoading" class="loading-state">
          <el-skeleton :rows="3" animated />
        </div>
        
        <div v-else-if="recommendations.length > 0" class="recommendations-list">
          <div
            v-for="(rec, index) in recommendations"
            :key="rec.category.id"
            class="recommendation-item"
            :class="{ 'selected': selectedCategoryId === rec.category.id }"
            @click="selectRecommendation(rec)"
          >
            <div class="rec-content">
              <div class="rec-header">
                <span class="rec-name">{{ rec.category.name }}</span>
                <div class="rec-badges">
                  <el-tag
                    size="small"
                    :type="getConfidenceType(rec.confidence)"
                    class="confidence-tag"
                  >
                    {{ getConfidenceText(rec.confidence) }}
                  </el-tag>
                  <span class="rec-rank">#{{ index + 1 }}</span>
                </div>
              </div>
              <p v-if="rec.reason" class="rec-reason">{{ rec.reason }}</p>
            </div>
            <el-icon class="rec-arrow"><ArrowRight /></el-icon>
          </div>
        </div>
        
        <div v-else class="no-recommendations">
          <el-icon class="no-rec-icon"><DocumentRemove /></el-icon>
          <p>暂无匹配的分类推荐</p>
          <p class="no-rec-hint">请完善文章标题和内容后重试</p>
        </div>
      </div>
    </Transition>

    <!-- 选择状态信息 -->
    <div v-if="selectedCategoryId" class="selection-info">
      <div class="selected-category">
        <el-icon class="info-icon"><Check /></el-icon>
        <span class="info-text">
          已选择：<strong>{{ getSelectedCategoryPath() }}</strong>
        </span>
      </div>
      
      <!-- 相关分类建议 -->
      <div v-if="relatedCategories.length > 0" class="related-categories">
        <span class="related-label">相关分类：</span>
        <el-button
          v-for="related in relatedCategories.slice(0, 3)"
          :key="related.id"
          size="small"
          text
          class="related-btn"
          @click="selectedCategoryId = related.id"
        >
          {{ related.name }}
        </el-button>
      </div>
      
      <!-- 验证警告 -->
      <el-alert
        v-if="validationResult && validationResult.warning"
        :title="validationResult.warning"
        type="warning"
        size="small"
        :closable="false"
        show-icon
        class="validation-alert"
      />
    </div>

    <!-- 快速创建分类弹窗 -->
    <QuickCategoryCreator
      v-model:visible="showQuickCreator"
      :initial-name="searchKeyword"
      :parent-categories="parentCategories"
      @category-created="handleCategoryCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import { 
  Collection, FolderOpened, MagicStick, Close, ArrowRight, 
  Check, DocumentRemove 
} from '@element-plus/icons-vue';
import message from '../utils/message';
import { useUserStore } from '../stores/user';
import QuickCategoryCreator from './QuickCategoryCreator.vue';
import { 
  recommendCategories, 
  getRelatedCategories, 
  validateCategorySelection 
} from '../utils/categoryRecommender';

// Props
const props = defineProps({
  modelValue: {
    type: [Number, null],
    default: null
  },
  categories: {
    type: Array,
    default: () => [],
    validator: (value) => {
      if (!Array.isArray(value)) {
        console.error('❌ CategorySelector: categories prop必须是数组格式，收到:', typeof value, value);
        return false;
      }
      return true;
    }
  },
  articleData: {
    type: Object,
    default: () => ({})
  },
  hideRecommendations: {
    type: Boolean,
    default: false
  },
  autoRecommend: {
    type: Boolean,
    default: true
  },
  size: {
    type: String,
    default: 'large'
  }
});

// Emits
const emit = defineEmits(['update:modelValue', 'change', 'recommendation-selected', 'refresh-categories']);

// Stores
const userStore = useUserStore();

// State
/** @type {import('vue').Ref<number | null>} */
const selectedCategoryId = ref(props.modelValue);
const searchKeyword = ref('');
const showRecommendationPanel = ref(false);
const showQuickCreator = ref(false);
const recommendationLoading = ref(false);
/** @type {import('vue').Ref<Array<{ category: import('@/types').Category, score: number, confidence?: number, reason?: string }>>} */
const recommendations = ref([]);
/** @type {import('vue').Ref<{ valid: boolean, warning?: string | null, error?: string } | null>} */
const validationResult = ref(null);

// 构建分类树结构
const categoryTree = computed(() => {
  /** @type {Array<import('@/types').Category & { children: any[], level: number, displayName: string }>} */
  const tree = [];
  /** @type {Map<number, import('@/types').Category & { children: any[], level: number, displayName: string }>} */
  const categoryMap = new Map();
  
  // 确保 categories 是数组格式
  const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
  
  if (categoriesArray.length === 0) {
    console.warn('⚠️ CategorySelector: categories 为空数组');
    return tree;
  }
  
  // 创建映射表
  categoriesArray.forEach(category => {
    categoryMap.set(category.id, {
      ...category,
      children: [],
      level: 0,
      displayName: category.name || ''
    });
  });
  
  // 构建树结构
  categoriesArray.forEach(category => {
    const item = categoryMap.get(category.id);
    if (item && category.parent_id && categoryMap.has(category.parent_id)) {
      const parent = categoryMap.get(category.parent_id);
      if (parent) {
        parent.children.push(item);
        item.level = parent.level + 1;
        item.displayName = `${'  '.repeat(item.level)}${category.name || ''}`;
      }
    } else if (item) {
      tree.push(item);
    }
  });
  
  return tree;
});

// 扁平化分类列表（用于搜索）
const flatCategories = computed(() => {
  /** @param {Array<import('@/types').Category & { children?: any[], level?: number, displayName?: string }>} categories @param {number} level */
  const flatten = (categories, level = 0) => {
    /** @type {Array<import('@/types').Category & { level: number, displayName: string }>} */
    const result = [];
    categories.forEach(category => {
      result.push({
        ...category,
        level,
        displayName: `${'  '.repeat(level)}${category.name}`
      });
      if (category.children && category.children.length > 0) {
        result.push(...flatten(category.children, level + 1));
      }
    });
    return result;
  };
  
  return flatten(categoryTree.value);
});

// 分组后的分类列表
const filteredCategoryGroups = computed(() => {
  const filtered = flatCategories.value.filter(category => {
    if (!searchKeyword.value) return true;
    return (category.name || '').toLowerCase().includes(searchKeyword.value.toLowerCase());
  });
  
  if (filtered.length === 0) return [];
  
  // 按级别分组
  /** @type {Record<string, Array<import('@/types').Category & { level: number, displayName: string }>>} */
  const groups = {};
  filtered.forEach(category => {
    const level = category.level;
    let groupName;
    
    if (level === 0) {
      groupName = '主要分类';
    } else if (level === 1) {
      groupName = '子分类';
    } else {
      groupName = '详细分类';
    }
    
    if (!groups[groupName]) {
      groups[groupName] = [];
    }
    groups[groupName].push(category);
  });
  
  return Object.entries(groups).map(([label, options]) => ({
    label,
    options
  }));
});

// 父级分类列表（用于快速创建）
const parentCategories = computed(() => {
  const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
  return categoriesArray.filter(cat => !cat.parent_id);
});

// 相关分类
const relatedCategories = computed(() => {
  if (!selectedCategoryId.value) return [];
  const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
  return getRelatedCategories(selectedCategoryId.value, categoriesArray);
});

// 搜索过滤
/** @param {string} value */
const handleFilter = (value) => {
  searchKeyword.value = value;
};

// 选择变更处理
/** @param {number | null} value */
const handleSelectionChange = (value) => {
  selectedCategoryId.value = value;
  emit('update:modelValue', value);
  emit('change', value);
  
  // 验证选择
  if (value) {
    const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
    validationResult.value = validateCategorySelection(
      value, 
      props.articleData, 
      categoriesArray
    );
  } else {
    validationResult.value = null;
  }
  
  // 隐藏推荐面板
  showRecommendationPanel.value = false;
};

// 下拉框显示/隐藏处理
/** @param {boolean} visible */
const handleDropdownVisibleChange = (visible) => {
  if (!visible) {
    searchKeyword.value = '';
  }
};

// 显示智能推荐
const showRecommendations = async () => {
  if (showRecommendationPanel.value) {
    showRecommendationPanel.value = false;
    return;
  }
  
  console.log('🤖 开始AI分类推荐...');
  console.log('📊 可用分类数量:', props.categories.length);
  console.log('📝 文章数据:', props.articleData);
  
  recommendationLoading.value = true;
  showRecommendationPanel.value = true;
  
  try {
    await nextTick();
    
    // 检查输入数据
    console.log('🔍 检查分类数据:', { 
      categories: props.categories, 
      categoriesLength: props.categories?.length,
      categoriesType: typeof props.categories,
      isArray: Array.isArray(props.categories)
    });
    
    // 确保 categories 是数组格式
    const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
    
    if (categoriesArray.length === 0) {
      console.warn('⚠️ 没有可用的分类数据或数据格式不正确');
      if (!props.categories) {
        message.warning('分类数据未加载，请稍后重试');
      } else if (!Array.isArray(props.categories)) {
        message.warning('分类数据格式错误，请刷新页面重试');
        console.error('❌ 分类数据不是数组格式:', props.categories);
      } else {
        message.warning('没有可用的分类，请先在管理后台创建分类');
      }
      recommendations.value = [];
      return;
    }
    
    const articleData = /** @type {{ title?: string, content?: string, summary?: string }} */ (props.articleData);
    if (!articleData || (!articleData.title && !articleData.content && !articleData.summary)) {
      console.warn('⚠️ 文章数据不足，无法进行智能推荐');
      message.info('请先填写文章标题或内容，以便AI进行智能推荐');
      recommendations.value = [];
      return;
    }
    
    // 模拟AI分析延迟
    await new Promise(resolve => setTimeout(resolve, 800));
    
    console.log('🔍 调用推荐算法...');
    recommendations.value = recommendCategories(
      props.articleData,
      categoriesArray,
      { maxRecommendations: 5, includeReason: true }
    );
    
    console.log('✨ 推荐结果:', recommendations.value);
    
    if (recommendations.value.length === 0) {
      console.log('💡 未找到匹配的分类推荐');
      message.info('未找到匹配的分类，请手动选择或创建新分类');
    } else {
      console.log(`🎯 成功推荐 ${recommendations.value.length} 个分类`);
      message.success(`AI推荐了 ${recommendations.value.length} 个相关分类`);
    }
  } catch (error) {
    console.error('❌ 获取分类推荐失败:', error);
    message.warning('分类推荐功能暂时不可用');
  } finally {
    recommendationLoading.value = false;
  }
};

// 选择推荐分类
/** @param {{ category: import('@/types').Category, score: number, confidence?: number, reason?: string }} recommendation */
const selectRecommendation = (recommendation) => {
  selectedCategoryId.value = recommendation.category.id;
  handleSelectionChange(recommendation.category.id);
  emit('recommendation-selected', recommendation);
  
  message.success(`已选择推荐分类：${recommendation.category.name}`);
};

// 获取置信度类型
/**
 * @param {number | undefined} confidence
 * @returns {'success' | 'primary' | 'warning' | 'info'}
 */
const getConfidenceType = (confidence) => {
  const c = confidence ?? 0;
  if (c >= 0.8) return 'success';
  if (c >= 0.6) return 'primary';
  if (c >= 0.4) return 'warning';
  return 'info';
};

// 获取置信度文本
/** @param {number | undefined} confidence */
const getConfidenceText = (confidence) => {
  const c = confidence ?? 0;
  if (c >= 0.8) return '高匹配';
  if (c >= 0.6) return '较匹配';
  if (c >= 0.4) return '一般匹配';
  return '低匹配';
};

// 获取选中分类的完整路径
const getSelectedCategoryPath = () => {
  if (!selectedCategoryId.value) return '';
  
  const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
  const category = categoriesArray.find(cat => cat.id === selectedCategoryId.value);
  if (!category) return '';
  
  const path = [category.name || ''];
  let current = category;
  
  while (current.parent_id) {
    const parent = categoriesArray.find(cat => cat.id === current.parent_id);
    if (parent) {
      path.unshift(parent.name || '');
      current = parent;
    } else {
      break;
    }
  }
  
  return path.join(' > ');
};

// 处理分类创建成功
/** @param {import('@/types').Category} newCategory */
const handleCategoryCreated = (newCategory) => {
  showQuickCreator.value = false;
  message.success('分类创建成功');
  
  // 自动选择新创建的分类
  selectedCategoryId.value = newCategory.id;
  handleSelectionChange(newCategory.id);
  
  // 刷新分类列表
  emit('refresh-categories');
};

// 自动推荐监听
watch([() => props.articleData.title, () => props.articleData.content], 
  () => {
    if (props.autoRecommend && !selectedCategoryId.value) {
      // 延迟执行，避免频繁触发
      clearTimeout(window.categoryAutoRecommendTimer);
      window.categoryAutoRecommendTimer = setTimeout(() => {
        if (!selectedCategoryId.value) {
          showRecommendations();
        }
      }, 2000);
    }
  },
  { deep: true }
);

// 监听外部值变化
watch(() => props.modelValue, (newValue) => {
  selectedCategoryId.value = newValue;
});

// 监听选中值变化，更新验证结果
watch(selectedCategoryId, (newValue) => {
  if (newValue) {
    const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
    validationResult.value = validateCategorySelection(
      newValue, 
      props.articleData, 
      categoriesArray
    );
  } else {
    validationResult.value = null;
  }
});

onMounted(() => {
  // 如果有初始值，进行验证
  if (selectedCategoryId.value) {
    const categoriesArray = /** @type {Array<import('@/types').Category>} */ (Array.isArray(props.categories) ? props.categories : []);
    validationResult.value = validateCategorySelection(
      selectedCategoryId.value, 
      props.articleData, 
      categoriesArray
    );
  }
});
</script>

<style scoped>
.category-selector {
  /* EP 主色对齐公开站 #2563eb(按钮/选中态) */
  --el-color-primary: #2563eb;
  --el-color-primary-light-3: #5a8bef;
  --el-color-primary-light-5: #8fadf4;
  --el-color-primary-light-7: #c3d5f8;
  --el-color-primary-light-8: #dbe5fa;
  --el-color-primary-light-9: #eef3fd;
  --el-color-primary-dark-2: #1d4ed8;
  width: 100%;
}

.selector-main {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.category-select {
  flex: 1;
}

.select-icon {
  color: var(--muted, #6b7280);
}

.ai-recommend-btn {
  flex-shrink: 0;
  background: #2563eb;
  border: 1px solid #2563eb;
  transition: background-color 180ms ease, border-color 180ms ease;
}

.ai-recommend-btn:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

/* 选项样式 */
.category-option {
  padding: 0 !important;
}

.option-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 16px;
}

.option-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-count {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 10px;
  margin-left: 8px;
}

.level-1 .option-label {
  padding-left: 16px;
}

.level-2 .option-label {
  padding-left: 32px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 20px;
  color: #909399;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
  color: #c0c4cc;
}

/* 推荐面板 */
.recommendations-panel {
  margin-top: 16px;
  background: var(--surface, #fff);
  border: 1px solid var(--line, #e3e3df);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--surface-2, #f1f1ee);
  border-bottom: 1px solid var(--line, #e3e3df);
  color: var(--text, #171717);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  color: white;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.loading-state {
  padding: 20px;
}

.recommendations-list {
  padding: 16px;
}

.recommendation-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: white;
  border: 2px solid #f0f2f5;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.recommendation-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
  transform: translateY(-1px);
}

.recommendation-item.selected {
  border-color: #67c23a;
  background: #f0f9ff;
}

.rec-content {
  flex: 1;
}

.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.rec-name {
  font-weight: 600;
  color: #303133;
}

.rec-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-tag {
  font-size: 11px;
}

.rec-rank {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 10px;
}

.rec-reason {
  margin: 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.4;
}

.rec-arrow {
  color: #c0c4cc;
  margin-left: 12px;
  transition: color 0.3s ease;
}

.recommendation-item:hover .rec-arrow {
  color: #409eff;
}

.no-recommendations {
  text-align: center;
  padding: 32px 20px;
  color: #909399;
}

.no-rec-icon {
  font-size: 48px;
  margin-bottom: 12px;
  color: #c0c4cc;
}

.no-rec-hint {
  font-size: 12px;
  margin: 4px 0 0;
}

/* 选择信息 */
.selection-info {
  margin-top: 16px;
}

.selected-category {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--blue-soft, #edf3ff);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  margin-bottom: 12px;
}

.info-icon {
  color: #67c23a;
  font-size: 16px;
}

.info-text {
  font-size: 14px;
  color: #606266;
}

.related-categories {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.related-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.related-btn {
  font-size: 12px;
  padding: 4px 8px;
  height: auto;
  border-radius: 12px;
}

.validation-alert {
  margin-top: 8px;
}

/* 动画 */
.recommendations-enter-active,
.recommendations-leave-active {
  transition: all 0.3s ease;
}

.recommendations-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.recommendations-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 响应式 */
@media (max-width: 768px) {
  .selector-main {
    flex-direction: column;
  }
  
  .ai-recommend-btn {
    width: 100%;
  }
  
  .rec-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .related-categories {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>