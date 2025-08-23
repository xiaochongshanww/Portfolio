<template>
  <div class="archive-page">
    <div class="max-w-4xl mx-auto py-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-4">文章归档</h1>
        <p class="text-gray-600 max-w-2xl mx-auto">
          按时间浏览博客的所有文章，回顾写作历程
        </p>
      </div>

      <!-- 现代化统计信息 -->
      <div class="stats-grid">
        <div class="modern-stat-card stat-card-1">
          <div class="stat-icon">
            <el-icon size="24"><DocumentCopy /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ totalArticles }}</div>
            <div class="stat-label">总文章数</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        <div class="modern-stat-card stat-card-2">
          <div class="stat-icon">
            <el-icon size="24"><Calendar /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ totalMonths }}</div>
            <div class="stat-label">活跃月份</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        <div class="modern-stat-card stat-card-3">
          <div class="stat-icon">
            <el-icon size="24"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ currentYear }}</div>
            <div class="stat-label">当前年份</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        <div class="modern-stat-card stat-card-4">
          <div class="stat-icon">
            <el-icon size="24"><Refresh /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ latestMonth }}</div>
            <div class="stat-label">最新更新</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
      </div>

      <!-- 现代化年份筛选 -->
      <div class="year-filter-container">
        <div class="year-filter-wrapper">
          <div class="filter-header">
            <el-icon class="filter-icon"><Filter /></el-icon>
            <span class="filter-title">筛选年份</span>
          </div>
          <div class="year-buttons-group">
            <button 
              v-for="year in availableYears" 
              :key="year"
              @click="selectedYear = year"
              :class="[
                'year-filter-btn',
                selectedYear === year ? 'year-filter-btn-active' : 'year-filter-btn-default'
              ]"
            >
              <span class="year-text">{{ year }}</span>
              <div v-if="selectedYear === year" class="active-indicator"></div>
            </button>
            <button 
              @click="selectedYear = null"
              :class="[
                'year-filter-btn all-years-btn',
                selectedYear === null ? 'year-filter-btn-active' : 'year-filter-btn-default'
              ]"
            >
              <span class="year-text">全部</span>
              <div v-if="selectedYear === null" class="active-indicator"></div>
            </button>
          </div>
        </div>
      </div>

      <!-- 时间轴 -->
      <div class="timeline-container">
        <div v-for="(yearData, year) in filteredArchive" :key="year" class="year-section">
          <!-- 年份标题 -->
          <div class="year-header">
            <div class="year-marker">
              <div class="year-dot"></div>
              <div class="year-line"></div>
            </div>
            <div class="year-title">
              <h2 class="text-2xl font-bold text-gray-900">{{ year }}年</h2>
              <p class="text-sm text-gray-600">{{ yearData.totalCount }} 篇文章</p>
            </div>
          </div>

          <!-- 月份列表 -->
          <div class="months-container">
            <div v-for="(monthData, month) in yearData.months" :key="month" class="month-section">
              <!-- 月份标题 -->
              <div class="month-header">
                <div class="month-marker">
                  <div class="month-dot"></div>
                </div>
                <div class="month-title">
                  <h3 class="text-lg font-semibold text-gray-800">{{ formatMonth(month) }}</h3>
                  <span class="text-xs text-gray-500">{{ monthData.articles.length }} 篇</span>
                </div>
              </div>

              <!-- 文章列表 -->
              <div class="articles-list">
                <article 
                  v-for="article in monthData.articles" 
                  :key="article.id"
                  @click="goToArticle(article.slug)"
                  class="article-item group"
                >
                  <div class="article-content">
                    <div class="article-date">
                      {{ formatDate(article.published_at || article.created_at) }}
                    </div>
                    <h4 class="article-title">
                      {{ article.title }}
                    </h4>
                    <p class="article-summary">
                      {{ article.summary || '暂无摘要' }}
                    </p>
                    <div class="article-meta">
                      <span class="meta-item">
                        <el-icon><View /></el-icon>
                        {{ article.views_count || 0 }}
                      </span>
                      <span class="meta-item">
                        <el-icon><ChatRound /></el-icon>
                        {{ article.comments_count || 0 }}
                      </span>
                      <span v-if="article.category" class="meta-item category">
                        <el-icon><Folder /></el-icon>
                        {{ article.category.name }}
                      </span>
                    </div>
                  </div>
                  <div class="article-arrow">
                    <el-icon><ArrowRight /></el-icon>
                  </div>
                </article>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <el-icon class="animate-spin text-2xl text-blue-500 mr-3"><Loading /></el-icon>
        <span class="text-gray-600">加载归档数据中...</span>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && totalArticles === 0" class="text-center py-12">
        <el-icon class="text-6xl text-gray-300 mb-4"><Calendar /></el-icon>
        <h3 class="text-xl font-medium text-gray-900 mb-2">暂无文章</h3>
        <p class="text-gray-600">还没有发布任何文章，快去创建第一篇吧！</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { View, ChatRound, Folder, ArrowRight, Loading, Calendar, DocumentCopy, Clock, Refresh, Filter } from '@element-plus/icons-vue';
