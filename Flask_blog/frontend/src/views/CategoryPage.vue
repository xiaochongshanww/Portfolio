<template>
  <div class="category-page">
    <!-- 加载状态 -->
    <div v-if="!loaded" class="loading-container">
      <div class="loading-content">
        <el-skeleton :rows="8" animated />
        <div class="loading-text">正在加载分类内容...</div>
      </div>
    </div>

    <!-- 主要内容 -->
    <div v-else class="category-content">
      <!-- 分类头部 -->
      <header class="category-header">
        <div class="header-background"></div>
        <div class="header-content">
          <!-- 面包屑导航 -->
          <nav class="breadcrumb-nav" aria-label="面包屑导航">
            <router-link to="/" class="breadcrumb-link">首页</router-link>
            <span class="breadcrumb-separator">/</span>
            <router-link to="/categories" class="breadcrumb-link">分类</router-link>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ categoryName || (loaded ? slugOrId : '加载中...') }}</span>
          </nav>

          <!-- 分类信息 -->
          <div class="category-info">
            <div class="category-icon">
              <i class="fa fa-folder-open" aria-hidden="true"></i>
            </div>
            <div class="category-details">
              <h1 class="category-title">{{ categoryName || (loaded ? `分类 ${slugOrId}` : '正在加载...') }}</h1>
              <p class="category-description">
                {{ categoryDescription || (loaded ? `探索 ${categoryName || '该分类'} 下的所有精彩文章` : '正在获取分类信息...') }}
              </p>
              <div class="category-stats">
                <span class="stat-item">
                  <i class="fa fa-file-text-o" aria-hidden="true"></i>
                  {{ articles.length }} 篇文章
                </span>
                <span class="stat-item" v-if="lastUpdated">
                  <i class="fa fa-clock-o" aria-hidden="true"></i>
                  最近更新: {{ formatDate(lastUpdated) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- 文章列表区域 -->
      <main class="articles-section">
        <div class="container">
          <!-- 排序和筛选 -->
          <div class="articles-controls">
            <div class="view-options">
              <el-button-group>
                <el-button 
                  :type="viewMode === 'grid' ? 'primary' : ''" 
                  @click="viewMode = 'grid'"
                  :icon="Grid"
                  size="small"
                >
                  网格
                </el-button>
                <el-button 
                  :type="viewMode === 'list' ? 'primary' : ''" 
                  @click="viewMode = 'list'"
                  :icon="List"
                  size="small"
                >
                  列表
                </el-button>
              </el-button-group>
            </div>
            
            <div class="sort-options">
              <el-select v-model="sortBy" size="small" style="width: 120px" @change="sortArticles">
                <el-option label="最新发布" value="date_desc" />
                <el-option label="最早发布" value="date_asc" />
                <el-option label="标题A-Z" value="title_asc" />
                <el-option label="标题Z-A" value="title_desc" />
              </el-select>
            </div>
          </div>

          <!-- 文章网格/列表 -->
          <div v-if="articles.length > 0" :class="['articles-container', `view-${viewMode}`]">
            <article 
              v-for="article in sortedArticles" 
              :key="article.id"
              class="article-card"
              @click="navigateToArticle(article.slug)"
            >
              <!-- 封面图片 -->
              <div class="article-image">
                <img 
                  v-if="article.featured_image" 
                  :src="article.featured_image" 
                  :alt="article.title"
                  class="article-img"
                  loading="lazy"
                />
                <div v-else class="article-img-placeholder">
                  <i class="fa fa-file-text-o" aria-hidden="true"></i>
                </div>
              </div>

              <!-- 文章内容 -->
              <div class="article-content">
                <h2 class="article-title">{{ article.title }}</h2>
                <p class="article-summary">{{ article.summary || '暂无摘要，点击查看完整内容...' }}</p>
                
                <!-- 文章元信息 -->
                <div class="article-meta">
                  <div class="meta-primary">
                    <span class="author" v-if="article.author">
                      <i class="fa fa-user" aria-hidden="true"></i>
                      {{ article.author.name || article.author.nickname }}
                    </span>
                    <time class="publish-date" :datetime="article.published_at || article.created_at">
                      <i class="fa fa-calendar" aria-hidden="true"></i>
                      {{ formatDate(article.published_at || article.created_at) }}
                    </time>
                  </div>
                  
                  <div class="meta-secondary">
                    <span class="views" v-if="article.views_count">
                      <i class="fa fa-eye" aria-hidden="true"></i>
                      {{ formatNumber(article.views_count) }}
                    </span>
                    <span class="likes" v-if="article.likes_count">
                      <i class="fa fa-heart-o" aria-hidden="true"></i>
                      {{ formatNumber(article.likes_count) }}
                    </span>
                  </div>
                </div>

                <!-- 标签 -->
                <div class="article-tags">
                  <template v-if="article.tags && article.tags.length">
                    <el-tag 
                      v-for="tag in article.tags.slice(0, 3)" 
                      :key="tag" 
                      size="small" 
                      type="info" 
                      effect="plain"
                      class="tag-item"
                    >
                      {{ tag }}
                    </el-tag>
                    <span v-if="article.tags.length > 3" class="more-tags">
                      +{{ article.tags.length - 3 }}
                    </span>
                  </template>
                  <span v-else class="no-tags">暂无标签</span>
                </div>
              </div>

              <!-- 阅读更多按钮 -->
              <div class="article-action">
                <el-button type="primary" size="small" class="read-more-btn">
                  阅读全文
                  <i class="fa fa-arrow-right" aria-hidden="true"></i>
                </el-button>
              </div>
            </article>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">
                <i class="fa fa-folder-open-o" aria-hidden="true"></i>
              </div>
              <h3 class="empty-title">暂无文章</h3>
              <p class="empty-description">该分类下还没有发布任何文章</p>
              <el-button type="primary" @click="$router.push('/')">
                浏览其他内容
              </el-button>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
const props = withDefaults(defineProps<{ id?: string|number }>(), { id: "" })
import { setMeta, injectJsonLd } from '../composables/useMeta';
import { Grid, List } from '@element-plus/icons-vue';
import { API } from '../api';

const route = useRoute();
const router = useRouter();
const loaded = ref(false);
const articles = ref([]);
const slugOrId = ref(props.id || route.params.id || route.params.slug);
const categoryName = ref('');
const categoryDescription = ref('');
const lastUpdated = ref(null);
const viewMode = ref('grid'); // 'grid' or 'list'
const sortBy = ref('date_desc');

// 计算排序后的文章列表
const sortedArticles = computed(() => {
  const articlesArray = [...articles.value];
  
  switch (sortBy.value) {
    case 'date_asc':
      return articlesArray.sort((a, b) => 
        new Date(a.published_at || a.created_at) - new Date(b.published_at || b.created_at)
      );
    case 'date_desc':
      return articlesArray.sort((a, b) => 
        new Date(b.published_at || b.created_at) - new Date(a.published_at || a.created_at)
      );
    case 'title_asc':
      return articlesArray.sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'));
    case 'title_desc':
      return articlesArray.sort((a, b) => b.title.localeCompare(a.title, 'zh-CN'));
    default:
      return articlesArray;
  }
});

async function load() {
  loaded.value = false;
  
  try {
    // 获取分类信息
    console.log('🔍 正在获取分类信息，ID:', slugOrId.value);
    const response = await fetch('/public/v1/taxonomy');
    const result = await response.json();
    const cats = result.data?.categories || [];
    console.log('📋 获取到分类列表:', cats);
    const idNum = Number(slugOrId.value);
    const category = cats.find(c => c.id === idNum);
    console.log('🎯 匹配到的分类:', category);
    
    if (category) {
      categoryName.value = category.name;
      categoryDescription.value = category.description || '';
      console.log('✅ 分类信息设置成功:', categoryName.value);
    } else {
      console.warn('⚠️ 未找到匹配的分类，ID:', idNum);
      // 如果通过API找不到分类，尝试设置一个默认名称
      categoryName.value = `分类 ${slugOrId.value}`;
    }
  } catch (e) {
    console.error('❌ 加载分类信息失败:', e);
    // API失败时的后备方案
    categoryName.value = `分类 ${slugOrId.value}`;
  }
  
  try {
    // 获取文章列表
    const resp = await fetch(`/api/v1/articles/public?category_id=${slugOrId.value}`);
    const j = await resp.json();
    articles.value = j.data?.list || [];
    
    // 计算最近更新时间
    if (articles.value.length > 0) {
      const dates = articles.value.map(a => new Date(a.published_at || a.created_at));
      lastUpdated.value = new Date(Math.max(...dates));
    }
  } catch (e) {
    console.error('Failed to load articles:', e);
    articles.value = [];
  }
  
  // 设置SEO元信息
  const url = window.location.href;
  setMeta({
    title: `${categoryName.value || `分类 ${slugOrId.value}`} - 文章列表`,
    description: categoryDescription.value || `浏览 ${categoryName.value || '该分类'} 下的所有文章，发现更多精彩内容`,
    image: articles.value[0]?.featured_image,
    url
  });
  
  // 注入结构化数据
  injectJsonLd({
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: `分类: ${categoryName.value || slugOrId.value}`,
    description: categoryDescription.value || `${categoryName.value || '该分类'} 下的文章列表`,
    url,
    mainEntity: {
      '@type': 'ItemList',
      numberOfItems: articles.value.length,
      itemListElement: articles.value.map((a, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: window.location.origin + '/article/' + a.slug,
        name: a.title,
        description: a.summary
      }))
    }
  });
  
  loaded.value = true;
}

// 导航到文章详情页
function navigateToArticle(slug) {
  router.push(`/article/${slug}`);
}

// 排序文章
function sortArticles() {
  // 排序逻辑在 computed 中处理
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '';
  
  const date = new Date(dateStr);
  const now = new Date();
  const diffTime = now - date;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 1) return '昨天';
  if (diffDays === 0) return '今天';
  if (diffDays <= 7) return `${diffDays}天前`;
  if (diffDays <= 30) return `${Math.ceil(diffDays / 7)}周前`;
  if (diffDays <= 365) return `${Math.ceil(diffDays / 30)}个月前`;
  
  return date.toLocaleDateString('zh-CN');
}

