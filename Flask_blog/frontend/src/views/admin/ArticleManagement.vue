<template>
  <div class="article-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">文章管理</h1>
        <p class="page-description">管理所有文章，包括草稿、待审核和已发布的内容</p>
      </div>
      <div class="header-actions">
        <RouterLink to="/articles/new" class="action-button primary">
          <el-icon><EditPen /></el-icon>
          创建文章
        </RouterLink>
      </div>
    </div>

    <!-- 筛选控制栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-select v-model="filters.status" placeholder="状态筛选" clearable @change="handleFilterChange">
          <el-option label="全部状态" value="" />
          <el-option label="草稿" value="draft" />
          <el-option label="待审核" value="pending" />
          <el-option label="已发布" value="published" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>

        <el-select v-model="filters.category_id" placeholder="分类筛选" clearable @change="handleFilterChange">
          <el-option label="全部分类" value="" />
          <el-option 
            v-for="cat in categories" 
            :key="cat.id" 
            :label="cat.name" 
            :value="cat.id" 
          />
        </el-select>

        <el-select 
          v-if="userStore.isAdmin" 
          v-model="filters.author_id" 
          placeholder="作者筛选" 
          clearable 
          @change="handleFilterChange"
        >
          <el-option label="全部作者" value="" />
          <el-option 
            v-for="author in authors" 
            :key="author.id" 
            :label="author.nickname || author.email" 
            :value="author.id" 
          />
        </el-select>

        <el-input
          v-model="filters.search"
          placeholder="搜索文章标题..."
          clearable
          @clear="handleFilterChange"
          @keyup.enter="handleFilterChange"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <div class="filter-right">
        <el-button @click="handleRefresh" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedArticles.length > 0" class="bulk-actions">
      <div class="selected-info">
        已选择 {{ selectedArticles.length }} 篇文章
      </div>
      <div class="bulk-buttons">
        <el-button 
          v-if="userStore.canModerateContent" 
          @click="handleBulkApprove" 
          type="success" 
          size="small"
          :disabled="!canBulkApprove"
        >
          批量审核通过
        </el-button>
        <el-button 
          v-if="userStore.canModerateContent" 
          @click="handleBulkReject" 
          type="warning" 
          size="small"
          :disabled="!canBulkReject"
        >
          批量拒绝
        </el-button>
        <el-button @click="selectedArticles = []" size="small">
          取消选择
        </el-button>
      </div>
    </div>

    <!-- 文章列表 -->
    <div class="article-list-container">
      <el-table
        :data="articles"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column label="文章信息" min-width="300">
          <template #default="{ row }">
            <div class="article-info">
              <div class="article-title">
                <RouterLink 
                  :to="`/article/${row.slug}`" 
                  class="title-link"
                  target="_blank"
                >
                  {{ row.title }}
                </RouterLink>
              </div>
              <div class="article-meta">
                <span class="meta-item">
                  <el-icon><User /></el-icon>
                  {{ row.author?.nickname || row.author?.email }}
                </span>
                <span class="meta-item">
                  <el-icon><Calendar /></el-icon>
                  {{ formatDate(row.created_at) }}
                </span>
                <span v-if="row.category" class="meta-item">
                  <el-icon><Collection /></el-icon>
                  {{ row.category.name }}
                </span>
              </div>
              <div v-if="row.summary" class="article-summary">
                {{ row.summary }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="统计" width="120" align="center">
          <template #default="{ row }">
            <div class="article-stats">
              <div class="stat-item">
                <el-icon><View /></el-icon>
                <span>{{ row.views_count || 0 }}</span>
              </div>
              <div class="stat-item">
                <el-icon><Star /></el-icon>
                <span>{{ row.likes_count || 0 }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="发布时间" width="120" align="center">
          <template #default="{ row }">
            <div v-if="row.published_at" class="publish-time">
              {{ formatDate(row.published_at) }}
            </div>
            <div v-else-if="row.scheduled_at" class="schedule-time">
              <el-icon><Clock /></el-icon>
              {{ formatDate(row.scheduled_at) }}
            </div>
            <span v-else class="no-time">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                size="small" 
                @click="handleEdit(row)"
                :disabled="!canEdit(row)"
              >
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              
              <!-- 状态操作按钮 -->
              <el-dropdown @command="(command) => handleStatusAction(row, command)">
                <el-button size="small" type="primary">
                  状态操作
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item 
                      v-if="row.status === 'draft'" 
                      command="submit"
                      :disabled="!canSubmit(row)"
                    >
                      <el-icon><Upload /></el-icon>
                      提交审核
                    </el-dropdown-item>
                    
                    <el-dropdown-item 
                      v-if="row.status === 'pending' && userStore.canModerateContent" 
                      command="approve"
                    >
                      <el-icon><Check /></el-icon>
                      审核通过
                    </el-dropdown-item>
                    
                    <el-dropdown-item 
                      v-if="row.status === 'pending' && userStore.canModerateContent" 
                      command="reject"
                    >
                      <el-icon><Close /></el-icon>
                      拒绝发布
                    </el-dropdown-item>
                    
                    <el-dropdown-item 
                      v-if="row.status === 'published' && userStore.canModerateContent" 
                      command="unpublish"
                    >
                      <el-icon><Hide /></el-icon>
                      取消发布
                    </el-dropdown-item>
                    
                    <el-dropdown-item 
                      command="delete"
                      :disabled="!canDelete(row)"
                      divided
                    >
                      <el-icon><Delete /></el-icon>
                      删除文章
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="meta.total"
          :current-page="meta.page"
          :page-size="meta.page_size"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- 拒绝原因对话框 -->
    <el-dialog 
      v-model="rejectDialog.visible" 
      title="拒绝发布" 
      width="500px"
    >
      <el-form :model="rejectDialog.form" label-width="80px">
        <el-form-item label="拒绝原因" required>
          <el-input
            v-model="rejectDialog.form.reason"
            type="textarea"
            :rows="4"
            placeholder="请输入拒绝发布的原因，这将帮助作者了解如何改进文章..."
            maxlength="500"
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { 
  EditPen, Search, Refresh, User, Calendar, Collection, View, Star, 
  Clock, Edit, ArrowDown, Upload, Check, Close, Hide, Delete 
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';
import apiClient from '../../apiClient';

const router = useRouter();
const userStore = useUserStore();

// 响应式数据
const loading = ref(false);
const articles = ref<any[]>([]);
const categories = ref<any[]>([]);
const authors = ref<any[]>([]);
const selectedArticles = ref<any[]>([]);

// 筛选条件
const filters = reactive({
  status: '',
  category_id: '',
  author_id: '',
  search: ''
});

// 分页信息
const meta = reactive({
  total: 0,
  page: 1,
  page_size: 20
});

// 拒绝对话框
const rejectDialog = reactive({
  visible: false,
  loading: false,
  article: null as any,
  form: {
    reason: ''
  }
});

// 计算属性
const canBulkApprove = computed(() => {
  return selectedArticles.value.some(article => article.status === 'pending');
});

const canBulkReject = computed(() => {
  return selectedArticles.value.some(article => article.status === 'pending');
});

// 权限检查函数
function canEdit(article: any): boolean {
  return userStore.canModerateContent || article.author_id === userStore.user?.id;
}

function canSubmit(article: any): boolean {
  return article.author_id === userStore.user?.id || userStore.canModerateContent;
}

function canDelete(article: any): boolean {
  return userStore.canModerateContent || article.author_id === userStore.user?.id;
}

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
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

// 数据加载
async function loadArticles() {
  loading.value = true;
  
  try {
    const params: any = {
      page: meta.page,
      page_size: meta.page_size
    };

    // 添加筛选条件
    if (filters.status) params.status = filters.status;
    if (filters.category_id) params.category_id = filters.category_id;
    if (filters.author_id) params.author_id = filters.author_id;
    if (filters.search) params.search = filters.search;

    // 非管理员只能看自己的文章
    if (!userStore.canModerateContent) {
      params.author_id = userStore.user?.id;
    }

    // 调试信息
    console.log('🔍 文章加载调试信息:', {
      userRole: userStore.user?.role,
      canModerateContent: userStore.canModerateContent,
      requestParams: params,
      requestUrl: '/articles/'
    });

    const response = await apiClient.get('/articles/', { params });
    const data = response.data.data;
    
    // 更多调试信息
    console.log('📊 API响应调试:', {
      status: response.status,
      responseData: data,
      articlesCount: data?.list?.length,
      articleStatuses: data?.list?.map(a => ({ id: a.id, title: a.title, status: a.status }))
    });
    
    articles.value = data?.list || [];
    meta.total = data?.total || 0;
    meta.page = data?.page || 1;
    meta.page_size = data?.page_size || 20;
  } catch (error) {
    console.error('❌ 加载文章列表失败:', error);
    if (error.response) {
      console.error('错误详情:', {
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers
      });
    }
    ElMessage.error('加载文章列表失败');
  } finally {
    loading.value = false;
  }
}

async function loadCategories() {
  try {
    const response = await apiClient.get('/taxonomy/categories/');
    categories.value = response.data.data || [];
  } catch (error) {
    console.error('加载分类失败:', error);
  }
}

async function loadAuthors() {
  if (!userStore.isAdmin) return;
  
  try {
    const response = await apiClient.get('/users/');
    authors.value = response.data.data?.list || [];
  } catch (error) {
    console.error('加载作者列表失败:', error);
  }
}

// 事件处理
function handleFilterChange() {
  meta.page = 1;
  loadArticles();
}

function handleRefresh() {
  loadArticles();
}

// 刷新用户权限并重新加载
async function refreshUserAndReload() {
  try {
    await userStore.refreshUserInfo();
    ElMessage.success('用户权限已刷新');
    loadArticles();
  } catch (error) {
    ElMessage.error('刷新用户信息失败');
  }
}

// 强制重新登录
function forceRelogin() {
  ElMessageBox.confirm(
    '这将清除当前登录状态并跳转到登录页面，确定继续吗？',
    '重新登录',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    localStorage.clear();
    window.location.href = '/login';
  }).catch(() => {
    // 用户取消
  });
}

// 测试待审核文章
async function testPendingArticles() {
  try {
    console.log('🧪 开始测试待审核文章...');
    
    // 1. 检查用户信息和Token
    const token = localStorage.getItem('access_token');
    console.log('👤 当前用户信息:', {
      user: userStore.user,
      role: userStore.user?.role,
      canModerateContent: userStore.canModerateContent,
      isAdmin: userStore.isAdmin,
      token: token ? token.substring(0, 20) + '...' : 'null'
    });
    
    // 2. 检查JWT Token内容
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        console.log('🔑 JWT Token内容:', payload);
      } catch (e) {
        console.warn('JWT解析失败:', e);
      }
    }
    
    // 3. 测试用户信息API
    const userResponse = await apiClient.get('/users/me');
    console.log('👤 用户信息API响应:', userResponse.data);
    
    // 4. 直接请求pending状态的文章
    const pendingResponse = await apiClient.get('/articles/', {
      params: { status: 'pending', page: 1, page_size: 50 }
    });
    
    console.log('📋 待审核文章API响应:', pendingResponse.data);
    console.log('📋 待审核文章详细数据:', pendingResponse.data.data);
    
    // 5. 请求所有文章（不指定状态）
    const allResponse = await apiClient.get('/articles/', {
      params: { page: 1, page_size: 50 }
    });
    
    console.log('📋 所有文章API响应:', allResponse.data);
    console.log('📋 所有文章详细数据:', allResponse.data.data);
    
    // 6. 显示结果
    const pendingCount = pendingResponse.data.data?.total || 0;
    const allCount = allResponse.data.data?.total || 0;
    
    ElMessage.info(`找到 ${pendingCount} 篇待审核文章，总共 ${allCount} 篇文章`);
    
  } catch (error) {
    console.error('❌ 测试失败:', error);
    ElMessage.error('测试失败：' + (error.response?.data?.message || error.message));
  }
}