import apiClient from '../apiClient';
import { setMeta } from '../composables/useMeta';

const router = useRouter();
const articles = ref([]);
const loading = ref(false);
const selectedYear = ref(null);

// 计算属性
const archive = computed(() => {
  const archiveData = {};
  
  articles.value.forEach(article => {
    const date = new Date(article.published_at || article.created_at);
    const year = date.getFullYear();
    const month = date.getMonth() + 1; // JavaScript月份从0开始
    
    if (!archiveData[year]) {
      archiveData[year] = {
        totalCount: 0,
        months: {}
      };
    }
    
    if (!archiveData[year].months[month]) {
      archiveData[year].months[month] = {
        articles: []
      };
    }
    
    archiveData[year].months[month].articles.push(article);
    archiveData[year].totalCount++;
  });
  
  // 排序：年份倒序，月份倒序，文章按日期倒序
  const sortedArchive = {};
  Object.keys(archiveData)
    .sort((a, b) => parseInt(b) - parseInt(a))
    .forEach(year => {
      sortedArchive[year] = {
        totalCount: archiveData[year].totalCount,
        months: {}
      };
      
      Object.keys(archiveData[year].months)
        .sort((a, b) => parseInt(b) - parseInt(a))
        .forEach(month => {
          const articles = archiveData[year].months[month].articles
            .sort((a, b) => new Date(b.published_at || b.created_at) - new Date(a.published_at || a.created_at));
          
          sortedArchive[year].months[month] = { articles };
        });
    });
  
  return sortedArchive;
});

const filteredArchive = computed(() => {
  if (selectedYear.value === null) {
    return archive.value;
  }
  
  const year = selectedYear.value.toString();
  return archive.value[year] ? { [year]: archive.value[year] } : {};
});

const availableYears = computed(() => {
  return Object.keys(archive.value).map(year => parseInt(year)).sort((a, b) => b - a);
});

const totalArticles = computed(() => {
  return articles.value.length;
});

const totalMonths = computed(() => {
  let monthCount = 0;
  Object.values(archive.value).forEach(yearData => {
    monthCount += Object.keys(yearData.months).length;
  });
  return monthCount;
});

const currentYear = computed(() => {
  return new Date().getFullYear();
});

const latestMonth = computed(() => {
  if (articles.value.length === 0) return '-';
  
  const latest = articles.value.reduce((latest, article) => {
    const articleDate = new Date(article.published_at || article.created_at);
    const latestDate = new Date(latest.published_at || latest.created_at);
    return articleDate > latestDate ? article : latest;
  });
  
  const date = new Date(latest.published_at || latest.created_at);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
});

// 方法
async function loadArchive() {
  loading.value = true;
  try {
    // 加载所有文章，按发布时间排序
    const response = await apiClient.get('/articles/public?sort=-published_at&limit=1000');
    articles.value = response.data.data?.list || [];
    
    // 设置SEO元数据
    setMeta({
      title: '文章归档 - 时间轴浏览',
      description: `浏览博客的文章归档，共有 ${totalArticles.value} 篇文章，涵盖 ${totalMonths.value} 个活跃月份`,
      url: window.location.href
    });
  } catch (error) {
    console.error('加载归档失败:', error);
  } finally {
    loading.value = false;
  }
}

