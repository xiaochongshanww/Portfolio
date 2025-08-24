<template>
  <div class="article-review">
    <!-- 页面头部 -->
    <div class="modern-page-header">
      <div class="header-decoration"></div>
      <div class="header-pattern"></div>
      <div class="header-content">
        <div class="title-container">
          <div class="title-icon">
            <el-icon size="32"><View /></el-icon>
          </div>
          <div class="title-text">
            <h1 class="page-title">文章审核</h1>
            <p class="page-description">审核作者提交的文章，确保内容质量</p>
          </div>
        </div>
      </div>
      <div class="modern-stats">
        <div class="stat-card pending">
          <div class="stat-icon">
            <el-icon size="20"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.pending }}</span>
            <span class="stat-label">待审核</span>
          </div>
        </div>
        <div class="stat-card today">
          <div class="stat-icon">
            <el-icon size="20"><Check /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.todayReviewed }}</span>
            <span class="stat-label">今日审核</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速筛选 -->
    <div class="modern-filters">
      <div class="filter-container">
        <div class="filter-tabs">
          <button 
            :class="['filter-tab', { active: currentFilter === 'pending' }]"
            @click="setFilter('pending')"
          >
            <el-icon size="16"><Clock /></el-icon>
            <span>待审核</span>
            <span class="count">({{ stats.pending }})</span>
          </button>
          <button 
            :class="['filter-tab', { active: currentFilter === 'all_recent' }]"
            @click="setFilter('all_recent')"
          >
            <el-icon size="16"><Document /></el-icon>
            <span>最近文章</span>
          </button>
          <button 
            :class="['filter-tab', { active: currentFilter === 'my_reviewed' }]"
            @click="setFilter('my_reviewed')"
          >
            <el-icon size="16"><User /></el-icon>
            <span>我审核的</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 文章列表 -->
    <div class="review-list">
      <div v-if="loading" class="loading-state">
        <el-skeleton v-for="n in 3" :key="n" :rows="4" animated class="review-skeleton" />
      </div>
      
      <div v-else-if="!articles.length" class="empty-state">
        <el-empty description="没有需要审核的文章" />
      </div>
      
      <div v-else class="article-cards">
        <div 
          v-for="article in articles" 
          :key="article.id" 
          class="modern-review-card"
          :class="{ 'pending': article.status === 'pending' }"
        >
          <!-- 文章基本信息 -->
          <div class="modern-card-header">
            <div class="article-info">
              <h3 class="modern-article-title">{{ article.title }}</h3>
              <div class="modern-article-meta">
                <div class="meta-item author">
                  <el-icon size="16"><User /></el-icon>
                  <span>{{ article.author?.nickname || article.author?.email }}</span>
                </div>
                <div class="meta-item time">
                  <el-icon size="16"><Clock /></el-icon>
                  <span>{{ formatRelativeTime(article.created_at) }}</span>
                </div>
                <div v-if="article.category" class="meta-item category">
                  <el-icon size="16"><Collection /></el-icon>
                  <span>{{ article.category.name }}</span>
                </div>
              </div>
            </div>
            <div class="modern-status-badge">
              <div :class="['status-indicator', article.status]">
                <span class="status-text">{{ getStatusText(article.status) }}</span>
              </div>
            </div>
          </div>

          <!-- 文章摘要 -->
          <div v-if="article.summary" class="article-summary">
            {{ article.summary }}
          </div>

          <!-- 文章标签 -->
          <div v-if="article.tags && article.tags.length" class="article-tags">
            <el-tag 
              v-for="tag in article.tags.slice(0, 5)" 
              :key="tag" 
              size="small" 
              class="tag-item"
            >
              {{ tag }}
            </el-tag>
            <span v-if="article.tags.length > 5" class="more-tags">
              +{{ article.tags.length - 5 }}
            </span>
          </div>

          <!-- SEO信息 -->
          <div v-if="article.seo_title || article.seo_desc" class="seo-info">
            <div class="seo-title">SEO标题: {{ article.seo_title || '未设置' }}</div>
            <div class="seo-desc">SEO描述: {{ article.seo_desc || '未设置' }}</div>
          </div>

          <!-- 拒绝原因 -->
          <div v-if="article.status === 'rejected' && article.reject_reason" class="reject-reason">
            <el-alert 
              :title="`拒绝原因: ${article.reject_reason}`" 
              type="error" 
              :closable="false"
            />
          </div>

          <!-- 操作按钮 -->
          <div class="modern-card-actions">
            <div class="action-left">
              <button @click="previewArticle(article)" class="action-btn preview">
                <el-icon size="16"><View /></el-icon>
                <span>预览</span>
              </button>
              <button @click="viewHistory(article)" class="action-btn history">
                <el-icon size="16"><Clock /></el-icon>
                <span>历史版本</span>
              </button>
              <RouterLink :to="`/article/${article.slug}`" target="_blank" class="action-link">
                <button class="action-btn link">
                  <el-icon size="16"><Link /></el-icon>
                  <span>查看页面</span>
                </button>
              </RouterLink>
            </div>
            
            <div v-if="article.status === 'pending'" class="action-right">
              <button 
                @click="showRejectDialog(article)" 
                class="action-btn reject"
              >
                <el-icon size="16"><Close /></el-icon>
                <span>拒绝</span>
              </button>
              <button 
                @click="approveArticle(article)" 
                class="action-btn approve"
              >
                <el-icon size="16"><Check /></el-icon>
                <span>通过</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="meta.total > 0" class="modern-pagination-wrapper">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        @current-change="handlePageChange"
        class="modern-pagination-component"
      />
    </div>

    <!-- 预览对话框 -->
    <el-dialog 
      v-model="previewDialog.visible" 
      :title="previewDialog.article?.title" 
      width="80%"
      top="5vh"
    >
      <div v-if="previewDialog.article" class="preview-content">
        <div class="preview-meta">
          <div><strong>作者:</strong> {{ previewDialog.article.author?.nickname || previewDialog.article.author?.email }}</div>
          <div><strong>分类:</strong> {{ previewDialog.article.category?.name || '无' }}</div>
          <div><strong>标签:</strong> {{ previewDialog.article.tags?.join(', ') || '无' }}</div>
          <div><strong>创建时间:</strong> {{ formatDate(previewDialog.article.created_at) }}</div>
        </div>
        <div class="preview-body" v-html="previewDialog.article.content_html"></div>
      </div>
    </el-dialog>

    <!-- 拒绝原因对话框 -->
    <el-dialog 
      v-model="rejectDialog.visible" 
      title="拒绝文章" 
      width="500px"
    >
      <el-form :model="rejectDialog.form" label-width="80px">
        <el-form-item label="文章标题">
          <span>{{ rejectDialog.article?.title }}</span>
        </el-form-item>
        <el-form-item label="拒绝原因" required>
          <el-input
            v-model="rejectDialog.form.reason"
            type="textarea"
            :rows="4"
            placeholder="请详细说明拒绝的原因，帮助作者改进文章质量..."
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="建议修改">
          <el-input
            v-model="rejectDialog.form.suggestions"
            type="textarea"
            :rows="3"
            placeholder="可以提供一些改进建议（可选）"
            maxlength="300"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialog.visible = false">取消</el-button>
        <el-button 
          type="danger" 
          @click="confirmReject"
          :loading="rejectDialog.loading"
        >
          确认拒绝
        </el-button>
      </template>
    </el-dialog>

    <!-- 历史版本对话框 -->
    <el-dialog 
      v-model="historyDialog.visible" 
      title="历史版本" 
      width="60%"
    >
      <div v-loading="historyDialog.loading">
        <div v-if="historyDialog.versions.length === 0" class="empty-state">
          <el-empty description="暂无历史版本" />
        </div>
        <div v-else class="version-list">
          <div 
            v-for="version in historyDialog.versions" 
            :key="version.id" 
            class="version-item"
          >
            <div class="version-header">
              <span class="version-no">版本 {{ version.version_no }}</span>
              <span class="version-time">{{ formatDate(version.created_at) }}</span>
              <span class="version-editor">
                编辑者: {{ version.editor?.nickname || version.editor?.email }}
              </span>
            </div>
            <div class="version-actions">
              <el-button size="small" @click="previewVersion(version)">
                预览此版本
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { 
  User, Clock, Collection, View, Link, Close, Check, Document 
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';
import apiClient from '../../apiClient';

const userStore = useUserStore();

// 响应式数据
const loading = ref(false);
const articles = ref<any[]>([]);
const currentFilter = ref('pending');

// 统计数据
const stats = reactive({
  pending: 0,
  todayReviewed: 0
});

// 分页信息
const meta = reactive({
  total: 0,
  page: 1,
  page_size: 10
});

// 对话框状态
const previewDialog = reactive({
  visible: false,
  article: null as any
});

const rejectDialog = reactive({
  visible: false,
  loading: false,
  article: null as any,
  form: {
    reason: '',
    suggestions: ''
  }
});

const historyDialog = reactive({
  visible: false,
  loading: false,
  versions: [] as any[]
});

// 状态相关函数
function getStatusType(status: string): string {
  switch (status) {
    case 'published': return 'success';
    case 'pending': return 'warning';
    case 'draft': return 'info';
    case 'rejected': return 'danger';
    default: return '';
  }
}

function getStatusText(status: string): string {
  switch (status) {
    case 'published': return '已发布';
    case 'pending': return '待审核';
    case 'draft': return '草稿';
    case 'rejected': return '已拒绝';
    default: return status;
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (minutes < 60) {
    return `${minutes}分钟前`;
  } else if (hours < 24) {
    return `${hours}小时前`;
  } else if (days < 7) {
    return `${days}天前`;
  } else {
    return formatDate(dateStr);
  }
}

// 数据加载
async function loadArticles() {
  loading.value = true;
  
  try {
    const params: any = {
      page: meta.page,
      page_size: meta.page_size
    };

    // 根据筛选条件设置参数
    switch (currentFilter.value) {
      case 'pending':
        params.status = 'pending';
        break;
      case 'all_recent':
        // 加载最近的所有文章（不包括草稿）
        params.exclude_status = 'draft';
        break;
      case 'my_reviewed':
        // 加载我审核过的文章
        params.reviewer_id = userStore.user?.id;
        break;
    }

    const response = await apiClient.get('/articles/', { params });
    const data = response.data.data;
    
    articles.value = data?.list || [];
    meta.total = data?.total || 0;
    meta.page = data?.page || 1;
    meta.page_size = data?.page_size || 10;
  } catch (error) {
    console.error('加载文章列表失败:', error);
    ElMessage.error('加载文章列表失败');
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  try {
    // 加载待审核文章数量
    const pendingResponse = await apiClient.get('/articles/', { 
      params: { status: 'pending', page: 1, page_size: 1 }
    });
    stats.pending = pendingResponse.data.data?.total || 0;

    // 加载今日审核数量
    const today = new Date().toISOString().split('T')[0];
    const reviewedResponse = await apiClient.get('/articles/audit_logs', {
      params: { 
        action: 'approve,reject', 
        date: today,
        operator_id: userStore.user?.id,
        page: 1, 
        page_size: 1 
      }
    });
    stats.todayReviewed = reviewedResponse.data.data?.total || 0;
  } catch (error) {
    console.error('加载统计数据失败:', error);
  }
}

// 筛选器切换
function setFilter(filter: string) {
  currentFilter.value = filter;
  meta.page = 1;
  loadArticles();
}

// 分页处理
function handlePageChange(page: number) {
  meta.page = page;
  loadArticles();
}

// 预览文章
function previewArticle(article: any) {
  previewDialog.article = article;
  previewDialog.visible = true;
}

// 查看历史版本
async function viewHistory(article: any) {
  historyDialog.visible = true;
  historyDialog.loading = true;
  
  try {
    const response = await apiClient.get(`/articles/${article.id}/versions`);
    historyDialog.versions = response.data.data || [];
  } catch (error) {
    ElMessage.error('加载历史版本失败');
    historyDialog.versions = [];
  } finally {
    historyDialog.loading = false;
  }
}

async function previewVersion(version: any) {
  // 这里可以实现版本预览功能
  ElMessage.info('版本预览功能开发中');
}

// 审核操作
async function approveArticle(article: any) {
  try {
    await apiClient.post(`/articles/${article.id}/approve`);
    ElMessage.success('文章审核通过');
    loadArticles();
    loadStats();
  } catch (error) {
    ElMessage.error('审核失败');
  }
}

function showRejectDialog(article: any) {
  rejectDialog.article = article;
  rejectDialog.form.reason = '';
  rejectDialog.form.suggestions = '';
  rejectDialog.visible = true;
}

async function confirmReject() {
  if (!rejectDialog.form.reason.trim()) {
    ElMessage.warning('请输入拒绝原因');
    return;
  }

  rejectDialog.loading = true;
  
  try {
    const reason = rejectDialog.form.reason.trim();
    const suggestions = rejectDialog.form.suggestions.trim();
    const fullReason = suggestions ? `${reason}\n\n改进建议：${suggestions}` : reason;

    await apiClient.post(`/articles/${rejectDialog.article.id}/reject`, {
      reason: fullReason
    });
    
    ElMessage.success('文章已拒绝');
    rejectDialog.visible = false;
    loadArticles();
    loadStats();
  } catch (error) {
    ElMessage.error('操作失败');
  } finally {
    rejectDialog.loading = false;
  }
}

// 生命周期
onMounted(() => {
  loadArticles();
  loadStats();
});
</script>

<style scoped>
/* ===== 现代化文章审核样式 ===== */
.article-review {
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}

/* 页面头部 */
.modern-page-header {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 2rem;
  background: 
    linear-gradient(135deg, 
      rgba(34, 197, 94, 0.05) 0%, 
      rgba(59, 130, 246, 0.03) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  box-shadow: 
    0 4px 20px rgba(34, 197, 94, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-decoration {
  position: absolute;
  top: -50px;
  left: -50px;
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(59, 130, 246, 0.05));
  border-radius: 50%;
  filter: blur(30px);
  animation: float-decoration 8s ease-in-out infinite;
}

.header-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 2px 2px, rgba(34, 197, 94, 0.1) 1px, transparent 0);
  background-size: 30px 30px;
  opacity: 0.3;
  pointer-events: none;
}

@keyframes float-decoration {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(180deg); }
}

.header-content {
  flex: 1;
  position: relative;
  z-index: 2;
}

.title-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 25px rgba(34, 197, 94, 0.3);
  position: relative;
  overflow: hidden;
}

.title-icon::before {
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

.title-icon:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.title-text {
  flex: 1;
}

.page-title {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #22c55e 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
}

.page-description {
  margin: 0;
  color: #64748b;
  font-size: 1rem;
  line-height: 1.6;
}

.modern-stats {
  display: flex;
  gap: 1rem;
  position: relative;
  z-index: 2;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card.pending {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
  border-color: rgba(245, 158, 11, 0.2);
}

.stat-card.today {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
  border-color: rgba(34, 197, 94, 0.2);
}

.stat-card:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-card.pending .stat-icon {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.stat-card.today .stat-icon {
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.stat-label {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.125rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 筛选器样式 */
.modern-filters {
  margin-bottom: 1.5rem;
}

.filter-container {
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.9) 0%, 
      rgba(248, 250, 252, 0.8) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 1rem;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.05),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-tabs {
  display: flex;
  gap: 0.5rem;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  color: #64748b;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.filter-tab::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(34, 197, 94, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.filter-tab:hover:not(.active) {
  background: rgba(255, 255, 255, 0.8);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
}

.filter-tab:hover:not(.active)::before {
  opacity: 1;
}

.filter-tab.active {
  background: linear-gradient(135deg, #3b82f6 0%, #22c55e 100%);
  color: white;
  border-color: #3b82f6;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
}

.count {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
}

.filter-tab.active .count {
  background: rgba(255, 255, 255, 0.25);
}

.review-list {
  margin-bottom: 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-skeleton {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.empty-state {
  background: white;
  padding: 40px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  text-align: center;
}

/* 文章卡片样式 */
.article-cards {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modern-review-card {
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.95) 0%, 
      rgba(248, 250, 252, 0.9) 100%
    );
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  padding: 1.5rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.05),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.modern-review-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(34, 197, 94, 0.01));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.modern-review-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 
    0 12px 40px rgba(0, 0, 0, 0.1),
    0 4px 20px rgba(59, 130, 246, 0.05);
}

.modern-review-card:hover::before {
  opacity: 1;
}

.modern-review-card.pending {
  border-left: 4px solid #f59e0b;
  box-shadow: 
    0 4px 20px rgba(245, 158, 11, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.modern-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  position: relative;
  z-index: 2;
}

.article-info {
  flex: 1;
}

.modern-article-title {
  margin: 0 0 0.75rem 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.4;
  transition: color 0.3s ease;
}

.modern-article-title:hover {
  color: #3b82f6;
}

.modern-article-meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
  font-size: 0.875rem;
  color: #64748b;
  transition: all 0.3s ease;
  border: 1px solid rgba(59, 130, 246, 0.1);
}

.meta-item:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.2);
  transform: scale(1.05);
}

.meta-item.author {
  background: rgba(139, 92, 246, 0.05);
  border-color: rgba(139, 92, 246, 0.1);
}

.meta-item.author:hover {
  background: rgba(139, 92, 246, 0.1);
  border-color: rgba(139, 92, 246, 0.2);
}

.meta-item.time {
  background: rgba(6, 182, 212, 0.05);
  border-color: rgba(6, 182, 212, 0.1);
}

.meta-item.time:hover {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.2);
}

.meta-item.category {
  background: rgba(34, 197, 94, 0.05);
  border-color: rgba(34, 197, 94, 0.1);
}

.meta-item.category:hover {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.2);
}

.modern-status-badge {
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}

.status-indicator {
  padding: 0.5rem 1rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: relative;
  overflow: hidden;
}

.status-indicator.pending {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.1));
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-indicator.published {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(22, 163, 74, 0.1));
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-indicator.rejected {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-indicator.draft {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.15), rgba(75, 85, 99, 0.1));
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.article-summary {
  margin-bottom: 16px;
  color: #4b5563;
  line-height: 1.6;
}

