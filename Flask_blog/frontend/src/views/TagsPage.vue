<template>
  <div class="tags-page">
    <div class="max-w-6xl mx-auto py-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-4">标签云</h1>
        <p class="text-gray-600 max-w-2xl mx-auto">
          探索博客的所有文章标签，发现感兴趣的主题内容
        </p>
      </div>

      <!-- 现代化统计面板 -->
      <div class="modern-stats-grid">
        <div class="stat-card stat-card-blue">
          <div class="stat-icon-wrapper">
            <el-icon size="24"><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ tags.length }}</div>
            <div class="stat-label">总标签数</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        
        <div class="stat-card stat-card-green">
          <div class="stat-icon-wrapper">
            <el-icon size="24"><Reading /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ totalArticles }}</div>
            <div class="stat-label">关联文章</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        
        <div class="stat-card stat-card-purple">
          <div class="stat-icon-wrapper">
            <el-icon size="24"><Star /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ popularTags.length }}</div>
            <div class="stat-label">热门标签</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        
        <div class="stat-card stat-card-orange">
          <div class="stat-icon-wrapper">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ averagePerTag }}</div>
            <div class="stat-label">平均文章数</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
      </div>

      <!-- 现代化视图切换器 -->
      <div class="modern-view-switcher">
        <div class="view-switcher-container">
          <div class="switcher-background"></div>
          <button 
            v-for="view in viewModes" 
            :key="view.value"
            @click="currentView = view.value"
            :class="[
              'view-switcher-btn',
              currentView === view.value ? 'active' : ''
            ]"
          >
            <div class="btn-icon-wrapper">
              <el-icon size="18"><component :is="view.icon" /></el-icon>
            </div>
            <span class="btn-label">{{ view.label }}</span>
            <div class="btn-glow"></div>
          </button>
        </div>
      </div>

      <!-- 标签云视图 -->
      <div v-if="currentView === 'cloud'" class="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 mb-8">
        <div class="tag-cloud">
          <button
            v-for="tag in tags" 
            :key="tag.id"
            @click="handleTagClick(tag.slug)"
            :class="getTagCloudClass(tag.article_count || 0)"
            class="tag-cloud-item"
          >
            #{{ tag.name }}
            <span class="tag-count">({{ tag.article_count || 0 }})</span>
          </button>
        </div>
      </div>

      <!-- 卡片网格视图 -->
      <div v-if="currentView === 'grid'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div v-for="tag in tags" :key="tag.id" class="modern-tag-card group">
          <button @click="handleTagClick(tag.slug)" class="tag-card-button">
            <!-- 卡片头部 -->
            <div class="card-header">
              <div class="tag-icon">
                <el-icon size="20"><Document /></el-icon>
              </div>
              <div class="article-count">
                {{ tag.article_count || 0 }}
              </div>
            </div>
            
            <!-- 卡片内容 -->
            <div class="card-content">
              <h3 class="tag-title">#{{ tag.name }}</h3>
              <p class="tag-description">{{ tag.description || `探索与"${tag.name}"相关的精彩内容` }}</p>
            </div>
            
            <!-- 卡片底部 -->
            <div class="card-footer">
              <span class="explore-text">浏览文章</span>
              <div class="arrow-icon">
                <el-icon size="16"><ArrowRight /></el-icon>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- 现代化列表视图 -->
      <div v-if="currentView === 'list'" class="modern-list-container">
        <div class="list-header">
          <h3 class="list-title">所有标签</h3>
          <p class="list-subtitle">点击标签查看相关文章</p>
        </div>
        <div class="divide-y divide-gray-50">
          <div 
            v-for="tag in sortedTags" 
            :key="tag.id"
            @click="handleTagClick(tag.slug)"
            class="tag-list-item flex items-center justify-between group"
          >
            <div class="flex items-center gap-3">
              <div class="tag-list-icon">
                <el-icon size="18"><Document /></el-icon>
              </div>
              <div>
                <div class="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                  #{{ tag.name }}
                </div>
                <div class="text-sm text-gray-500">
                  {{ tag.description || '暂无描述' }}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-sm text-gray-500">{{ tag.article_count || 0 }} 篇文章</span>
              <el-icon class="text-gray-400 group-hover:text-blue-500 transition-colors">
                <ArrowRight />
              </el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <el-icon class="animate-spin text-2xl text-blue-500 mr-3"><Loading /></el-icon>
        <span class="text-gray-600">加载标签中...</span>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && tags.length === 0" class="text-center py-12">
        <el-icon class="text-6xl text-gray-300 mb-4"><Document /></el-icon>
        <h3 class="text-xl font-medium text-gray-900 mb-2">暂无标签</h3>
        <p class="text-gray-600">还没有任何标签，快去创建第一篇文章吧！</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Document, ArrowRight, Loading, Grid, List, Compass, Reading, Star, TrendCharts } from '@element-plus/icons-vue';