// 格式化数字
function formatNumber(num) {
  if (!num) return '0';
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return num.toString();
}

onMounted(load);
watch(() => props.id || route.params.id, (newId) => {
  if (newId) {
    slugOrId.value = newId;
    load();
  }
});
</script>
<style scoped>
/* 全局布局 */
.category-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-attachment: fixed;
}

/* 加载状态 */
.loading-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

.loading-content {
  text-align: center;
  max-width: 600px;
  width: 100%;
  padding: 2rem;
}

.loading-text {
  margin-top: 1.5rem;
  font-size: 1.1rem;
  color: #666;
  font-weight: 500;
}

/* 分类头部 */
.category-header {
  position: relative;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
  color: white;
  padding: 3rem 0 4rem;
  margin-bottom: 2rem;
  overflow: hidden;
}

.category-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 100" fill="white" opacity="0.1"><polygon points="0,0 1000,0 1000,80 0,100"/></svg>') no-repeat bottom;
  background-size: cover;
}

.header-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
}

.header-content {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

/* 面包屑导航 */
.breadcrumb-nav {
  margin-bottom: 2rem;
  font-size: 0.9rem;
  opacity: 0.9;
}

.breadcrumb-link {
  color: white;
  text-decoration: none;
  transition: opacity 0.3s ease;
}

.breadcrumb-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.breadcrumb-separator {
  margin: 0 0.5rem;
  opacity: 0.7;
}

.breadcrumb-current {
  opacity: 0.9;
  font-weight: 500;
}

/* 分类信息 */
.category-info {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
}

.category-icon {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 1rem;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.category-icon i {
  font-size: 2rem;
  color: white;
}

.category-details {
  flex: 1;
}

.category-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.category-description {
  font-size: 1.1rem;
  margin: 0 0 1.5rem 0;
  opacity: 0.9;
  line-height: 1.6;
}

.category-stats {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.5rem 1rem;
  border-radius: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.9rem;
}

.stat-item i {
  opacity: 0.8;
}

/* 主要内容区域 */
.articles-section {
  background: white;
  border-radius: 20px 20px 0 0;
  margin-top: -1rem;
  position: relative;
  z-index: 1;
  min-height: 60vh;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

/* 文章控制栏 */
.articles-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 1rem 0;
  border-bottom: 2px solid #f5f5f5;
}

.view-options .el-button-group {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.sort-options .el-select {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

/* 文章容器 */
.articles-container {
  margin-top: 2rem;
}

.articles-container.view-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
  align-items: stretch;
}

.articles-container.view-list .article-card {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding: 2rem;
}

.articles-container.view-list .article-image {
  flex-shrink: 0;
  width: 200px;
  height: 120px;
}

.articles-container.view-list .article-content {
  flex: 1;
}

.articles-container.view-list .article-card {
  height: auto; /* 列表视图允许自适应高度 */
}

.articles-container.view-list .article-title {
  min-height: auto; /* 列表视图标题高度自适应 */
}

.articles-container.view-list .article-summary {
  min-height: auto; /* 列表视图摘要高度自适应 */
}

.articles-container.view-list .article-tags {
  min-height: auto; /* 列表视图标签高度自适应 */
  margin-top: 0; /* 列表视图不需要推到底部 */
}

/* 文章卡片 */
.article-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.05);
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.article-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.article-card:hover::before {
  transform: scaleX(1);
}

.article-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  border-color: rgba(102, 126, 234, 0.2);
}

/* 文章图片 */
.article-image {
  width: 100%;
  height: 200px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.article-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.article-card:hover .article-img {
  transform: scale(1.05);
}

.article-img-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.article-img-placeholder i {
  font-size: 3rem;
  opacity: 0.7;
}

/* 文章内容 */
.article-content {
  padding: 1.5rem;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.article-title {
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0 0 0.8rem 0;
  line-height: 1.4;
  color: #2c3e50;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.3s ease;
  min-height: 3.6rem; /* 确保标题区域高度一致，可容纳2行文字 */
}

.article-card:hover .article-title {
  color: #667eea;
}

.article-summary {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.6;
  margin: 0 0 1rem 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 4.3rem; /* 确保摘要区域高度一致，可容纳3行文字 */
}

/* 文章元信息 */
.article-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  font-size: 0.8rem;
  color: #888;
}

.meta-primary {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.meta-secondary {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.author, .publish-date, .views, .likes {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.author i, .publish-date i, .views i, .likes i {
  opacity: 0.7;
}

/* 文章标签 */
.article-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 1rem;
  min-height: 2rem; /* 确保标签区域高度一致 */
  margin-top: auto; /* 将标签区域推到底部 */
}

.tag-item {
  font-size: 0.75rem;
  border-radius: 12px;
}

.more-tags {
  font-size: 0.75rem;
  color: #999;
  background: #f5f5f5;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
}

.no-tags {
  font-size: 0.75rem;
  color: #ccc;
  font-style: italic;
}

/* 文章操作 */
.article-action {
  padding: 0 1.5rem 1.5rem;
}

.read-more-btn {
  width: 100%;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.read-more-btn:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.empty-content {
  max-width: 400px;
  margin: 0 auto;
}

.empty-icon {
  margin-bottom: 2rem;
}

.empty-icon i {
  font-size: 4rem;
  color: #ddd;
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
  color: #999;
}

.empty-description {
  font-size: 1rem;
  margin: 0 0 2rem 0;
  line-height: 1.6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .category-header {
    padding: 2rem 0 3rem;
  }
  
  .header-content {
    padding: 0 1rem;
  }
  
  .category-info {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .category-title {
    font-size: 2rem;
  }
  
  .category-stats {
    justify-content: center;
    gap: 1rem;
  }
  
  .container {
    padding: 1rem;
  }
  
  .articles-controls {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .articles-container.view-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .articles-container.view-list .article-card {
    flex-direction: column;
    padding: 1.5rem;
  }
  
  .articles-container.view-list .article-image {
    width: 100%;
    height: 200px;
  }
}

@media (max-width: 480px) {
  .category-title {
    font-size: 1.8rem;
  }
  
  .category-stats {
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  
  .article-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .meta-primary, .meta-secondary {
    justify-content: space-between;
    width: 100%;
  }
}

/* 动画效果 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.article-card {
  animation: fadeInUp 0.6s ease-out;
}

.article-card:nth-child(2) { animation-delay: 0.1s; }
.article-card:nth-child(3) { animation-delay: 0.2s; }
.article-card:nth-child(4) { animation-delay: 0.3s; }
.article-card:nth-child(5) { animation-delay: 0.4s; }
.article-card:nth-child(6) { animation-delay: 0.5s; }
</style>