function handleSelectionChange(selection: any[]) {
  selectedArticles.value = selection;
}

function handlePageChange(page: number) {
  meta.page = page;
  loadArticles();
}

function handleSizeChange(size: number) {
  meta.page_size = size;
  meta.page = 1;
  loadArticles();
}

function handleEdit(article: any) {
  router.push(`/articles/edit/${article.id}`);
}

// 状态操作
async function handleStatusAction(article: any, action: string) {
  switch (action) {
    case 'submit':
      await submitArticle(article);
      break;
    case 'approve':
      await approveArticle(article);
      break;
    case 'reject':
      showRejectDialog(article);
      break;
    case 'unpublish':
      await unpublishArticle(article);
      break;
    case 'delete':
      await deleteArticle(article);
      break;
  }
}

async function submitArticle(article: any) {
  try {
    await apiClient.post(`/articles/${article.id}/submit`);
    ElMessage.success('文章已提交审核');
    loadArticles();
  } catch (error) {
    ElMessage.error('提交失败');
  }
}

async function approveArticle(article: any) {
  try {
    await apiClient.post(`/articles/${article.id}/approve`);
    ElMessage.success('文章审核通过');
    loadArticles();
  } catch (error) {
    ElMessage.error('审核失败');
  }
}

function showRejectDialog(article: any) {
  rejectDialog.article = article;
  rejectDialog.form.reason = '';
  rejectDialog.visible = true;
}