function formatMonth(month) {
  const monthNames = [
    '一月', '二月', '三月', '四月', '五月', '六月',
    '七月', '八月', '九月', '十月', '十一月', '十二月'
  ];
  return monthNames[parseInt(month) - 1];
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function goToArticle(slug) {
  router.push(`/article/${slug}`);
}

onMounted(loadArchive);
</script>

<style scoped>
.archive-page {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #ffffff 100%);
  min-height: 100vh;
  padding: 2rem 1rem;
}

/* ===== 现代化年份筛选样式 ===== */
.year-filter-container {
  display: flex;
  justify-content: center;
  margin-bottom: 3rem;
}

.year-filter-wrapper {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 28px;
  padding: 1.5rem 2rem;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.year-filter-wrapper::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.6s ease;
  pointer-events: none;
}

.year-filter-wrapper:hover::before {
  opacity: 1;
}

.year-filter-wrapper:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 40px rgba(59, 130, 246, 0.08),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
  border-color: rgba(255, 255, 255, 0.5);
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  position: relative;
}

.filter-icon {
  width: 24px;
  height: 24px;
  padding: 6px;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
  transition: all 0.3s ease;
}

.year-filter-wrapper:hover .filter-icon {
  transform: scale(1.1) rotate(-5deg);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
}

.filter-title {
  font-size: 0.875rem;
  font-weight: 600;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 0.025em;
  transition: all 0.3s ease;
}

.year-buttons-group {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
}

.year-filter-btn {
  position: relative;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 18px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  overflow: hidden;
  letter-spacing: 0.025em;
}

.year-filter-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s ease;
}

.year-filter-btn:hover::before {
  left: 100%;
}

.year-filter-btn-default {
  background: rgba(248, 250, 252, 0.8);
  color: #64748b;
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
}

.year-filter-btn-default:hover {
  background: rgba(255, 255, 255, 0.95);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.2);
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.1);
}

.year-filter-btn-active {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 
    0 4px 16px rgba(59, 130, 246, 0.25),
    0 1px 0 rgba(255, 255, 255, 0.2) inset;
  transform: translateY(-1px);
}

.year-filter-btn-active:hover {
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  transform: translateY(-3px) scale(1.02);
  box-shadow: 
    0 8px 24px rgba(59, 130, 246, 0.3),
    0 2px 0 rgba(255, 255, 255, 0.3) inset;
}

.year-text {
  position: relative;
  z-index: 2;
  transition: all 0.3s ease;
}

.active-indicator {
  position: absolute;
  bottom: 4px;
  left: 50%;
  width: 20px;
  height: 2px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 2px;
  transform: translateX(-50%);
  animation: pulse-indicator 2s ease-in-out infinite;
}

@keyframes pulse-indicator {
  0%, 100% { opacity: 0.8; transform: translateX(-50%) scaleX(1); }
  50% { opacity: 1; transform: translateX(-50%) scaleX(1.2); }
}

.all-years-btn {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.05)) !important;
  border-color: rgba(16, 185, 129, 0.2) !important;
}

.all-years-btn.year-filter-btn-default {
  color: #059669;
}

.all-years-btn.year-filter-btn-default:hover {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 182, 212, 0.1)) !important;
  color: #047857;
  border-color: rgba(16, 185, 129, 0.3) !important;
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.1);
}

.all-years-btn.year-filter-btn-active {
  background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%) !important;
  box-shadow: 
    0 4px 16px rgba(16, 185, 129, 0.25),
    0 1px 0 rgba(255, 255, 255, 0.2) inset;
}

.all-years-btn.year-filter-btn-active:hover {
  background: linear-gradient(135deg, #059669 0%, #0891b2 100%) !important;
  box-shadow: 
    0 8px 24px rgba(16, 185, 129, 0.3),
    0 2px 0 rgba(255, 255, 255, 0.3) inset;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .year-filter-wrapper {
    padding: 1.25rem 1.5rem;
    border-radius: 24px;
  }
  
  .year-filter-btn {
    padding: 0.625rem 1.25rem;
    font-size: 0.8rem;
    min-width: 60px;
  }
  
  .filter-header {
    margin-bottom: 1rem;
  }
}

@media (max-width: 640px) {
  .year-filter-wrapper {
    padding: 1rem;
    border-radius: 20px;
  }
  
  .year-buttons-group {
    gap: 0.375rem;
  }
  
  .year-filter-btn {
    padding: 0.5rem 1rem;
    border-radius: 14px;
    min-width: 50px;
  }
  
  .filter-title {
    font-size: 0.8rem;
  }
}

/* ===== 现代化统计卡片样式 ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 3rem;
}

@media (min-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.modern-stat-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  padding: 2rem 1.5rem;
  text-align: center;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.modern-stat-card::before {
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

.modern-stat-card:hover::before {
  transform: scale(1);
}

.modern-stat-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.08),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.95);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  color: white;
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
}

.stat-icon::before {
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

.modern-stat-card:hover .stat-icon::before {
  transform: rotate(45deg) translateX(100%);
}

.modern-stat-card:hover .stat-icon {
  transform: scale(1.1) rotate(-5deg);
}

/* 不同卡片的主题色彩 */
.stat-card-1 .stat-icon {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
}

.stat-card-1:hover .stat-icon {
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.4);
}

