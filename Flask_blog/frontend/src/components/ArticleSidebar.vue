<template>
  <aside class="article-sidebar">
    <!-- 文章目录 -->
    <div class="sidebar-section toc-section">
      <h3 class="sidebar-title">目录</h3>
      <nav v-if="tocItems.length" class="table-of-contents">
        <ol class="toc-list">
          <li
            v-for="item in tocItems"
            :key="item.id"
            :class="['toc-item', `toc-level-${item.level}`, { 'active': activeHeading === item.id }]"
          >
            <a
              :href="`#${item.id}`"
              class="toc-link"
              @click.prevent="emit('scroll-to', item.id || '')"
            >
              {{ item.text }}
            </a>
          </li>
        </ol>
      </nav>
      <p v-else class="toc-empty">暂无目录</p>
    </div>

    <!-- 阅读进度 -->
    <div class="sidebar-section progress-section">
      <h3 class="sidebar-title">阅读进度</h3>
      <div class="reading-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: readingProgress + '%' }" />
        </div>
        <span class="progress-text">{{ Math.round(readingProgress) }}%</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
export interface TOCItem {
  id?: string
  text?: string
  level?: number
}

defineProps<{
  tocItems: TOCItem[]
  activeHeading: string
  readingProgress: number
}>()

const emit = defineEmits<{
  'scroll-to': [id: string]
}>()
</script>

<style scoped>
.article-sidebar {
  position: sticky;
  top: 2rem;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .article-sidebar {
    position: static;
    max-height: none;
    order: 2;
  }
}

.sidebar-section {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #f3f4f6;
}

.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-item {
  margin: 0.25rem 0;
}

.toc-link {
  display: block;
  padding: 0.5rem 0.75rem;
  color: #6b7280;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.4;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.toc-link:hover {
  background: #f3f4f6;
  color: #374151;
}

.toc-item.active .toc-link {
  background: #eff6ff;
  color: #2563eb;
  border-left-color: #3b82f6;
  font-weight: 500;
}

.toc-level-2 .toc-link { padding-left: 1.5rem; }
.toc-level-3 .toc-link { padding-left: 2.25rem; }
.toc-level-4 .toc-link { padding-left: 3rem; }

.toc-empty {
  color: #9ca3af;
  font-size: 0.875rem;
  text-align: center;
  margin: 0;
  padding: 1rem;
}

.reading-progress {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  min-width: 40px;
}
</style>