import apiClient from '../apiClient';
import { setMeta } from '../composables/useMeta';

const router = useRouter();
const tags = ref([]);
const loading = ref(false);
const currentView = ref('cloud');

const viewModes = [
  { label: '标签云', value: 'cloud', icon: 'Compass' },
  { label: '网格', value: 'grid', icon: 'Grid' },
  { label: '列表', value: 'list', icon: 'List' }
];

// 计算属性
const totalArticles = computed(() => {
  return tags.value.reduce((sum, tag) => sum + (tag.article_count || 0), 0);
});

const popularTags = computed(() => {
  return tags.value.filter(tag => (tag.article_count || 0) >= 3);
});

const averagePerTag = computed(() => {
  return tags.value.length > 0 ? Math.round(totalArticles.value / tags.value.length) : 0;
});

const sortedTags = computed(() => {
  return [...tags.value].sort((a, b) => (b.article_count || 0) - (a.article_count || 0));
});

// 方法
async function loadTags() {
  loading.value = true;
  try {
    const response = await apiClient.get('/taxonomy/tags/');
    tags.value = response.data.data || [];
    
    // 设置SEO元数据
    setMeta({
      title: '标签云 - 发现更多主题',
      description: `浏览博客的所有文章标签，发现感兴趣的主题内容。共有 ${tags.value.length} 个标签，涵盖 ${totalArticles.value} 篇文章`,
      url: window.location.href
    });
  } catch (error) {
    console.error('加载标签失败:', error);
  } finally {
    loading.value = false;
  }
}

function handleTagClick(tagSlug) {
  router.push(`/tag/${tagSlug}`);
}

function getTagCloudClass(count) {
  if (count >= 10) return 'tag-cloud-xl';
  if (count >= 7) return 'tag-cloud-lg';
  if (count >= 4) return 'tag-cloud-md';
  if (count >= 2) return 'tag-cloud-sm';
  return 'tag-cloud-xs';
}

onMounted(loadTags);
</script>

<style scoped>
.tags-page {
  background: 
    radial-gradient(circle at 20% 50%, rgba(59, 130, 246, 0.03) 0%, transparent 40%),
    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.03) 0%, transparent 40%),
    radial-gradient(circle at 40% 80%, rgba(6, 182, 212, 0.03) 0%, transparent 40%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 30%, #ffffff 70%, #fafbfe 100%);
  min-height: 100vh;
  padding: 3rem 1rem;
  position: relative;
  overflow: hidden;
}

.tags-page::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background-image: 
    radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: float 20s ease-in-out infinite;
  pointer-events: none;
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(2deg); }
}

/* ===== 现代化统计面板样式 ===== */
.modern-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  padding: 2rem;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--stat-gradient));
  transform: scaleX(0);
  transition: transform 0.5s ease;
  transform-origin: left;
  border-radius: 24px 24px 0 0;
}

.stat-card:hover::before {
  transform: scaleX(1);
}

