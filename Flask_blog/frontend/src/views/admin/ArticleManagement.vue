<template>
  <div class="article-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-decoration" />
      <div class="header-pattern" />
      <div class="header-content">
        <div class="title-container">
          <div class="title-icon">
            <el-icon size="32"><Document /></el-icon>
          </div>
          <div class="title-text">
            <h1 class="page-title">文章管理</h1>
            <p class="page-description">管理所有文章，包括草稿、待审核和已发布的内容</p>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <RouterLink to="/articles/new" class="modern-action-btn primary">
          <el-icon size="18"><EditPen /></el-icon>
          <span>创建文章</span>
        </RouterLink>
      </div>
    </div>

    <!-- 筛选控制栏 -->
    <div class="modern-filter-bar">
      <div class="filter-container">
        <div class="filter-left">
          <div class="filter-group">
            <div class="filter-item">
              <el-select v-model="filters.status" placeholder="状态筛选" clearable class="modern-select" @change="handleFilterChange">
                <el-option label="全部状态" value="" />
                <el-option label="草稿" value="draft" />
                <el-option label="待审核" value="pending" />
                <el-option label="已发布" value="published" />
                <el-option label="已拒绝" value="rejected" />
              </el-select>
            </div>

            <div class="filter-item">
              <el-select v-model="filters.category_id" placeholder="分类筛选" clearable class="modern-select" @change="handleFilterChange">
                <el-option label="全部分类" value="" />
                <el-option 
                  v-for="cat in categories" 
                  :key="cat.id" 
                  :label="cat.name" 
                  :value="cat.id" 
                />
              </el-select>
            </div>

            <div v-if="userStore.isAdmin" class="filter-item">
              <el-select 
                v-model="filters.author_id" 
                placeholder="作者筛选" 
                clearable 
                class="modern-select"
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
            </div>

            <div class="filter-item search-item">
              <el-input
                v-model="filters.search"
                placeholder="搜索文章标题..."
                clearable
                class="modern-search-input"
                @clear="handleFilterChange"
                @keyup.enter="handleFilterChange"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
          </div>
        </div>

        <div class="filter-right">
          <button :disabled="loading" class="refresh-btn" @click="handleRefresh">
            <el-icon size="16" :class="{ 'is-loading': loading }"><Refresh /></el-icon>
            <span>刷新</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedArticles.length > 0" class="modern-bulk-actions">
      <div class="bulk-decoration" />
      <div class="bulk-content">
        <div class="selected-info">
          <el-icon size="18"><Select /></el-icon>
          <span>已选择 <strong>{{ selectedArticles.length }}</strong> 篇文章</span>
        </div>
        <div class="bulk-buttons">
          <button 
            v-if="userStore.canModerateContent" 
            class="bulk-btn success" 
            :disabled="!canBulkApprove"
            @click="handleBulkApprove"
          >
            <el-icon size="16"><Check /></el-icon>
            <span>批量审核通过</span>
          </button>
          <button 
            v-if="userStore.canModerateContent" 
            class="bulk-btn warning" 
            :disabled="!canBulkReject"
            @click="handleBulkReject"
          >
            <el-icon size="16"><Close /></el-icon>
            <span>批量拒绝</span>
          </button>
          <button class="bulk-btn cancel" @click="selectedArticles = []">
            <el-icon size="16"><RefreshLeft /></el-icon>
            <span>取消选择</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 文章列表 -->
    <div class="modern-article-list">
      <el-table
        v-loading="loading"
        :data="articles"
        row-key="id"
        class="modern-table"
        @selection-change="handleSelectionChange"
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
                :disabled="!canEdit(row)"
                @click="handleEdit(row)"
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
      <div class="modern-pagination">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="meta.total"
          :current-page="meta.page"
          :page-size="meta.page_size"
          :page-sizes="[10, 20, 50, 100]"
          class="modern-pagination-component"
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
      class="modern-dialog"
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
          :loading="rejectDialog.loading"
          @click="confirmReject"
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
  Clock, Edit, ArrowDown, Upload, Check, Close, Hide, Delete, Document,
  Select, RefreshLeft 
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
/* ===== 现代化文章管理样式 ===== */
.article-management {
  max-width: 1400px;
  margin: 0 auto;
  position: relative;
}

/* 页面头部 */
.page-header {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 2rem;
  background: 
    linear-gradient(135deg, 
      rgba(59, 130, 246, 0.05) 0%, 
      rgba(139, 92, 246, 0.03) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  box-shadow: 
    0 4px 20px rgba(59, 130, 246, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-decoration {
  position: absolute;
  top: -50px;
  left: -50px;
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
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
    radial-gradient(circle at 2px 2px, rgba(59, 130, 246, 0.1) 1px, transparent 0);
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
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
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
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
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

.header-actions {
  position: relative;
  z-index: 2;
}

.modern-action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 12px;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  border: none;
  cursor: pointer;
}

.modern-action-btn.primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.25);
}

.modern-action-btn.primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.modern-action-btn.primary:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.3);
}

.modern-action-btn.primary:hover::before {
  opacity: 1;
}

.modern-action-btn.primary:active {
  transform: translateY(0) scale(0.98);
}

/* 筛选栏样式 */
.modern-filter-bar {
  margin-bottom: 1.5rem;
  position: relative;
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
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.05),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-left {
  flex: 1;
}

.filter-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
}

.filter-item {
  position: relative;
}

.modern-select {
  width: 160px;
}

.search-item {
  min-width: 240px;
  flex: 1;
}

.modern-search-input {
  width: 100%;
}