.article-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.tag-item {
  background: #f3f4f6;
  border: none;
}

.more-tags {
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
}

.seo-info {
  background: #f9fafb;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}

.seo-title, .seo-desc {
  margin-bottom: 4px;
  color: #4b5563;
}

.reject-reason {
  margin-bottom: 16px;
}

/* 操作按钮样式 */
.modern-card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.3);
  position: relative;
  z-index: 2;
}

.action-left, .action-right {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.action-link {
  text-decoration: none;
  color: inherit;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-btn.preview {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05));
  color: #2563eb;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.action-btn.preview::before {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05));
}

.action-btn.history {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.05));
  color: #7c3aed;
  border: 1px solid rgba(139, 92, 246, 0.2);
}

.action-btn.history::before {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.05));
}

.action-btn.link {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(8, 145, 178, 0.05));
  color: #0891b2;
  border: 1px solid rgba(6, 182, 212, 0.2);
}

.action-btn.link::before {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(8, 145, 178, 0.05));
}

.action-btn.reject {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.action-btn.reject::before {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
}

.action-btn.approve {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.action-btn.approve::before {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
}

.action-btn:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.action-btn:hover::before {
  opacity: 1;
}

.action-btn:active {
  transform: translateY(0) scale(0.98);
}

/* 分页样式 */
.modern-pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 1.5rem;
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.95) 0%, 
      rgba(248, 250, 252, 0.9) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.05),
    0 1px 3px rgba(0, 0, 0, 0.1);
  margin-top: 1.5rem;
}