.stat-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 25px 50px rgba(0, 0, 0, 0.1),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.95);
}

.stat-decoration {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, var(--stat-decoration) 0%, transparent 70%);
  transform: scale(0);
  transition: transform 0.6s ease;
  pointer-events: none;
  opacity: 0.1;
}

.stat-card:hover .stat-decoration {
  transform: scale(1);
}

.stat-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: var(--stat-gradient);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 8px 32px var(--stat-shadow);
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
}

.stat-icon-wrapper::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.2) 50%, transparent 70%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.stat-card:hover .stat-icon-wrapper {
  transform: rotate(-8deg) scale(1.15);
  box-shadow: 0 12px 40px var(--stat-shadow);
}

.stat-card:hover .stat-icon-wrapper::before {
  transform: rotate(45deg) translateX(100%);
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 800;
  background: var(--stat-gradient);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
  letter-spacing: -0.025em;
  transition: all 0.4s ease;
}

.stat-card:hover .stat-number {
  transform: scale(1.1);
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: color 0.3s ease;
}

.stat-card:hover .stat-label {
  color: #475569;
}

/* 不同主题色彩 */
.stat-card-blue {
  --stat-gradient: linear-gradient(135deg, #3b82f6, #1d4ed8);
  --stat-shadow: rgba(59, 130, 246, 0.25);
  --stat-decoration: rgba(59, 130, 246, 0.1);
}

.stat-card-green {
  --stat-gradient: linear-gradient(135deg, #10b981, #059669);
  --stat-shadow: rgba(16, 185, 129, 0.25);
  --stat-decoration: rgba(16, 185, 129, 0.1);
}

.stat-card-purple {
  --stat-gradient: linear-gradient(135deg, #8b5cf6, #7c3aed);
  --stat-shadow: rgba(139, 92, 246, 0.25);
  --stat-decoration: rgba(139, 92, 246, 0.1);
}

.stat-card-orange {
  --stat-gradient: linear-gradient(135deg, #f59e0b, #d97706);
  --stat-shadow: rgba(245, 158, 11, 0.25);
  --stat-decoration: rgba(245, 158, 11, 0.1);
}

/* ===== 现代化视图切换器样式 ===== */
.modern-view-switcher {
  display: flex;
  justify-content: center;
  margin-bottom: 3rem;
}

.view-switcher-container {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 8px;
  backdrop-filter: blur(20px);
  display: flex;
  gap: 4px;
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
}

.switcher-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
  pointer-events: none;
}

.view-switcher-btn {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 16px;
  background: transparent;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  overflow: hidden;
  z-index: 2;
}

.view-switcher-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0);
  border-radius: 16px;
  transition: all 0.3s ease;
  z-index: -1;
}

.view-switcher-btn:hover::before {
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.view-switcher-btn:hover {
  color: #475569;
  transform: translateY(-1px);
}

.view-switcher-btn.active {
  color: white;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
  box-shadow: 
    0 4px 20px rgba(59, 130, 246, 0.25),
    0 1px 0 rgba(255, 255, 255, 0.2) inset;
  transform: translateY(-2px) scale(1.02);
}

.view-switcher-btn.active::before {
  background: transparent;
}

.btn-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.view-switcher-btn:hover .btn-icon-wrapper {
  background: rgba(59, 130, 246, 0.1);
}

.view-switcher-btn.active .btn-icon-wrapper {
  background: rgba(255, 255, 255, 0.15);
}

.btn-icon-wrapper::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.2) 50%, transparent 70%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.view-switcher-btn.active:hover .btn-icon-wrapper::before {
  transform: rotate(45deg) translateX(100%);
}

.btn-label {
  font-weight: 600;
  letter-spacing: -0.025em;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.view-switcher-btn:hover .btn-label {
  transform: translateX(1px);
}

.view-switcher-btn.active .btn-label {
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.btn-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at center, rgba(255, 255, 255, 0.2) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
  border-radius: 16px;
  pointer-events: none;
}

.view-switcher-btn.active .btn-glow {
  opacity: 1;
}

/* ===== 现代化标签云样式 ===== */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  align-items: center;
  line-height: 1.6;
  padding: 2rem;
}

.tag-cloud-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 30px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 600;
  text-decoration: none;
  backdrop-filter: blur(16px);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  position: relative;
  overflow: hidden;
}

