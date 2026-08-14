<template>
  <footer class="article-footer">
    <!-- 点赞收藏区 -->
    <div class="interaction-section">
      <div class="interaction-buttons">
        <button
          :disabled="liking"
          :class="['interaction-btn', 'like-btn', {
            'liked': liked,
            'liking': liking
          }]"
          @click="emit('like')"
        >
          <div class="like-btn-content">
            <div class="like-icon-wrapper">
              <i v-if="!liking" :class="liked ? 'fa fa-heart' : 'fa fa-heart-o'" aria-hidden="true" />
              <div v-else class="like-loading-spinner">
                <i class="fa fa-heart beating-heart" aria-hidden="true" />
              </div>
            </div>
            <span class="like-text">{{ liking ? '处理中...' : (liked ? '已点赞' : '点赞') }}</span>
            <span class="count">({{ formatNumber(likeCount) }})</span>
          </div>
        </button>

        <button
          :disabled="bookmarking"
          :class="['interaction-btn', 'bookmark-btn', { 'bookmarked': bookmarked }]"
          @click="emit('bookmark')"
        >
          <i :class="bookmarked ? 'fa fa-bookmark' : 'fa fa-bookmark-o'" aria-hidden="true" />
          <span>{{ bookmarked ? '已收藏' : '收藏' }}</span>
          <span class="count">{{ formatNumber(bookmarkCount) }}</span>
        </button>

        <button class="interaction-btn share-btn" @click="emit('share')">
          <i class="fa fa-share-alt" aria-hidden="true" />
          <span>分享</span>
        </button>
      </div>
    </div>

    <!-- 分隔线 -->
    <div class="section-divider" />

    <!-- 作者信息卡片 -->
    <div class="author-card">
      <div class="author-card-avatar">
        <img
          v-if="article?.author?.avatar"
          :src="article.author.avatar"
          :alt="article.author.name || ''"
          class="author-card-img"
        >
        <div v-else class="author-card-fallback">
          <i class="fa fa-user" aria-hidden="true" />
        </div>
      </div>
      <div class="author-card-info">
        <h3 class="author-card-name">{{ article?.author?.name || '匿名作者' }}</h3>
        <p class="author-card-bio">{{ article?.author?.bio || '这位作者很神秘，还没有添加个人简介。' }}</p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import type { Article } from '../types'

defineProps<{
  liked: boolean
  liking: boolean
  likeCount: number
  bookmarked: boolean
  bookmarking: boolean
  bookmarkCount: number
  article: Article | null
}>()

const emit = defineEmits<{
  like: []
  bookmark: []
  share: []
}>()

/** @param {number} num */
function formatNumber(num: number) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return String(num)
}
</script>

<style scoped>
.article-footer {
  padding: 0 3rem 3rem;
}

.interaction-section {
  margin-top: 2rem;
}

.interaction-buttons {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.interaction-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  background: white;
  color: #4b5563;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.interaction-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.interaction-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.like-btn.liked {
  border-color: #ef4444;
  background: #fef2f2;
  color: #ef4444;
}

.like-btn.liked:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.bookmark-btn.bookmarked {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #3b82f6;
}

.bookmark-btn.bookmarked:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.like-btn-content {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.like-icon-wrapper {
  display: inline-flex;
  align-items: center;
}

.beating-heart {
  animation: beat 0.8s ease-in-out infinite;
}

@keyframes beat {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.3); }
}

.count {
  font-weight: 600;
  color: #9ca3af;
}

.section-divider {
  height: 1px;
  background: linear-gradient(to right, transparent, #e5e7eb, transparent);
  margin: 2rem 0;
}

.author-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 16px;
}

.author-card-avatar {
  width: 4rem;
  height: 4rem;
  border-radius: 9999px;
  overflow: hidden;
  flex-shrink: 0;
}

.author-card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-card-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  font-size: 1.5rem;
}

.author-card-info {
  flex: 1;
}

.author-card-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.5rem;
}

.author-card-bio {
  color: #6b7280;
  line-height: 1.5;
  margin: 0;
}
</style>
