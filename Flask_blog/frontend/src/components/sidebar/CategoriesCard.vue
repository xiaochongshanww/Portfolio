<template>
  <div class="categories-card" style="background-color: rgb(248 250 252); border-radius: 24px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; margin-bottom: 16px;">
    <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
      <el-icon class="text-blue-500"><Compass /></el-icon>
      探索发现
    </h3>
    
    <!-- 分类区域 -->
    <div class="mb-6">
      <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
        <el-icon size="14" class="text-gray-500"><Collection /></el-icon>
        热门分类
      </h4>
      <div class="flex flex-wrap gap-2">
        <el-button 
          v-for="category in displayCategories" 
          :key="category.id" 
          size="small" 
          :type="selectedCategory === String(category.id) ? 'primary' : ''" 
          plain
          @click="$emit('category-click', category.id)"
          class="category-btn"
        >
          {{ category.name }}
        </el-button>
        
        <!-- 显示更多分类按钮 -->
        <el-button 
          v-if="categories.length > showCategoryLimit"
          size="small" 
          text
          @click="toggleShowAllCategories"
          class="show-more-btn"
        >
          {{ showAllCategories ? '收起' : `+${categories.length - showCategoryLimit}` }}
        </el-button>
      </div>
    </div>

    <!-- 标签云区域 -->
    <div>
      <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
        <el-icon size="14" class="text-gray-500"><PriceTag /></el-icon>
        标签云
      </h4>
      <div class="flex flex-wrap gap-2">
        <el-tag 
          v-for="tag in displayTags" 
          :key="tag.id" 
          size="small" 
          :type="selectedTag === tag.slug ? 'primary' : 'info'" 
          class="tag-item"
          @click="$emit('tag-click', tag.slug)"
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
import { Compass, Collection, PriceTag } from '@element-plus/icons-vue'

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
defineEmits(['category-click', 'tag-click'])

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
</script>

<style scoped>

.category-btn {
  font-size: 0.75rem;
  height: 28px;
  padding: 0 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.category-btn:hover {
  transform: translateY(-1px);
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