.filter-right {
  margin-left: 1rem;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.05));
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  color: #8b5cf6;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.refresh-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.1));
  border-color: rgba(139, 92, 246, 0.3);
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.2);
}

.refresh-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-btn .is-loading {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 批量操作栏 */
.modern-bulk-actions {
  position: relative;
  margin-bottom: 1.5rem;
  background: 
    linear-gradient(135deg, 
      rgba(59, 130, 246, 0.08) 0%, 
      rgba(139, 92, 246, 0.05) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  overflow: hidden;
  animation: slideInDown 0.3s ease-out;
}

@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bulk-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4);
}

.bulk-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  position: relative;
  z-index: 2;
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #1e40af;
  font-size: 0.95rem;
}

.bulk-buttons {
  display: flex;
  gap: 0.75rem;
}

.bulk-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.bulk-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.bulk-btn.success {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.bulk-btn.success::before {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
}

.bulk-btn.warning {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.bulk-btn.warning::before {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
}

.bulk-btn.cancel {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.1), rgba(75, 85, 99, 0.05));
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.2);
}

.bulk-btn.cancel::before {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.1), rgba(75, 85, 99, 0.05));
}

.bulk-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.bulk-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.bulk-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.bulk-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
}

/* 文章列表容器 */
.modern-article-list {
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.95) 0%, 
      rgba(248, 250, 252, 0.9) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  overflow: hidden;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.05),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.modern-table {
  background: transparent;
}

.modern-table :deep(.el-table__header-wrapper) {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(139, 92, 246, 0.03));
}

.modern-table :deep(.el-table__header) {
  background: transparent;
}

.modern-table :deep(.el-table__header th) {
  background: transparent;
  border-bottom: 2px solid rgba(59, 130, 246, 0.1);
  color: #1e293b;
  font-weight: 600;
  padding: 1rem 0.75rem;
}

.modern-table :deep(.el-table__body-wrapper) {
  background: transparent;
}

.modern-table :deep(.el-table__row) {
  background: rgba(255, 255, 255, 0.6);
  transition: all 0.3s ease;
}

.modern-table :deep(.el-table__row:hover) {
  background: rgba(59, 130, 246, 0.05) !important;
  transform: scale(1.01);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.1);
}

.modern-table :deep(.el-table td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  padding: 1rem 0.75rem;
}

.modern-table :deep(.el-table--striped .el-table__row--striped) {
  background: rgba(248, 250, 252, 0.5);
}

.modern-table :deep(.el-table--striped .el-table__row--striped:hover) {
  background: rgba(59, 130, 246, 0.05) !important;
}

/* 文章信息样式 */
.article-info {
  padding: 0.75rem 0;
}

.article-title {
  margin-bottom: 0.75rem;
}

.title-link {
  color: #1e293b;
  text-decoration: none;
  font-weight: 600;
  font-size: 1rem;
  line-height: 1.4;
  transition: all 0.3s ease;
  position: relative;
}

.title-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 0.3s ease;
}

.title-link:hover {
  color: #3b82f6;
}

.title-link:hover::after {
  width: 100%;
}

.article-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: #64748b;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 6px;
  transition: all 0.3s ease;
}

.meta-item:hover {
  background: rgba(59, 130, 246, 0.1);
  transform: scale(1.05);
}

.article-summary {
  font-size: 0.875rem;
  color: #9ca3af;
  line-height: 1.5;
  max-width: 400px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  word-wrap: break-word;
}

.article-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #64748b;
  padding: 0.25rem 0.5rem;
  background: rgba(139, 92, 246, 0.05);
  border-radius: 6px;
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: rgba(139, 92, 246, 0.1);
  transform: scale(1.1);
}

.publish-time, .schedule-time, .no-time {
  font-size: 0.875rem;
  color: #64748b;
  padding: 0.25rem 0.5rem;
  background: rgba(6, 182, 212, 0.05);
  border-radius: 6px;
  text-align: center;
}

.schedule-time {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* 分页样式 */
.modern-pagination {
  padding: 1.5rem;
  display: flex;
  justify-content: center;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.6));
  border-top: 1px solid rgba(255, 255, 255, 0.3);
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
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px);
}

.modern-pagination-component :deep(.el-pagination .el-pager li.is-active) {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-color: #3b82f6;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
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
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .page-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .title-container {
    width: 100%;
  }
  
  .header-actions {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }
  
  .filter-container {
    flex-direction: column;
    gap: 1rem;
  }
  
  .filter-group {
    width: 100%;
    justify-content: flex-start;
  }
  
  .filter-item {
    flex: 1;
    min-width: 140px;
  }
  
  .search-item {
    min-width: 200px;
  }
  
  .filter-right {
    margin-left: 0;
    align-self: flex-end;
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: 1.5rem;
  }
  
  .title-container {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }
  
  .title-icon {
    width: 50px;
    height: 50px;
  }
  
  .page-title {
    font-size: 1.75rem;
  }
  
  .filter-container {
    padding: 1rem;
  }
  
  .filter-group {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .filter-item {
    width: 100%;
  }
  
  .modern-select,
  .modern-search-input {
    width: 100%;
  }
  
  .filter-right {
    align-self: stretch;
  }
  
  .refresh-btn {
    width: 100%;
    justify-content: center;
  }
  
  .bulk-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .bulk-buttons {
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .article-meta {
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .modern-table :deep(.el-table__row:hover) {
    transform: none;
  }
}

@media (max-width: 640px) {
  .bulk-buttons {
    flex-direction: column;
    width: 100%;
  }
  
  .bulk-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>