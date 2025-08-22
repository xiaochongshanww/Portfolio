<template>
  <div class="hot-articles-card" style="background-color: rgb(248 250 252); border-radius: 24px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; margin-bottom: 16px;">
    <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
      <el-icon class="text-orange-500"><TrendCharts /></el-icon>
      近期热门
    </h3>
    
    <!-- 加载状态 -->
    <el-skeleton v-if="loading" :rows="4" animated />
    
    <!-- 非加载状态的内容 -->
    <template v-else>
      <!-- 文章列表 -->
      <div v-if="articles.length" class="space-y-1">
      <article 
        v-for="(article, index) in articles" 
        :key="article.id" 
        class="hot-article-item group cursor-pointer"
      >
        <router-link :to="'/article/' + article.slug" class="block">
          <div class="flex gap-3 items-baseline">
            <!-- 排名徽章 -->
            <div class="ranking-badge">
              {{ index + 1 }}
            </div>
            
            <!-- 文章信息 -->
            <div class="flex-1 min-w-0">
              <h4 class="article-title">
                {{ article.title }}
              </h4>
              <div class="article-meta">
                <span class="meta-item">
                  <el-icon size="12"><View /></el-icon>
                  {{ formatNumber(article.views_count || 0) }}
                </span>
                <span class="meta-item">
                  <el-icon size="12"><Star /></el-icon>
                  {{ formatNumber(article.likes_count || 0) }}
                </span>
                <span v-if="article.published_at" class="meta-item">
                  {{ formatDate(article.published_at) }}
                </span>
              </div>
            </div>
          </div>
        </router-link>
      </article>
      </div>
      
      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-icon size="48" class="mb-2 text-gray-300"><DataLine /></el-icon>
        <p class="text-sm text-gray-400">暂无热门文章</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { TrendCharts, View, Star, DataLine } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  articles: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// 调试信息（可在生产环境移除）
if (process.env.NODE_ENV === 'development') {
  console.log('HotArticlesCard - Props received:', {
    articles: props.articles,
    loading: props.loading,
    articlesLength: props.articles?.length
  });
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
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`
    
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

.hot-article-item {
  padding: 6px 8px; /* 进一步减少内边距，与最新卡片统一 */
  border-radius: 6px; /* 统一圆角大小 */
  transition: all 0.2s ease;
}

.hot-article-item:hover {
  background-color: rgb(249 250 251);
  transform: translateX(2px);
}

.hot-article-item a {
  text-decoration: none; /* 去掉链接下划线 */
}

.hot-article-item a:hover {
  text-decoration: none; /* 悬停时也不显示下划线 */
}

.ranking-badge {
  flex-shrink: 0;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 0.3125rem;
  background: linear-gradient(to bottom right, rgb(251 146 60), rgb(239 68 68));
  display: inline-flex; /* 关键：使用inline-flex参与baseline对齐 */
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 0.625rem;
  /* 移除所有手动计算，使用CSS原生baseline对齐 */
}

.article-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(17 24 39);
  transition: color 0.2s ease;
  margin-bottom: 0.25rem; /* 减少标题与元信息的间距 */
  line-height: 1.4; /* 统一行高 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.group:hover .article-title {
  color: rgb(37 99 235);
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: rgb(107 114 128);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.empty-state {
  text-align: center;
  color: rgb(156 163 175);
  padding: 2rem 0;
}

/* line-clamp utility */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>