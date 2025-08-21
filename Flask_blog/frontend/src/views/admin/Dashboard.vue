<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-subtitle">欢迎回来，{{ userStore.user?.nickname || userStore.user?.email }}</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon total-articles">
          <el-icon size="32"><Document /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.totalArticles || 0 }}</div>
          <div class="stat-label">总文章数</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon pending-articles">
          <el-icon size="32"><Clock /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.pendingArticles || 0 }}</div>
          <div class="stat-label">待审核文章</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon published-articles">
          <el-icon size="32"><Check /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.publishedArticles || 0 }}</div>
          <div class="stat-label">已发布文章</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon total-users">
          <el-icon size="32"><User /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.totalUsers || 0 }}</div>
          <div class="stat-label">用户总数</div>
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="dashboard-content">
      <!-- 左侧：待办事项和最新文章 -->
      <div class="content-left">
        <!-- 待办事项 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h3><el-icon><List /></el-icon> 待办事项</h3>
          </div>
          <div class="card-body">
            <div v-if="loading" class="loading-state">
              <el-skeleton :rows="3" animated />
            </div>
            <div v-else-if="!todos.length" class="empty-state">
              <el-empty description="暂无待办事项" />
            </div>
            <div v-else class="todo-list">
              <div v-for="todo in todos" :key="todo.id" class="todo-item">
                <div class="todo-content">
                  <div class="todo-title">{{ todo.title }}</div>
                  <div class="todo-meta">{{ formatDate(todo.created_at) }}</div>
                </div>
                <el-tag :type="getTodoType(todo.type)" size="small">
                  {{ getTodoText(todo.type) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 最新文章 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h3><el-icon><Document /></el-icon> 最新文章</h3>
            <RouterLink to="/admin/articles" class="view-all">查看全部</RouterLink>
          </div>
          <div class="card-body">
            <div v-if="loading" class="loading-state">
              <el-skeleton :rows="4" animated />
            </div>
            <div v-else-if="!recentArticles.length" class="empty-state">
              <el-empty description="暂无文章" />
            </div>
            <div v-else class="article-list">
              <div v-for="article in recentArticles" :key="article.id" class="article-item">
                <div class="article-content">
                  <div class="article-title">{{ article.title }}</div>
                  <div class="article-meta">
                    <span>{{ article.author?.nickname || article.author?.email }}</span>
                    <span>·</span>
                    <span>{{ formatDate(article.created_at) }}</span>
                  </div>
                </div>
                <el-tag :type="getStatusType(article.status)" size="small">
                  {{ getStatusText(article.status) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：快速操作和活动日志 -->
      <div class="content-right">
        <!-- 快速操作 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h3><el-icon><Lightning /></el-icon> 快速操作</h3>
          </div>
          <div class="card-body">
            <div class="quick-actions">
              <RouterLink to="/new-article" class="action-button">
                <el-icon><EditPen /></el-icon>
                <span>创建文章</span>
              </RouterLink>
              
              <RouterLink 
                v-if="hasRole(['editor', 'admin'])" 
                to="/admin/articles/review" 
                class="action-button"
              >
                <el-icon><View /></el-icon>
                <span>审核文章</span>
              </RouterLink>
              
              <RouterLink 
                v-if="hasRole(['editor', 'admin'])" 
                to="/admin/comments" 
                class="action-button"
              >
                <el-icon><ChatLineRound /></el-icon>
                <span>管理评论</span>
              </RouterLink>
              
              <RouterLink 
                v-if="hasRole(['admin'])" 
                to="/admin/users" 
                class="action-button"
              >
                <el-icon><UserFilled /></el-icon>
                <span>管理用户</span>
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- 活动日志 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h3><el-icon><Clock /></el-icon> 最近活动</h3>
          </div>
          <div class="card-body">
            <div v-if="loading" class="loading-state">
              <el-skeleton :rows="5" animated />
            </div>
            <div v-else-if="!activities.length" class="empty-state">
              <el-empty description="暂无活动记录" />
            </div>
            <div v-else class="activity-list">
              <div v-for="activity in activities" :key="activity.id" class="activity-item">
                <div class="activity-icon">
                  <el-icon><component :is="getActivityIcon(activity.action)" /></el-icon>
                </div>
                <div class="activity-content">
                  <div class="activity-text">{{ getActivityText(activity) }}</div>
                  <div class="activity-time">{{ formatRelativeTime(activity.created_at) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { 
  Document, Clock, Check, User, List, Lightning, EditPen, 
  View, ChatLineRound, UserFilled 
} from '@element-plus/icons-vue';
import { useUserStore } from '../../stores/user';
import apiClient from '../../apiClient';

const userStore = useUserStore();

// 数据状态
const loading = ref(true);
const stats = ref({
  totalArticles: 0,
  pendingArticles: 0,
  publishedArticles: 0,
  totalUsers: 0
});

const todos = ref<any[]>([]);
const recentArticles = ref<any[]>([]);
const activities = ref<any[]>([]);

// 权限检查
function hasRole(roles: string[]): boolean {
  return roles.includes(userStore.user?.role || '');
}

// 状态类型映射
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

function getTodoType(type: string): string {
  switch (type) {
    case 'review': return 'warning';
    case 'schedule': return 'info';
    case 'urgent': return 'danger';
    default: return '';
  }
}

function getTodoText(type: string): string {
  switch (type) {
    case 'review': return '待审核';
    case 'schedule': return '定时发布';
    case 'urgent': return '紧急';
    default: return type;
  }
}

function getActivityIcon(action: string): string {
  switch (action) {
    case 'submit': return 'Upload';
    case 'approve': return 'Check';
    case 'reject': return 'Close';
    case 'publish': return 'Promotion';
    case 'create': return 'Plus';
    default: return 'InfoFilled';
  }
}

function getActivityText(activity: any): string {
  const user = activity.operator?.nickname || activity.operator?.email || '用户';
  const article = activity.article?.title || '文章';
  
  switch (activity.action) {
    case 'submit': return `${user} 提交了文章 "${article}" 待审核`;
    case 'approve': return `${user} 审核通过了文章 "${article}"`;
    case 'reject': return `${user} 拒绝了文章 "${article}"`;
    case 'publish': return `${user} 发布了文章 "${article}"`;
    case 'create': return `${user} 创建了文章 "${article}"`;
    default: return `${user} 对文章 "${article}" 执行了 ${activity.action} 操作`;
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN');
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
async function loadDashboardData() {
  loading.value = true;
  
  try {
    // 并行加载各种数据
    const promises = [];
    
    // 统计数据 - 基于用户角色加载不同数据
    if (hasRole(['admin'])) {
      promises.push(loadAdminStats());
    } else if (hasRole(['editor'])) {
      promises.push(loadEditorStats());
    } else {
      promises.push(loadAuthorStats());
    }
    
    // 最新文章
    promises.push(loadRecentArticles());
    
    // 活动日志
    if (hasRole(['editor', 'admin'])) {
      promises.push(loadActivities());
    }
    
    // 待办事项
    promises.push(loadTodos());
    
    await Promise.all(promises);
  } catch (error) {
    console.error('加载仪表盘数据失败:', error);
  } finally {
    loading.value = false;
  }
}

async function loadAdminStats() {
  // 管理员看到所有统计
  const [articlesRes, usersRes] = await Promise.all([
    apiClient.get('/articles/', { params: { page: 1, page_size: 1 } }),
    apiClient.get('/users/', { params: { page: 1, page_size: 1 } })
  ]);
  
  stats.value.totalArticles = articlesRes.data.data?.total || 0;
  stats.value.totalUsers = usersRes.data.data?.total || 0;
  
  // 获取待审核文章数
  const pendingRes = await apiClient.get('/articles/', { 
    params: { page: 1, page_size: 1, status: 'pending' } 
  });
  stats.value.pendingArticles = pendingRes.data.data?.total || 0;
  
  // 获取已发布文章数
  const publishedRes = await apiClient.get('/articles/public/', { 
    params: { page: 1, page_size: 1 } 
  });
  stats.value.publishedArticles = publishedRes.data.data?.total || 0;
}

async function loadEditorStats() {
  // 编辑看到文章相关统计
  const [articlesRes, pendingRes, publishedRes] = await Promise.all([
    apiClient.get('/articles/', { params: { page: 1, page_size: 1 } }),
    apiClient.get('/articles/', { params: { page: 1, page_size: 1, status: 'pending' } }),
    apiClient.get('/articles/public/', { params: { page: 1, page_size: 1 } })
  ]);
  
  stats.value.totalArticles = articlesRes.data.data?.total || 0;
  stats.value.pendingArticles = pendingRes.data.data?.total || 0;
  stats.value.publishedArticles = publishedRes.data.data?.total || 0;
}

async function loadAuthorStats() {
  // 作者只看到自己的文章统计
  const userId = userStore.user?.id;
  const [myArticlesRes, myPublishedRes] = await Promise.all([
    apiClient.get('/articles/', { params: { page: 1, page_size: 1, author_id: userId } }),
    apiClient.get('/articles/public/', { params: { page: 1, page_size: 1, author_id: userId } })
  ]);
  
  stats.value.totalArticles = myArticlesRes.data.data?.total || 0;
  stats.value.publishedArticles = myPublishedRes.data.data?.total || 0;
}

async function loadRecentArticles() {
  try {
    let url = '/articles/';
    let params: any = { page: 1, page_size: 5, sort: 'created_at', order: 'desc' };
    
    // 作者只看自己的文章
    if (userStore.user?.role === 'author') {
      params.author_id = userStore.user.id;
    }
    
    const res = await apiClient.get(url, { params });
    recentArticles.value = res.data.data?.list || [];
  } catch (error) {
    console.error('加载最新文章失败:', error);
    recentArticles.value = [];
  }
}

async function loadActivities() {
  try {
    // 这里假设有审核日志API，如果没有则显示空状态
    // const res = await apiClient.get('/articles/audit_logs', { 
    //   params: { page: 1, page_size: 10 }
    // });
    // activities.value = res.data.data?.list || [];
    
    // 临时使用空数组
    activities.value = [];
  } catch (error) {
    console.error('加载活动日志失败:', error);
    activities.value = [];
  }
}

async function loadTodos() {
  try {
    // 根据角色生成不同的待办事项
    const todoList = [];
    
    if (hasRole(['editor', 'admin'])) {
      // 检查待审核文章
      if (stats.value.pendingArticles > 0) {
        todoList.push({
          id: 1,
          title: `有 ${stats.value.pendingArticles} 篇文章待审核`,
          type: 'review',
          created_at: new Date().toISOString()
        });
      }
    }
    
    todos.value = todoList;
  } catch (error) {
    console.error('加载待办事项失败:', error);
    todos.value = [];
  }
}

onMounted(() => {
  loadDashboardData();
});
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  margin-bottom: 24px;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-subtitle {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.total-articles {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.pending-articles {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.published-articles {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.total-users {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.dashboard-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

.content-left {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content-right {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-all {
  color: #3b82f6;
  text-decoration: none;
  font-size: 14px;
}

.view-all:hover {
  text-decoration: underline;
}

.card-body {
  padding: 24px;
}

.loading-state, .empty-state {
  padding: 20px 0;
}

.todo-list, .article-list, .activity-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.todo-item, .article-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.todo-item:last-child,
.article-item:last-child {
  border-bottom: none;
}

.todo-content, .article-content {
  flex: 1;
}

.todo-title, .article-title {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
}

.todo-meta, .article-meta {
  font-size: 14px;
  color: #6b7280;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  text-decoration: none;
  color: #475569;
  transition: all 0.2s;
}

.action-button:hover {
  background: #e2e8f0;
  transform: translateY(-2px);
}

.action-button span {
  font-size: 12px;
  font-weight: 500;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
}

.activity-text {
  font-size: 14px;
  color: #374151;
  margin-bottom: 4px;
}

.activity-time {
  font-size: 12px;
  color: #9ca3af;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .dashboard-content {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>