<template>
  <div class="latest-articles-card" style="background-color: rgb(248 250 252); border-radius: 24px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; margin-bottom: 16px;">
    <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
      <el-icon class="text-green-500"><Clock /></el-icon>
      最新发布
    </h3>
    
    <!-- 加载状态 -->
    <el-skeleton v-if="loading" :rows="3" animated />
    
    <!-- 文章列表 -->
    <div v-else-if="articles.length" class="space-y-3">
      <article 
        v-for="article in articles" 
        :key="article.id" 
        class="latest-article-item group"
      >
        <router-link :to="'/article/' + article.slug" class="block">
          <div class="flex items-start gap-3">
            <!-- 时间指示器 -->
            <div class="time-indicator">
              <div class="time-dot"></div>
            </div>
            
            <!-- 文章信息 -->
            <div class="flex-1 min-w-0">
              <h4 class="article-title">
                {{ article.title }}
              </h4>
              <div class="article-meta">
                <span class="publish-time">
                  {{ formatDate(article.published_at) }}
                </span>
                <span v-if="article.category" class="category-tag">
                  {{ article.category }}
                </span>
              </div>
            </div>
          </div>
        </router-link>
      </article>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <el-icon size="48" class="mb-2 text-gray-300"><DocumentAdd /></el-icon>
      <p class="text-sm text-gray-400">暂无最新文章</p>
    </div>
    
    <!-- 查看更多 -->
    <div v-if="articles.length" class="mt-4 pt-4 border-t border-gray-100">
      <router-link 
        to="/" 
        class="view-more-link"
      >
        查看更多文章
        <el-icon size="12"><ArrowRight /></el-icon>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { Clock, DocumentAdd, ArrowRight } from '@element-plus/icons-vue'

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
  console.log('LatestArticlesCard - Props received:', {
    articles: props.articles,
    loading: props.loading,
    articlesLength: props.articles?.length
  });
}

// 工具函数
function formatDate(dateString) {
  if (!dateString) return ''
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = now - date
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
    const diffHours = Math.floor(diffTime / (1000 * 60 * 60))
    const diffMinutes = Math.floor(diffTime / (1000 * 60))
    
    if (diffMinutes < 1) return '刚刚'
    if (diffMinutes < 60) return `${diffMinutes}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
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

.latest-article-item {
  padding: 8px 0;
  transition: all 0.2s ease;
}

.latest-article-item:hover {
  transform: translateX(2px);
}

.time-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  margin-top: 0.25rem;
}

.time-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  background-color: rgb(74 222 128);
  box-shadow: 0 0 0 3px rgb(34 197 94 / 0.2);
}

.article-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(17 24 39);
  transition: color 0.2s ease;
  margin-bottom: 0.25rem;
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
  gap: 0.5rem;
  font-size: 0.75rem;
  color: rgb(107 114 128);
}

.publish-time {
  color: rgb(75 85 99);
}

.category-tag {
  padding: 0.125rem 0.5rem;
  background-color: rgb(243 244 246);
  color: rgb(75 85 99);
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.empty-state {
  text-align: center;
  color: rgb(156 163 175);
  padding: 2rem 0;
}

.view-more-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: rgb(37 99 235);
  transition: color 0.2s ease;
  font-weight: 500;
}

.view-more-link:hover {
  color: rgb(29 78 216);
}

.view-more-link:hover {
  transform: translateY(-1px);
}

/* line-clamp utility */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>