.modern-pagination-component :deep(.el-pagination) {
  gap: 0.5rem;
}

.modern-pagination-component :deep(.el-pagination .el-pager li) {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

.modern-pagination-component :deep(.el-pagination .el-pager li:hover) {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
  transform: translateY(-2px);
}

.modern-pagination-component :deep(.el-pagination .el-pager li.is-active) {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-color: #22c55e;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
}

.modern-pagination-component :deep(.el-pagination .btn-prev),
.modern-pagination-component :deep(.el-pagination .btn-next) {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

.modern-pagination-component :deep(.el-pagination .btn-prev:hover),
.modern-pagination-component :deep(.el-pagination .btn-next:hover) {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
  transform: translateY(-2px);
}

.preview-content {
  max-height: 60vh;
  overflow-y: auto;
}

.preview-meta {
  background: #f9fafb;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
}

.preview-meta > div {
  margin-bottom: 8px;
}

.preview-body {
  line-height: 1.8;
  color: #374151;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.version-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.version-header {
  display: flex;
  gap: 16px;
  font-size: 14px;
}

.version-no {
  font-weight: 500;
  color: #1f2937;
}

.version-time, .version-editor {
  color: #6b7280;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-stats {
    align-self: stretch;
    justify-content: space-around;
  }
  
  .card-header {
    flex-direction: column;
    gap: 12px;
  }
  
  .article-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .card-actions {
    flex-direction: column;
    gap: 12px;
  }
  
  .action-left, .action-right {
    justify-content: center;
  }
  
  .version-item {
    flex-direction: column;
    gap: 8px;
  }
  
  .version-header {
    flex-direction: column;
    gap: 4px;
  }
}
</style>