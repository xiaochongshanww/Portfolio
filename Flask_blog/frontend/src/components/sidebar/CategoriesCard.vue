<template>
  <div class="categories-card" style="background-color: rgb(248 250 252); border-radius: 24px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; margin-bottom: 16px;">
    <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
      <el-icon class="text-blue-500"><Compass /></el-icon>
      探索发现
    </h3>
    
    <!-- 分类区域 -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-medium text-gray-700 flex items-center gap-2">
          <el-icon size="14" class="text-gray-500"><Collection /></el-icon>
          热门分类
        </h4>
        <router-link 
          to="/categories" 
          class="text-xs text-blue-600 hover:text-blue-700 hover:underline transition-colors"
        >
          查看全部
        </router-link>
      </div>
      <div class="flex flex-wrap gap-2 category-buttons-container">
        <button
          v-for="category in displayCategories" 
          :key="category.id" 
          @click="handleCategoryClick(category.id)"
          :class="[
            'sidebar-category-btn',
            selectedCategory === String(category.id) ? 'sidebar-category-btn-active' : 'sidebar-category-btn-default'
          ]"
        >
          <span class="category-text">{{ category.name }}</span>
          <el-icon v-if="selectedCategory === String(category.id)" size="12" class="close-icon">
            <Close />
          </el-icon>
        </button>
        
        <!-- 显示更多分类按钮 -->
        <button 
          v-if="categories.length > showCategoryLimit"
          @click="toggleShowAllCategories"
          class="sidebar-show-more-btn"
        >
          {{ showAllCategories ? '收起' : `+${categories.length - showCategoryLimit}` }}
        </button>
      </div>
    </div>

    <!-- 标签云区域 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-medium text-gray-700 flex items-center gap-2">
          <el-icon size="14" class="text-gray-500"><PriceTag /></el-icon>
          标签云
        </h4>
        <router-link 
          to="/tags" 
          class="text-xs text-purple-600 hover:text-purple-700 hover:underline transition-colors"
        >
          查看全部
        </router-link>
      </div>
      <div class="flex flex-wrap gap-2">
        <el-tag 
          v-for="tag in displayTags" 
          :key="tag.id" 
          size="small" 
          :type="selectedTag === tag.slug ? 'primary' : 'info'" 
          class="tag-item"
          @click="handleTagClick(tag.slug)"
        >
          #{{ tag.slug }}
        </el-tag>
        
        <!-- 显示更多标签按钮 -->
        <el-tag 
          v-if="tags.length > showTagLimit"
          size="small" 
          type="info"
          class="tag-item show-more-tag"
          @click="toggleShowAllTags"
        >
          {{ showAllTags ? '收起' : `+${tags.length - showTagLimit}` }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Compass, Collection, PriceTag, Close } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  categories: {
    type: Array,
    default: () => []
  },
  tags: {
    type: Array,
    default: () => []
  },
  selectedCategory: {
    type: String,
    default: ''
  },
  selectedTag: {
    type: String,
    default: ''
  }
})

// Events
const emit = defineEmits(['category-click', 'tag-click'])

// 显示控制
const showAllCategories = ref(false)
const showAllTags = ref(false)
const showCategoryLimit = 6
const showTagLimit = 12

// 计算属性
const displayCategories = computed(() => {
  if (showAllCategories.value) {
    return props.categories
  }
  return props.categories.slice(0, showCategoryLimit)
})

const displayTags = computed(() => {
  if (showAllTags.value) {
    return props.tags
  }
  return props.tags.slice(0, showTagLimit)
})

// 方法
function toggleShowAllCategories() {
  showAllCategories.value = !showAllCategories.value
}

function toggleShowAllTags() {
  showAllTags.value = !showAllTags.value
}

function handleCategoryClick(categoryId) {
  // 如果点击的是当前已选中的分类，则取消选择
  if (props.selectedCategory === String(categoryId)) {
    emit('category-click', ''); // 传递空字符串表示取消选择
  } else {
    emit('category-click', categoryId);
  }
}

function handleTagClick(tagSlug) {
  // 如果点击的是当前已选中的标签，则取消选择
  if (props.selectedTag === tagSlug) {
    emit('tag-click', ''); // 传递空字符串表示取消选择
  } else {
    emit('tag-click', tagSlug);
  }
}
</script>

<style scoped>
/* ===== 现代化侧边栏分类按钮样式 ===== */
.category-buttons-container {
  gap: 8px;
  row-gap: 10px;
}

.sidebar-category-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
}

.sidebar-category-btn-default {
  background: rgba(248, 250, 252, 0.8);
  color: #64748b;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.sidebar-category-btn-default:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
}

.sidebar-category-btn-active {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: 1px solid transparent;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.25);
}

.sidebar-category-btn-active:hover {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(239, 68, 68, 0.3);
}

.close-icon {
  opacity: 0.9;
  margin-left: 2px;
}

.sidebar-show-more-btn {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px dashed rgba(148, 163, 184, 0.6);
  background: transparent;
  color: #64748b;
  transition: all 0.25s ease;
}

.sidebar-show-more-btn:hover {
  border-color: rgba(59, 130, 246, 0.4);
  border-style: solid;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
}

.tag-item {
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag-item:hover {
  transform: scale(1.05);
}

.show-more-btn {
  font-size: 0.75rem;
  height: 28px;
  padding: 0 8px;
  color: rgb(107 114 128);
  border: 1px dashed rgb(209 213 219);
}

.show-more-tag {
  border: 1px dashed rgb(209 213 219);
  background: transparent;
  color: rgb(107 114 128);
}

.show-more-tag:hover {
  border-color: rgb(59 130 246);
  color: rgb(59 130 246);
}
</style>