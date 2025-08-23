<template>
  <div class="modern-metrics-dashboard">
    <!-- 现代化页面头部 -->
    <div class="dashboard-header">
      <div class="header-content">
        <div class="header-icon">
          <el-icon size="40"><TrendCharts /></el-icon>
        </div>
        <div class="header-text">
          <h1 class="dashboard-title">站点数据看板</h1>
          <p class="dashboard-subtitle">实时监控站点各项指标和运行状态</p>
        </div>
      </div>
      <div class="refresh-button">
        <el-button 
          @click="fetchStats" 
          :loading="loading" 
          type="primary" 
          :icon="Refresh"
          circle
          size="large"
        />
      </div>
    </div>
    <!-- 现代化加载状态 -->
    <div v-if="loading" class="modern-loading">
      <div class="loading-grid">
        <div v-for="n in 4" :key="n" class="loading-card">
          <div class="loading-header"></div>
          <div class="loading-content">
            <div v-for="i in 3" :key="i" class="loading-stat"></div>
          </div>
        </div>
      </div>
    </div>
    <!-- 现代化错误状态 -->
    <div v-else-if="error" class="modern-error">
      <div class="error-card">
        <div class="error-icon">
          <el-icon size="48"><Warning /></el-icon>
        </div>
        <h3 class="error-title">加载数据失败</h3>
        <p class="error-message">{{ error }}</p>
        <el-button @click="fetchStats" type="primary" :icon="Refresh">
          重新加载
        </el-button>
      </div>
    </div>
    <!-- 现代化统计网格 -->
    <div v-else class="modern-stats-grid">
      <!-- 文章统计卡片 -->
      <div class="modern-stat-card article-stats">
        <div class="card-header">
          <div class="header-icon">
            <el-icon size="24"><Document /></el-icon>
          </div>
          <div class="header-text">
            <h3 class="card-title">文章统计</h3>
            <span class="card-subtitle">内容管理数据</span>
          </div>
        </div>
        <div class="stats-container">
          <div class="stat-item primary">
            <div class="stat-icon">
              <el-icon size="20"><Collection /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.articles.total }}</div>
              <div class="stat-label">总数</div>
            </div>
          </div>
          <div class="stat-item success">
            <div class="stat-icon">
              <el-icon size="20"><Select /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.articles.published }}</div>
              <div class="stat-label">已发布</div>
            </div>
          </div>
          <div class="stat-item info">
            <div class="stat-icon">
              <el-icon size="20"><Edit /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.articles.draft }}</div>
              <div class="stat-label">草稿</div>
            </div>
          </div>
          <div class="stat-item warning">
            <div class="stat-icon">
              <el-icon size="20"><Clock /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.articles.pending }}</div>
              <div class="stat-label">待审核</div>
            </div>
            <div v-if="stats.articles.pending > 0" class="stat-alert">
              <el-icon size="14"><Warning /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 评论统计卡片 -->
      <div class="modern-stat-card comment-stats">
        <div class="card-header">
          <div class="header-icon">
            <el-icon size="24"><ChatDotRound /></el-icon>
          </div>
          <div class="header-text">
            <h3 class="card-title">评论统计</h3>
            <span class="card-subtitle">互动反馈数据</span>
          </div>
        </div>
        <div class="stats-container">
          <div class="stat-item primary">
            <div class="stat-icon">
              <el-icon size="20"><ChatRound /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.comments.total }}</div>
              <div class="stat-label">总数</div>
            </div>
          </div>
          <div class="stat-item success">
            <div class="stat-icon">
              <el-icon size="20"><CircleCheck /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.comments.approved }}</div>
              <div class="stat-label">已批准</div>
            </div>
          </div>
          <div class="stat-item warning">
            <div class="stat-icon">
              <el-icon size="20"><Clock /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.comments.pending }}</div>
              <div class="stat-label">待审核</div>
            </div>
            <div v-if="stats.comments.pending > 0" class="stat-alert">
              <el-icon size="14"><Warning /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 用户统计卡片 -->
      <div class="modern-stat-card user-stats">
        <div class="card-header">
          <div class="header-icon">
            <el-icon size="24"><User /></el-icon>
          </div>
          <div class="header-text">
            <h3 class="card-title">用户统计</h3>
            <span class="card-subtitle">社区成员数据</span>
          </div>
        </div>
        <div class="stats-container single-stat">
          <div class="stat-item primary large">
            <div class="stat-icon">
              <el-icon size="24"><UserFilled /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.users.total }}</div>
              <div class="stat-label">总用户数</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分类与标签统计卡片 -->
      <div class="modern-stat-card taxonomy-stats">
        <div class="card-header">
          <div class="header-icon">
            <el-icon size="24"><Files /></el-icon>
          </div>
          <div class="header-text">
            <h3 class="card-title">分类与标签</h3>
            <span class="card-subtitle">内容组织结构</span>
          </div>
        </div>
        <div class="stats-container">
          <div class="stat-item info">
            <div class="stat-icon">
              <el-icon size="20"><Folder /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.taxonomy.categories }}</div>
              <div class="stat-label">分类总数</div>
            </div>
          </div>
          <div class="stat-item purple">
            <div class="stat-icon">
              <el-icon size="20"><PriceTag /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-number">{{ stats.taxonomy.tags }}</div>
              <div class="stat-label">标签总数</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage, ElButton, ElIcon } from 'element-plus';