async function confirmReject() {
  if (!rejectDialog.form.reason.trim()) {
    ElMessage.warning('请输入拒绝原因');
    return;
  }

  rejectDialog.loading = true;
  
  try {
    await apiClient.post(`/articles/${rejectDialog.article.id}/reject`, {
      reason: rejectDialog.form.reason
    });
    ElMessage.success('文章已拒绝');
    rejectDialog.visible = false;
    loadArticles();
  } catch (error) {
    ElMessage.error('操作失败');
  } finally {
    rejectDialog.loading = false;
  }
}

async function unpublishArticle(article: any) {
  try {
    await ElMessageBox.confirm(
      '确定要取消发布这篇文章吗？',
      '确认操作',
      { type: 'warning' }
    );
    
    await apiClient.post(`/articles/${article.id}/unpublish`);
    ElMessage.success('已取消发布');
    loadArticles();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败');
    }
  }
}

async function deleteArticle(article: any) {
  try {
    await ElMessageBox.confirm(
      '确定要删除这篇文章吗？此操作不可恢复。',
      '确认删除',
      { type: 'warning' }
    );
    
    await apiClient.delete(`/articles/${article.id}`);
    ElMessage.success('文章已删除');
    loadArticles();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
}

// 批量操作
async function handleBulkApprove() {
  const pendingArticles = selectedArticles.value.filter(a => a.status === 'pending');
  if (pendingArticles.length === 0) {
    ElMessage.warning('没有可审核的文章');
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要批量审核通过 ${pendingArticles.length} 篇文章吗？`,
      '批量审核',
      { type: 'info' }
    );

    for (const article of pendingArticles) {
      await apiClient.post(`/articles/${article.id}/approve`);
    }

    ElMessage.success(`已批量审核通过 ${pendingArticles.length} 篇文章`);
    selectedArticles.value = [];
    loadArticles();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量操作失败');
    }
  }
}

async function handleBulkReject() {
  const pendingArticles = selectedArticles.value.filter(a => a.status === 'pending');
  if (pendingArticles.length === 0) {
    ElMessage.warning('没有可拒绝的文章');
    return;
  }

  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入拒绝原因',
      '批量拒绝',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /.+/,
        inputErrorMessage: '拒绝原因不能为空'
      }
    );

    for (const article of pendingArticles) {
      await apiClient.post(`/articles/${article.id}/reject`, { reason });
    }

    ElMessage.success(`已批量拒绝 ${pendingArticles.length} 篇文章`);
    selectedArticles.value = [];
    loadArticles();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量操作失败');
    }
  }
}

// 生命周期
onMounted(() => {
  loadArticles();
  loadCategories();
  loadAuthors();
});
</script>

<style scoped>
.article-management {
  max-width: 1400px;
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

.header-actions {
  display: flex;
  gap: 12px;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;
}

.action-button.primary {
  background: #3b82f6;
  color: white;
  border: 1px solid #3b82f6;
}

.action-button.primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.filter-left {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-left .el-select {
  width: 140px;
}

.search-input {
  width: 200px;
}

.filter-right {
  display: flex;
  gap: 8px;
}

.bulk-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
}

.selected-info {
  font-weight: 500;
  color: #1e40af;
}

.bulk-buttons {
  display: flex;
  gap: 8px;
}

.article-list-container {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.article-info {
  padding: 8px 0;
}

.article-title {
  margin-bottom: 8px;
}

.title-link {
  color: #1f2937;
  text-decoration: none;
  font-weight: 500;
  font-size: 16px;
}

.title-link:hover {
  color: #3b82f6;
}

.article-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #6b7280;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.article-summary {
  font-size: 14px;
  color: #9ca3af;
  line-height: 1.4;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #6b7280;
}

.publish-time, .schedule-time, .no-time {
  font-size: 14px;
  color: #6b7280;
}

.schedule-time {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #f59e0b;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.pagination-container {
  padding: 20px;
  display: flex;
  justify-content: center;
  background: #f9fafb;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .filter-bar {
    flex-direction: column;
    gap: 12px;
  }
  
  .filter-left {
    width: 100%;
  }
  
  .filter-left .el-select,
  .search-input {
    flex: 1;
    min-width: 120px;
  }
}

@media (max-width: 768px) {
  .article-meta {
    flex-direction: column;
    gap: 4px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .bulk-actions {
    flex-direction: column;
    gap: 12px;
  }
}
</style>