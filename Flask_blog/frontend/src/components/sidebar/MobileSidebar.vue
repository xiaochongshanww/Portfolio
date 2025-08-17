<template>
  <div class="mobile-sidebar h-full flex flex-col">
    <!-- 分类和标签快速访问 -->
    <div class="pt-4 border-t border-gray-200">
      <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
        探索发现
      </div>
      
      <!-- 热门分类 -->
      <div class="px-4 mb-4">
        <h4 class="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
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
            @click="handleCategoryClick(category.id)"
            class="mobile-category-btn"
          >
            {{ category.name }}
          </el-button>
          
          <!-- 展开/收起按钮 -->
          <el-button 
            v-if="categories.length > categoryLimit"
            size="small" 
            text
            @click="toggleShowAllCategories"
            class="text-gray-500"
          >
            {{ showAllCategories ? '收起' : `+${categories.length - categoryLimit}` }}
          </el-button>
        </div>
      </div>

      <!-- 标签云 -->
      <div class="px-4 mb-4">
        <h4 class="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <el-icon size="14" class="text-gray-500"><PriceTag /></el-icon>
          标签云
        </h4>
        <div class="flex flex-wrap gap-2">
          <el-tag 
            v-for="tag in displayTags" 
            :key="tag.id" 
            size="small" 
            :type="selectedTag === tag.slug ? 'primary' : 'info'"
            class="mobile-tag cursor-pointer"
            @click="handleTagClick(tag.slug)"
          >
            #{{ tag.slug }}
          </el-tag>
          
          <!-- 展开/收起按钮 -->
          <el-tag 
            v-if="tags.length > tagLimit"
            size="small" 
            type="info"
            class="mobile-tag cursor-pointer text-gray-500"
            @click="toggleShowAllTags"
          >
            {{ showAllTags ? '收起' : `+${tags.length - tagLimit}` }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 近期热门文章 -->
    <div class="pt-4 border-t border-gray-200">
      <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-2">
        <el-icon size="14" class="text-orange-500"><TrendCharts /></el-icon>
        近期热门
      </div>
      
      <div v-if="hotArticles.length" class="px-4 space-y-3">
        <article 
          v-for="(article, index) in hotArticles.slice(0, 3)" 
          :key="article.id" 
          class="mobile-hot-article group cursor-pointer"
          @click="handleArticleClick(article.slug)"
        >
          <div class="flex gap-3">
            <div class="flex-shrink-0 w-6 h-6 rounded bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center text-white font-bold text-xs">
              {{ index + 1 }}
            </div>
            <div class="flex-1 min-w-0">
              <h4 class="text-xs font-medium text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2 mb-1">
                {{ article.title }}
              </h4>
              <div class="flex items-center gap-2 text-xs text-gray-500">
                <span class="flex items-center gap-1">
                  <el-icon size="10"><View /></el-icon>
                  {{ formatNumber(article.views_count || 0) }}
                </span>
                <span class="flex items-center gap-1">
                  <el-icon size="10"><Star /></el-icon>
                  {{ formatNumber(article.likes_count || 0) }}
                </span>
              </div>
            </div>
          </div>
        </article>
      </div>
      
      <div v-else class="px-4 py-6 text-center text-gray-400">
        <el-icon size="32" class="mb-1"><DataLine /></el-icon>
        <p class="text-xs">暂无热门文章</p>
      </div>
    </div>

    <!-- 最新发布 -->
    <div class="pt-4 border-t border-gray-200 flex-1">
      <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-2">
        <el-icon size="14" class="text-green-500"><Clock /></el-icon>
        最新发布
      </div>
      
      <div v-if="latestArticles.length" class="px-4 space-y-2">
        <article 
          v-for="article in latestArticles.slice(0, 4)" 
          :key="article.id" 
          class="mobile-latest-article group cursor-pointer"
          @click="handleArticleClick(article.slug)"
        >
          <h4 class="text-xs font-medium text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2 mb-1">
            {{ article.title }}
          </h4>
          <div class="text-xs text-gray-500">
            {{ formatDate(article.published_at) }}
          </div>
        </article>
      </div>
      
      <div v-else class="px-4 py-6 text-center text-gray-400">
        <el-icon size="32" class="mb-1"><DocumentAdd /></el-icon>
        <p class="text-xs">暂无最新文章</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  Collection, PriceTag, TrendCharts, Clock, View, Star, 
  DataLine, DocumentAdd 
} from '@element-plus/icons-vue'

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
  hotArticles: {
    type: Array,
    default: () => []
  },
  latestArticles: {
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
const emit = defineEmits(['category-click', 'tag-click', 'article-click', 'close'])

// 展开状态
const showAllCategories = ref(false)
const showAllTags = ref(false)
const categoryLimit = 4
const tagLimit = 6

// 计算属性
const displayCategories = computed(() => {
  if (showAllCategories.value) {
    return props.categories
  }
  return props.categories.slice(0, categoryLimit)
})

const displayTags = computed(() => {
  if (showAllTags.value) {
    return props.tags
  }
  return props.tags.slice(0, tagLimit)
})

// 方法
function toggleShowAllCategories() {
  showAllCategories.value = !showAllCategories.value
}

function toggleShowAllTags() {
  showAllTags.value = !showAllTags.value
}

function handleCategoryClick(categoryId) {
  emit('category-click', categoryId)
  emit('close')
}

function handleTagClick(tagSlug) {
  emit('tag-click', tagSlug)
  emit('close')
}

function handleArticleClick(articleSlug) {
  emit('article-click', articleSlug)
  emit('close')
}

// 工具函数
function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return String(num)
}

function formatDate(dateString) {
  if (!dateString) return ''
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = now - date
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return '今天'
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays}天前`
    
    return date.toLocaleDateString('zh-CN', { 
      month: 'short', 
      day: 'numeric' 
    })
  } catch {
    return ''
  }
}
</script>

<style scoped>
.mobile-sidebar {
  background: white;
}

.mobile-category-btn {
  font-size: 0.75rem;
  height: 26px;
  padding: 0 6px;
}

.mobile-tag {
  font-size: 0.75rem;
  height: 22px;
  padding: 0 6px;
}

.mobile-hot-article {
  padding: 8px;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.mobile-hot-article:hover {
  background-color: rgb(249 250 251);
}

.mobile-latest-article {
  padding: 6px 8px;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.mobile-latest-article:hover {
  background-color: rgb(249 250 251);
}

/* line-clamp utility */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>