.tag-cloud-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.5s ease;
}

.tag-cloud-item:hover::before {
  left: 100%;
}

.tag-cloud-item:hover {
  background: rgba(255, 255, 255, 0.95);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-4px) scale(1.05);
  box-shadow: 
    0 8px 30px rgba(59, 130, 246, 0.1),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
}

.tag-cloud-xs {
  font-size: 0.8rem;
  background: linear-gradient(135deg, #64748b, #94a3b8);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.tag-cloud-sm {
  font-size: 0.9rem;
  background: linear-gradient(135deg, #475569, #64748b);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.tag-cloud-md {
  font-size: 1rem;
  background: linear-gradient(135deg, #334155, #475569);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 600;
}

.tag-cloud-lg {
  font-size: 1.125rem;
  background: linear-gradient(135deg, #1e293b, #334155);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
}

.tag-cloud-xl {
  font-size: 1.3rem;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
}

.tag-count {
  font-size: 0.75rem;
  opacity: 0.8;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: 4px;
  font-weight: 600;
}

/* ===== 现代化卡片网格样式 ===== */
.modern-tag-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  padding: 28px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
}

.modern-tag-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4, #10b981);
  transform: scaleX(0);
  transition: transform 0.5s ease;
  transform-origin: left;
  border-radius: 24px 24px 0 0;
}

.modern-tag-card::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  transform: scale(0);
  transition: transform 0.6s ease;
  pointer-events: none;
}

.modern-tag-card:hover::before {
  transform: scaleX(1);
}

.modern-tag-card:hover::after {
  transform: scale(1);
}

.modern-tag-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 25px 50px rgba(139, 92, 246, 0.08),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.95);
}

.tag-card-button {
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tag-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.2);
  position: relative;
  overflow: hidden;
}

.tag-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.2) 50%, transparent 70%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.modern-tag-card:hover .tag-icon {
  transform: rotate(-12deg) scale(1.15);
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #0891b2 100%);
  box-shadow: 0 8px 30px rgba(139, 92, 246, 0.3);
}

.modern-tag-card:hover .tag-icon::before {
  transform: rotate(45deg) translateX(100%);
}

.article-count {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(6, 182, 212, 0.05));
  color: #8b5cf6;
  border: 1px solid rgba(139, 92, 246, 0.15);
  padding: 6px 16px;
  border-radius: 24px;
  font-size: 0.8rem;
  font-weight: 700;
  transition: all 0.4s ease;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 12px rgba(139, 92, 246, 0.08);
}

.modern-tag-card:hover .article-count {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(6, 182, 212, 0.1));
  border-color: rgba(139, 92, 246, 0.25);
  transform: scale(1.08);
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15);
}

.card-content {
  margin-bottom: 20px;
}

.tag-title {
  font-size: 1.3rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 10px;
  line-height: 1.3;
  transition: all 0.4s ease;
  letter-spacing: -0.025em;
}

.modern-tag-card:hover .tag-title {
  background: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  transform: translateX(2px);
}

.tag-description {
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
}

.explore-text {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  transition: all 0.4s ease;
}

.modern-tag-card:hover .explore-text {
  background: linear-gradient(135deg, #8b5cf6, #06b6d4);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.arrow-icon {
  color: #94a3b8;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateX(0);
  padding: 8px;
  border-radius: 12px;
  background: rgba(148, 163, 184, 0.1);
}

.modern-tag-card:hover .arrow-icon {
  background: linear-gradient(135deg, #8b5cf6, #06b6d4);
  color: white;
  transform: translateX(6px) scale(1.1);
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.2);
}

/* ===== 现代化列表视图样式 ===== */
.modern-list-container {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 28px;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  overflow: hidden;
}

.list-header {
  padding: 2rem;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(139, 92, 246, 0.02));
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  position: relative;
}