import { 
  Warning, TrendCharts, Refresh, Document, Collection, Select, Edit, Clock,
  ChatDotRound, ChatRound, CircleCheck, User, UserFilled, Files, Folder, PriceTag
} from '@element-plus/icons-vue';
import apiClient from '../apiClient';
import { setMeta } from '../composables/useMeta';

const loading = ref(true);
const error = ref(null);
const stats = ref({
  articles: { total: 0, published: 0, draft: 0, pending: 0 },
  comments: { total: 0, pending: 0, approved: 0 },
  users: { total: 0 },
  taxonomy: { tags: 0, categories: 0 },
});

const api = {
  getSummary: () => apiClient.get('/metrics/summary'),
};

const fetchStats = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.getSummary();
    stats.value = response.data.data;
  } catch (err) {
    error.value = err.response?.data?.message || '无法连接到服务器';
    ElMessage.error('加载统计数据失败');
    console.error(err);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  setMeta({ 
    title: '站点数据看板', 
    description: '实时监控站点各项指标和运行状态' 
  });
  fetchStats();
});
</script>

<style scoped>
/* ===== 现代化数据看板样式 ===== */
.modern-metrics-dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem 1rem;
  background: 
    radial-gradient(circle at 20% 50%, rgba(59, 130, 246, 0.04) 0%, transparent 40%),
    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.04) 0%, transparent 40%),
    radial-gradient(circle at 40% 80%, rgba(16, 185, 129, 0.04) 0%, transparent 40%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 30%, #ffffff 70%, #fafbfe 100%);
  min-height: 100vh;
  position: relative;
}

/* 现代化页面头部 */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3rem;
  padding: 2.5rem;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.dashboard-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #10b981, #f59e0b);
  opacity: 0.6;
}

.dashboard-header:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 40px rgba(59, 130, 246, 0.08),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.header-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
  transition: all 0.3s ease;
}

.dashboard-header:hover .header-icon {
  transform: scale(1.05) rotate(-2deg);
  box-shadow: 0 12px 40px rgba(59, 130, 246, 0.4);
}

.dashboard-title {
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 50%, #8b5cf6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 0.5rem 0;
  letter-spacing: -0.05em;
}

.dashboard-subtitle {
  color: #64748b;
  font-size: 1rem;
  margin: 0;
  font-weight: 500;
  max-width: 400px;
}