.stat-card-2 .stat-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);
}

.stat-card-2:hover .stat-icon {
  box-shadow: 0 8px 30px rgba(16, 185, 129, 0.4);
}

.stat-card-3 .stat-icon {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
}

.stat-card-3:hover .stat-icon {
  box-shadow: 0 8px 30px rgba(139, 92, 246, 0.4);
}

.stat-card-4 .stat-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
}

.stat-card-4:hover .stat-icon {
  box-shadow: 0 8px 30px rgba(245, 158, 11, 0.4);
}

.stat-content {
  position: relative;
  z-index: 2;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  line-height: 1;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  transition: all 0.4s ease;
  letter-spacing: -0.05em;
}

.modern-stat-card:hover .stat-number {
  transform: scale(1.05);
}

/* 不同卡片数字的主题色彩 */
.stat-card-1:hover .stat-number {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-card-2:hover .stat-number {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-card-3:hover .stat-number {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-card-4:hover .stat-number {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: color 0.3s ease;
}

.modern-stat-card:hover .stat-label {
  color: #334155;
}

.stat-decoration {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  opacity: 0.1;
  transition: all 0.4s ease;
}

.stat-card-1 .stat-decoration {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
}

.stat-card-2 .stat-decoration {
  background: linear-gradient(135deg, #10b981, #059669);
}

.stat-card-3 .stat-decoration {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

.stat-card-4 .stat-decoration {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.modern-stat-card:hover .stat-decoration {
  opacity: 0.2;
  transform: scale(1.2) rotate(15deg);
}

/* 响应式优化 */
@media (max-width: 640px) {
  .modern-stat-card {
    padding: 1.5rem 1rem;
  }
  
  .stat-icon {
    width: 48px;
    height: 48px;
    margin-bottom: 1rem;
  }
  
  .stat-number {
    font-size: 2rem;
  }
  
  .stat-decoration {
    width: 30px;
    height: 30px;
  }
}

/* ===== 现代化时间轴样式 ===== */
.timeline-container {
  position: relative;
  margin-top: 2rem;
}

.year-section {
  position: relative;
  margin-bottom: 4rem;
}

.year-header {
  display: flex;
  align-items: center;
  margin-bottom: 2.5rem;
  position: relative;
  padding: 1.5rem 2rem;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.year-header:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 40px rgba(59, 130, 246, 0.08),
    0 1px 0 rgba(255, 255, 255, 0.6) inset;
  background: rgba(255, 255, 255, 0.8);
}

.year-marker {
  position: relative;
  margin-right: 1.5rem;
}

.year-dot {
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border: 3px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  box-shadow: 
    0 0 0 4px rgba(59, 130, 246, 0.15),
    0 4px 12px rgba(59, 130, 246, 0.3);
  position: relative;
  z-index: 2;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15), 0 4px 12px rgba(59, 130, 246, 0.3); }
  50% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.1), 0 4px 16px rgba(59, 130, 246, 0.2); }
}

.year-line {
  position: absolute;
  left: 50%;
  top: 20px;
  width: 3px;
  height: calc(100vh - 180px);
  background: linear-gradient(
    to bottom, 
    rgba(59, 130, 246, 0.4) 0%, 
    rgba(139, 92, 246, 0.3) 50%, 
    rgba(6, 182, 212, 0.2) 80%,
    transparent 100%
  );
  border-radius: 2px;
  transform: translateX(-50%);
  z-index: 1;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.1);
}

.year-title h2 {
  margin: 0;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 50%, #8b5cf6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.025em;
}

.year-title p {
  color: #64748b;
  font-weight: 500;
  background: rgba(59, 130, 246, 0.08);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.875rem;
}

.months-container {
  margin-left: 2rem;
  position: relative;
}

.month-section {
  margin-bottom: 2.5rem;
  position: relative;
}

.month-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 1rem 1.5rem;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.month-header:hover {
  background: rgba(255, 255, 255, 0.8);
  transform: translateX(4px);
  box-shadow: 0 6px 25px rgba(6, 182, 212, 0.06);
}

.month-marker {
  margin-right: 1rem;
}

.month-dot {
  width: 14px;
  height: 14px;
  background: linear-gradient(135deg, #06b6d4 0%, #8b5cf6 100%);
  border: 2px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  box-shadow: 
    0 0 0 3px rgba(6, 182, 212, 0.15),
    0 2px 8px rgba(6, 182, 212, 0.2);
  transition: all 0.3s ease;
}

.month-header:hover .month-dot {
  transform: scale(1.1);
  box-shadow: 
    0 0 0 5px rgba(6, 182, 212, 0.1),
    0 4px 12px rgba(6, 182, 212, 0.3);
}

.month-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.month-title h3 {
  background: linear-gradient(135deg, #0f172a 0%, #06b6d4 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
}

.month-title span {
  background: rgba(6, 182, 212, 0.1);
  color: #06b6d4;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 600;
}

.articles-list {
  margin-left: 1.5rem;
  space-y: 1rem;
}

.article-item {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 2rem;
  margin-bottom: 1.25rem;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(16px);
  display: flex;
  align-items: center;
  justify-content: between;
  box-shadow: 
    0 4px 24px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.5) inset;
  position: relative;
  overflow: hidden;
}

.article-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #3b82f6, #06b6d4, #8b5cf6);
  transform: scaleX(0);
  transition: transform 0.4s ease;
  transform-origin: left;
}

.article-item:hover::before {
  transform: scaleX(1);
}

.article-item:hover {
  transform: translateY(-4px) translateX(2px);
  box-shadow: 
    0 12px 40px rgba(59, 130, 246, 0.08),
    0 2px 0 rgba(255, 255, 255, 0.7) inset;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.95);
}