.list-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.2), transparent);
}

.list-title {
  font-size: 1.25rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
  letter-spacing: -0.025em;
}

.list-subtitle {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 500;
  margin: 8px 0 0 0;
}

.tag-list-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.2);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.tag-list-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.tag-list-item:hover .tag-list-icon {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(139, 92, 246, 0.3);
}

.tag-list-item:hover .tag-list-icon::before {
  transform: rotate(45deg) translateX(100%);
}

.tag-list-item {
  padding: 1.5rem 2rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border-bottom: 1px solid rgba(226, 232, 240, 0.3);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.tag-list-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  transform: scaleY(0);
  transition: transform 0.3s ease;
}

.tag-list-item:hover::before {
  transform: scaleY(1);
}

.tag-list-item:hover {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
  transform: translateX(8px);
  border-color: rgba(59, 130, 246, 0.1);
}

.tag-list-item:last-child {
  border-bottom: none;
}

.tag-list-item .font-medium {
  font-weight: 700;
  font-size: 1rem;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  transition: all 0.3s ease;
}

.tag-list-item:hover .font-medium {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  transform: translateX(2px);
}

.tag-list-item .text-sm {
  color: #64748b;
  font-weight: 500;
  line-height: 1.5;
}

.tag-list-item .text-sm:last-child {
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  padding: 4px 12px;
  border-radius: 16px;
  font-weight: 600;
  margin-left: 1rem;
  transition: all 0.3s ease;
}

.tag-list-item:hover .text-sm:last-child {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
  transform: scale(1.05);
}

.tag-list-item .el-icon:last-child {
  transition: all 0.3s ease;
  padding: 8px;
  border-radius: 10px;
  background: rgba(148, 163, 184, 0.1);
}

.tag-list-item:hover .el-icon:last-child {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  transform: translateX(4px) scale(1.1);
}

/* ===== 响应式设计 ===== */
@media (max-width: 768px) {
  .modern-stats-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
    margin-bottom: 2rem;
  }
  
  .stat-card {
    padding: 1.5rem;
    gap: 1rem;
  }
  
  .stat-icon-wrapper {
    width: 48px;
    height: 48px;
  }
  
  .stat-number {
    font-size: 2rem;
  }
  
  .modern-tag-card {
    padding: 20px;
    border-radius: 16px;
  }
  
  .tag-icon {
    width: 36px;
    height: 36px;
  }
  
  .tag-title {
    font-size: 1.125rem;
  }
  
  .tag-cloud {
    gap: 8px;
  }
  
  .tag-cloud-item {
    padding: 6px 12px;
    font-size: 0.875rem;
  }
}

@media (max-width: 640px) {
  .tags-page {
    padding: 1rem;
  }
  
  .modern-stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
  
  .stat-card {
    padding: 1rem;
    flex-direction: column;
    text-align: center;
    gap: 0.75rem;
  }
  
  .stat-icon-wrapper {
    width: 40px;
    height: 40px;
  }
  
  .stat-number {
    font-size: 1.75rem;
  }
  
  .stat-label {
    font-size: 0.75rem;
  }
  
  .view-switcher-container {
    padding: 6px;
    border-radius: 16px;
  }
  
  .view-switcher-btn {
    padding: 8px 12px;
    font-size: 0.75rem;
    gap: 6px;
  }
  
  .btn-icon-wrapper {
    width: 20px;
    height: 20px;
  }
  
  .modern-tag-card {
    padding: 16px;
  }
  
  .card-header {
    margin-bottom: 12px;
  }
  
  .card-content {
    margin-bottom: 16px;
  }
}
</style>