.refresh-button {
  background: rgba(59, 130, 246, 0.1);
  border-radius: 50%;
  padding: 0.5rem;
  transition: all 0.3s ease;
}

.refresh-button:hover {
  background: rgba(59, 130, 246, 0.15);
  transform: scale(1.05);
}

/* 现代化统计网格 */
.modern-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.modern-stat-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2rem;
  padding: 2rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
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

.modern-stat-card:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: 
    0 20px 40px rgba(59, 130, 246, 0.06),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
}

.modern-stat-card:hover::before {
  transform: scale(1);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.article-stats .header-icon {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

.comment-stats .header-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.user-stats .header-icon {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
}

.taxonomy-stats .header-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.modern-stat-card:hover .header-icon {
  transform: scale(1.1) rotate(-5deg);
}

.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
  letter-spacing: -0.025em;
}

.card-subtitle {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
  margin: 0;
}

/* 统计容器 */
.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1.5rem;
}

.stats-container.single-stat {
  grid-template-columns: 1fr;
  justify-items: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 1rem;
  transition: all 0.3s ease;
  position: relative;
  backdrop-filter: blur(8px);
}

.stat-item.large {
  padding: 2rem;
  gap: 1.5rem;
}

.stat-item:hover {
  transform: translateY(-2px) scale(1.02);
}

/* 统计项主题色彩 */
.stat-item.primary {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.15);
}

.stat-item.success {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.stat-item.info {
  background: rgba(6, 182, 212, 0.08);
  border: 1px solid rgba(6, 182, 212, 0.15);
}

.stat-item.warning {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.stat-item.purple {
  background: rgba(139, 92, 246, 0.08);
  border: 1px solid rgba(139, 92, 246, 0.15);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-item.primary .stat-icon {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
}

.stat-item.success .stat-icon {
  background: linear-gradient(135deg, #10b981, #059669);
}

.stat-item.info .stat-icon {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
}

.stat-item.warning .stat-icon {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.stat-item.purple .stat-icon {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

.stat-item:hover .stat-icon {
  transform: scale(1.1) rotate(-5deg);
}

.stat-content {
  text-align: center;
}

.stat-number {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.5rem;
  letter-spacing: -0.025em;
}

.stat-item.large .stat-number {
  font-size: 3rem;
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-alert {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 24px;
  height: 24px;
  background: #f59e0b;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  animation: pulse-alert 2s infinite;
}

@keyframes pulse-alert {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

/* 加载状态 */
.modern-loading {
  margin-top: 2rem;
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 2rem;
}

.loading-card {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2rem;
  padding: 2rem;
  animation: loading-shimmer 1.5s ease-in-out infinite;
}

.loading-header {
  height: 24px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  animation: loading-shimmer 1.5s ease-in-out infinite;
}

.loading-content {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.loading-stat {
  height: 80px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 8px;
  animation: loading-shimmer 1.5s ease-in-out infinite;
}

@keyframes loading-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* 错误状态 */
.modern-error {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 4rem;
}

.error-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2rem;
  padding: 3rem;
  text-align: center;
  max-width: 400px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
}

.error-icon {
  color: #ef4444;
  margin-bottom: 1rem;
}

.error-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #374151;
  margin: 0 0 1rem 0;
}

.error-message {
  color: #6b7280;
  margin: 0 0 2rem 0;
  line-height: 1.5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .modern-metrics-dashboard {
    padding: 1rem;
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 1.5rem;
    text-align: center;
    padding: 2rem;
  }
  
  .dashboard-title {
    font-size: 2rem;
  }
  
  .modern-stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-container {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .loading-content {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .header-icon {
    width: 48px;
    height: 48px;
  }
  
  .dashboard-title {
    font-size: 1.75rem;
  }
  
  .modern-stat-card {
    padding: 1.5rem;
  }
  
  .stats-container {
    grid-template-columns: 1fr;
  }
  
  .loading-content {
    grid-template-columns: 1fr;
  }
}
</style>