.article-content {
  flex: 1;
}

.article-date {
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
  color: #3b82f6;
  padding: 6px 14px;
  border-radius: 16px;
  display: inline-block;
  border: 1px solid rgba(59, 130, 246, 0.15);
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08);
  transition: all 0.3s ease;
}

.article-item:hover .article-date {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.1));
  border-color: rgba(59, 130, 246, 0.25);
  transform: scale(1.05);
}

.article-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
  line-height: 1.4;
  transition: color 0.3s ease;
}

.article-item:hover .article-title {
  color: #3b82f6;
}

.article-summary {
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.5;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-meta {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #9ca3af;
  transition: color 0.3s ease;
}

.meta-item.category {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(6, 182, 212, 0.05));
  color: #8b5cf6;
  padding: 4px 12px;
  border-radius: 12px;
  border: 1px solid rgba(139, 92, 246, 0.15);
  backdrop-filter: blur(4px);
  font-weight: 600;
  transition: all 0.3s ease;
}

.article-item:hover .meta-item.category {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(6, 182, 212, 0.1));
  border-color: rgba(139, 92, 246, 0.25);
  transform: scale(1.05);
}

.article-item:hover .meta-item {
  color: #6b7280;
}

.article-arrow {
  color: #d1d5db;
  transition: all 0.3s ease;
  transform: translateX(0);
  margin-left: 1rem;
}

.article-item:hover .article-arrow {
  color: #3b82f6;
  transform: translateX(4px);
}

/* ===== 响应式设计 ===== */
@media (max-width: 768px) {
  .timeline-container {
    margin-left: -1rem;
  }
  
  .year-header {
    margin-left: 1rem;
  }
  
  .months-container {
    margin-left: 1rem;
  }
  
  .articles-list {
    margin-left: 0.5rem;
  }
  
  .article-item {
    padding: 1rem;
    flex-direction: column;
    align-items: flex-start;
  }
  
  .article-arrow {
    align-self: flex-end;
    margin-left: 0;
    margin-top: 0.5rem;
  }
  
  .article-meta {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
}

@media (max-width: 640px) {
  .archive-page {
    padding: 1rem;
  }
  
  .article-item {
    border-radius: 12px;
  }
  
  .year-line {
    height: calc(100vh - 150px);
  }
}
</style>