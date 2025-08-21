<template>
  <div class="article-review">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">文章审核</h1>
        <p class="page-description">审核作者提交的文章，确保内容质量</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-label">待审核</span>
          <span class="stat-value pending">{{ stats.pending }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">今日审核</span>
          <span class="stat-value">{{ stats.todayReviewed }}</span>
        </div>
      </div>
    </div>

    <!-- 快速筛选 -->
    <div class="quick-filters">
      <el-button-group>
        <el-button 
          :type="currentFilter === 'pending' ? 'primary' : ''"
          @click="setFilter('pending')"
        >
          待审核 ({{ stats.pending }})
        </el-button>
        <el-button 
          :type="currentFilter === 'all_recent' ? 'primary' : ''"
          @click="setFilter('all_recent')"
        >
          最近文章
        </el-button>
        <el-button 
          :type="currentFilter === 'my_reviewed' ? 'primary' : ''"
          @click="setFilter('my_reviewed')"
        >
          我审核的
        </el-button>
      </el-button-group>
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
          class="review-card"
          :class="{ 'pending': article.status === 'pending' }"
        >
          <!-- 文章基本信息 -->
          <div class="card-header">
            <div class="article-info">
              <h3 class="article-title">{{ article.title }}</h3>
              <div class="article-meta">
                <span class="author">
                  <el-icon><User /></el-icon>
                  {{ article.author?.nickname || article.author?.email }}
                </span>
                <span class="submit-time">
                  <el-icon><Clock /></el-icon>
                  {{ formatRelativeTime(article.created_at) }}
                </span>
                <span v-if="article.category" class="category">
                  <el-icon><Collection /></el-icon>
                  {{ article.category.name }}
                </span>
              </div>
            </div>
            <div class="status-badge">
              <el-tag :type="getStatusType(article.status)" size="large">
                {{ getStatusText(article.status) }}
              </el-tag>
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
          <div class="card-actions">
            <div class="action-left">
              <el-button @click="previewArticle(article)" size="small">
                <el-icon><View /></el-icon>
                预览
              </el-button>
              <el-button @click="viewHistory(article)" size="small">
                <el-icon><Clock /></el-icon>
                历史版本
              </el-button>
              <RouterLink :to="`/article/${article.slug}`" target="_blank">
                <el-button size="small">
                  <el-icon><Link /></el-icon>
                  查看页面
                </el-button>
              </RouterLink>
            </div>
            
            <div v-if="article.status === 'pending'" class="action-right">
              <el-button 
                @click="showRejectDialog(article)" 
                type="warning" 
                size="small"
              >
                <el-icon><Close /></el-icon>
                拒绝
              </el-button>
              <el-button 
                @click="approveArticle(article)" 
                type="success" 
                size="small"
              >
                <el-icon><Check /></el-icon>
                通过
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="meta.total > 0" class="pagination-container">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        @current-change="handlePageChange"
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
  User, Clock, Collection, View, Link, Close, Check 
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
.article-review {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.header-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.stat-value.pending {
  color: #f59e0b;
}

.quick-filters {
  margin-bottom: 24px;
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

.article-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.2s;
}

.review-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.review-card.pending {
  border-left: 4px solid #f59e0b;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.article-info {
  flex: 1;
}

.article-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.article-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 14px;
  color: #6b7280;
}

.article-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-badge {
  flex-shrink: 0;
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

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.action-left, .action-right {
  display: flex;
  gap: 8px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
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