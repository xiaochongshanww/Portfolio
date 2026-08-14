<template>
  <header class="article-header">
    <!-- 管理状态（仅管理员可见） -->
    <div v-if="isModerator" class="admin-status-bar">
      <el-tag :type="getStatusType(article?.status)" size="small">
        {{ getStatusText(article?.status) }}
      </el-tag>
    </div>

    <!-- 面包屑导航 -->
    <nav class="breadcrumb-nav" aria-label="面包屑导航">
      <router-link to="/" class="breadcrumb-link">首页</router-link>
      <span class="breadcrumb-separator">/</span>
      <span v-if="article?.category" class="breadcrumb-item">{{ article.category }}</span>
      <span v-if="article?.category" class="breadcrumb-separator">/</span>
      <span class="breadcrumb-current">{{ article?.title }}</span>
    </nav>

    <!-- 文章标题 -->
    <h1 class="article-title">{{ article?.title }}</h1>

    <!-- 作者编辑操作区 -->
    <div v-if="canEdit" class="author-edit-actions">
      <el-button
        type="primary"
        size="small"
        :icon="Edit"
        class="edit-btn"
        @click="emit('edit')"
      >
        编辑文章
      </el-button>
      <span v-if="isAuthor" class="edit-hint">作为文章作者，您可以随时编辑</span>
      <span v-else-if="isModerator" class="edit-hint">管理员权限</span>
    </div>

    <!-- 文章元信息 -->
    <div class="article-meta">
      <div class="meta-primary">
        <!-- 作者信息 -->
        <div class="author-info">
          <div class="author-avatar">
            <img
              v-if="article?.author?.avatar"
              :src="article.author.avatar"
              :alt="article.author.name"
              class="avatar-img"
              @error="handleAuthorAvatarError"
            >
            <div v-else class="avatar-fallback">
              <i class="fa fa-user" aria-hidden="true" />
            </div>
          </div>
          <div class="author-details">
            <span class="author-name">{{ article?.author?.name || '匿名作者' }}</span>
            <time class="publish-date" :datetime="article?.published_at || article?.created_at || undefined">
              {{ formatPublishDate(article?.published_at || article?.created_at || '') }}
            </time>
          </div>
        </div>

        <!-- 文章统计 -->
        <div class="article-stats">
          <span class="stat-item">
            <i class="fa fa-clock-o" aria-hidden="true" />
            {{ calculateReadTime(article?.content_md || article?.content_html || '') }} 分钟阅读
          </span>
          <span class="stat-item">
            <i class="fa fa-eye" aria-hidden="true" />
            {{ formatNumber(article?.views_count || 0) }} 次浏览
          </span>
          <span class="stat-item">
            <i class="fa fa-heart-o" aria-hidden="true" />
            {{ formatNumber(article?.likes_count || 0) }} 点赞
          </span>
        </div>
      </div>

      <!-- 分类和标签 -->
      <div class="article-taxonomy">
        <!-- 文章分类 -->
        <div v-if="article?.category" class="article-category">
          <router-link :to="`/category/${article?.category_id || article?.category}`" class="category-link">
            <el-tag
              size="small"
              type="primary"
              effect="plain"
              class="category-tag"
            >
              <i class="fa fa-folder-o" aria-hidden="true" />
              {{ article?.category }}
            </el-tag>
          </router-link>
        </div>

        <!-- 标签 -->
        <div v-if="article?.tags && article.tags.length" class="article-tags">
          <el-tag
            v-for="tag in article.tags"
            :key="tag"
            size="small"
            type="info"
            effect="plain"
            class="tag-item"
          >
            <i class="fa fa-tag" aria-hidden="true" />
            {{ tag }}
          </el-tag>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Edit } from '@element-plus/icons-vue'
import type { Article } from '../types'

defineProps<{
  article: Article | null
  canEdit: boolean
  isAuthor: boolean
  isModerator: boolean
}>()

const emit = defineEmits<{
  edit: []
}>()

/** @param {Event} e */
function handleAuthorAvatarError(e: Event) {
  ;(e.target as HTMLElement).style.display = 'none'
}

/** @param {number} num */
function formatNumber(num: number) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return String(num)
}

/** @param {string} dateString */
function formatPublishDate(dateString: string) {
  if (!dateString) return ''

  try {
    let processedDateString = dateString
    if (!processedDateString.endsWith('Z') && !processedDateString.includes('+') && !processedDateString.includes('-', 10)) {
      processedDateString += 'Z'
    }

    const date = new Date(processedDateString)
    const now = new Date()

    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMinutes < 1) return '刚刚'
    if (diffMinutes < 60) return `${diffMinutes}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays}天前`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}个月前`

    return date.toLocaleDateString('zh-CN')
  } catch (error) {
    console.warn('formatPublishDate error:', error, 'input:', dateString)
    return ''
  }
}

/** @param {string} content */
function calculateReadTime(content: string) {
  if (!content) return 0
  const plainText = content.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()
  const chineseChars = (plainText.match(/[\u4e00-\u9fa5]/g) || []).length
  const englishWords = (plainText.replace(/[\u4e00-\u9fa5]/g, '').match(/\b\w+\b/g) || []).length
  const totalWords = chineseChars + englishWords
  return Math.max(1, Math.ceil(totalWords / 275))
}

/** @param {string | undefined} status */
function getStatusType(status?: string) {
  const statusMap: Record<string, 'info' | 'success' | 'primary' | 'warning' | 'danger'> = {
    'draft': 'info',
    'pending': 'warning',
    'published': 'success',
    'scheduled': 'primary'
  }
  return statusMap[status || ''] || 'info'
}

/** @param {string | undefined} status */
function getStatusText(status?: string) {
  const statusMap: Record<string, string> = {
    'draft': '草稿',
    'pending': '待审核',
    'published': '已发布',
    'scheduled': '定时发布'
  }
  return statusMap[status || ''] || status
}
</script>

<style scoped>
.article-header {
  padding: 3rem 3rem 2rem;
  background: linear-gradient(135deg, rgb(255 255 255) 0%, rgb(248 250 252) 100%);
}

.admin-status-bar {
  margin-bottom: 1rem;
}

.breadcrumb-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 2rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.breadcrumb-link {
  color: #3b82f6;
  text-decoration: none;
  transition: color 0.2s ease;
}

.breadcrumb-link:hover {
  color: #2563eb;
}

.breadcrumb-separator {
  color: #9ca3af;
}

.breadcrumb-current {
  color: #374151;
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-title {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1.2;
  color: #111827;
  margin-bottom: 1rem;
  letter-spacing: -0.025em;
}

.author-edit-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  transition: all 0.2s ease;
}

.author-edit-actions:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.edit-btn {
  font-size: 0.875rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.edit-hint {
  font-size: 0.875rem;
}

.article-meta {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.meta-primary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.author-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.author-avatar {
  width: 3rem;
  height: 3rem;
  border-radius: 9999px;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  font-size: 1.25rem;
}

.author-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.author-name {
  font-weight: 600;
  color: #111827;
}

.publish-date {
  font-size: 0.875rem;
  color: #6b7280;
}

.article-stats {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.article-taxonomy {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.category-link {
  text-decoration: none;
}

.tag-item {
  margin-right: 0.5rem;
}
</style>
