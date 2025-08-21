<template>
  <div class="user-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">用户管理</h1>
        <p class="page-description">管理用户账户、角色分配和权限控制</p>
      </div>
      <div class="header-stats">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总用户数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value active">{{ stats.activeToday }}</div>
          <div class="stat-label">今日活跃</div>
        </div>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-toolbar">
      <div class="filter-left">
        <el-select v-model="filters.role" placeholder="角色筛选" clearable @change="handleFilterChange">
          <el-option label="全部角色" value="" />
          <el-option label="管理员" value="admin" />
          <el-option label="编辑" value="editor" />
          <el-option label="作者" value="author" />
        </el-select>

        <el-input
          v-model="filters.search"
          placeholder="搜索用户名或邮箱..."
          clearable
          @clear="handleFilterChange"
          @keyup.enter="handleFilterChange"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          start-placeholder="注册开始日期"
          end-placeholder="注册结束日期"
          @change="handleFilterChange"
          size="default"
        />
      </div>

      <div class="filter-right">
        <el-button @click="handleRefresh" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <div class="user-list-container">
      <el-table
        :data="users"
        v-loading="loading"
        row-key="id"
      >
        <el-table-column label="用户信息" min-width="250">
          <template #default="{ row }">
            <div class="user-info">
              <div class="user-avatar">
                <img 
                  v-if="row.avatar" 
                  :src="row.avatar" 
                  :alt="row.nickname || row.email"
                  @error="handleAvatarError"
                />
                <div v-else class="avatar-placeholder">
                  <el-icon size="24"><User /></el-icon>
                </div>
              </div>
              <div class="user-details">
                <div class="user-name">
                  {{ row.nickname || '未设置昵称' }}
                </div>
                <div class="user-email">{{ row.email }}</div>
                <div v-if="row.bio" class="user-bio">{{ row.bio }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="文章统计" width="120" align="center">
          <template #default="{ row }">
            <div class="article-stats">
              <div class="stat-item">
                <span class="stat-value">{{ row.article_count || 0 }}</span>
                <span class="stat-label">文章</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="注册时间" width="120" align="center">
          <template #default="{ row }">
            <div class="join-date">
              {{ formatDate(row.created_at) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="最后活跃" width="120" align="center">
          <template #default="{ row }">
            <div class="last-active">
              {{ row.last_active ? formatRelativeTime(row.last_active) : '未知' }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag 
              :type="row.is_active ? 'success' : 'danger'" 
              size="small"
            >
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                size="small" 
                @click="viewUserDetail(row)"
              >
                <el-icon><View /></el-icon>
                详情
              </el-button>
              
              <el-dropdown 
                @command="(command) => handleUserAction(row, command)"
                :disabled="row.id === userStore.user?.id"
              >
                <el-button size="small" type="primary">
                  操作
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="changeRole">
                      <el-icon><UserFilled /></el-icon>
                      修改角色
                    </el-dropdown-item>
                    <el-dropdown-item 
                      :command="row.is_active ? 'disable' : 'enable'"
                    >
                      <el-icon><component :is="row.is_active ? 'Lock' : 'Unlock'" /></el-icon>
                      {{ row.is_active ? '禁用账户' : '启用账户' }}
                    </el-dropdown-item>
                    <el-dropdown-item 
                      command="resetPassword"
                      divided
                    >
                      <el-icon><Key /></el-icon>
                      重置密码
                    </el-dropdown-item>
                    <el-dropdown-item 
                      command="delete"
                      :disabled="row.role === 'admin'"
                    >
                      <el-icon><Delete /></el-icon>
                      删除用户
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

    <!-- 用户详情对话框 -->
    <el-dialog 
      v-model="detailDialog.visible" 
      :title="`用户详情 - ${detailDialog.user?.nickname || detailDialog.user?.email}`" 
      width="600px"
    >
      <div v-if="detailDialog.user" class="user-detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">邮箱:</span>
              <span class="value">{{ detailDialog.user.email }}</span>
            </div>
            <div class="detail-item">
              <span class="label">昵称:</span>
              <span class="value">{{ detailDialog.user.nickname || '未设置' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">角色:</span>
              <el-tag :type="getRoleType(detailDialog.user.role)">
                {{ getRoleText(detailDialog.user.role) }}
              </el-tag>
            </div>
            <div class="detail-item">
              <span class="label">注册时间:</span>
              <span class="value">{{ formatDate(detailDialog.user.created_at) }}</span>
            </div>
          </div>
        </div>

        <div v-if="detailDialog.user.bio" class="detail-section">
          <h4>个人简介</h4>
          <p class="bio-content">{{ detailDialog.user.bio }}</p>
        </div>

        <div v-if="detailDialog.user.social_links" class="detail-section">
          <h4>社交链接</h4>
          <div class="social-links">
            <!-- 这里可以解析并显示社交链接 -->
            <pre class="social-json">{{ detailDialog.user.social_links }}</pre>
          </div>
        </div>

        <div class="detail-section">
          <h4>统计信息</h4>
          <div class="stats-grid">
            <div class="stat-box">
              <div class="stat-number">{{ detailDialog.user.article_count || 0 }}</div>
              <div class="stat-text">发布文章</div>
            </div>
            <!-- 可以添加更多统计信息 -->
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 修改角色对话框 -->
    <el-dialog 
      v-model="roleDialog.visible" 
      title="修改用户角色" 
      width="400px"
    >
      <el-form :model="roleDialog.form" label-width="80px">
        <el-form-item label="用户">
          <span>{{ roleDialog.user?.nickname || roleDialog.user?.email }}</span>
        </el-form-item>
        <el-form-item label="当前角色">
          <el-tag :type="getRoleType(roleDialog.user?.role)">
            {{ getRoleText(roleDialog.user?.role) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="新角色" required>
          <el-select v-model="roleDialog.form.role" placeholder="选择新角色">
            <el-option label="作者" value="author" />
            <el-option label="编辑" value="editor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialog.visible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmRoleChange"
          :loading="roleDialog.loading"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { 
  Search, Refresh, User, View, ArrowDown, UserFilled, 
  Lock, Unlock, Key, Delete 
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';
import apiClient from '../../apiClient';

const userStore = useUserStore();

// 响应式数据
const loading = ref(false);
const users = ref<any[]>([]);

// 统计数据
const stats = reactive({
  total: 0,
  activeToday: 0
});

// 筛选条件
const filters = reactive({
  role: '',
  search: '',
  dateRange: null as any
});

// 分页信息
const meta = reactive({
  total: 0,
  page: 1,
  page_size: 20
});

// 对话框状态
const detailDialog = reactive({
  visible: false,
  user: null as any
});

const roleDialog = reactive({
  visible: false,
  loading: false,
  user: null as any,
  form: {
    role: ''
  }
});

// 工具函数
function getRoleType(role: string): string {
  switch (role) {
    case 'admin': return 'danger';
    case 'editor': return 'warning';
    case 'author': return 'info';
    default: return '';
  }
}

function getRoleText(role: string): string {
  switch (role) {
    case 'admin': return '管理员';
    case 'editor': return '编辑';
    case 'author': return '作者';
    default: return role;
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diff = now.getTime() - date.getTime();
  
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (hours < 24) {
    return `${hours}小时前`;
  } else if (days < 7) {
    return `${days}天前`;
  } else {
    return formatDate(dateStr);
  }
}

function handleAvatarError(e: Event) {
  const img = e.target as HTMLImageElement;
  img.style.display = 'none';
}

// 数据加载
async function loadUsers() {
  loading.value = true;
  
  try {
    const params: any = {
      page: meta.page,
      page_size: meta.page_size
    };

    // 添加筛选条件
    if (filters.role) params.role = filters.role;
    if (filters.search) params.search = filters.search;
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0].toISOString().split('T')[0];
      params.end_date = filters.dateRange[1].toISOString().split('T')[0];
    }

    const response = await apiClient.get('/users/', { params });
    const data = response.data.data;
    
    users.value = data?.list || [];
    meta.total = data?.total || 0;
    meta.page = data?.page || 1;
    meta.page_size = data?.page_size || 20;
    
    // 更新统计
    stats.total = meta.total;
  } catch (error) {
    console.error('加载用户列表失败:', error);
    ElMessage.error('加载用户列表失败');
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  try {
    // 这里可以添加更多统计数据的API调用
    // 比如今日活跃用户数等
    stats.activeToday = Math.floor(stats.total * 0.1); // 临时数据
  } catch (error) {
    console.error('加载统计数据失败:', error);
  }
}

// 事件处理
function handleFilterChange() {
  meta.page = 1;
  loadUsers();
}

function handleRefresh() {
  loadUsers();
}

function handlePageChange(page: number) {
  meta.page = page;
  loadUsers();
}

function handleSizeChange(size: number) {
  meta.page_size = size;
  meta.page = 1;
  loadUsers();
}

// 用户操作
function viewUserDetail(user: any) {
  detailDialog.user = user;
  detailDialog.visible = true;
}

async function handleUserAction(user: any, action: string) {
  switch (action) {
    case 'changeRole':
      showRoleDialog(user);
      break;
    case 'disable':
      await toggleUserStatus(user, false);
      break;
    case 'enable':
      await toggleUserStatus(user, true);
      break;
    case 'resetPassword':
      await resetUserPassword(user);
      break;
    case 'delete':
      await deleteUser(user);
      break;
  }
}

function showRoleDialog(user: any) {
  roleDialog.user = user;
  roleDialog.form.role = user.role;
  roleDialog.visible = true;
}

async function confirmRoleChange() {
  if (!roleDialog.form.role) {
    ElMessage.warning('请选择新角色');
    return;
  }

  if (roleDialog.form.role === roleDialog.user.role) {
    ElMessage.warning('新角色与当前角色相同');
    return;
  }

  roleDialog.loading = true;
  
  try {
    await apiClient.patch(`/users/${roleDialog.user.id}`, {
      role: roleDialog.form.role
    });
    
    ElMessage.success('角色修改成功');
    roleDialog.visible = false;
    loadUsers();
  } catch (error) {
    ElMessage.error('角色修改失败');
  } finally {
    roleDialog.loading = false;
  }
}

async function toggleUserStatus(user: any, isActive: boolean) {
  const action = isActive ? '启用' : '禁用';
  
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户 "${user.nickname || user.email}" 吗？`,
      `${action}用户`,
      { type: 'warning' }
    );

    await apiClient.patch(`/users/${user.id}`, {
      is_active: isActive
    });

    ElMessage.success(`用户已${action}`);
    loadUsers();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`${action}失败`);
    }
  }
}

async function resetUserPassword(user: any) {
  try {
    await ElMessageBox.confirm(
      `确定要重置用户 "${user.nickname || user.email}" 的密码吗？新密码将发送到用户邮箱。`,
      '重置密码',
      { type: 'warning' }
    );

    await apiClient.post(`/users/${user.id}/reset-password`);
    ElMessage.success('密码重置成功，新密码已发送到用户邮箱');
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('密码重置失败');
    }
  }
}

async function deleteUser(user: any) {
  if (user.role === 'admin') {
    ElMessage.warning('无法删除管理员账户');
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.nickname || user.email}" 吗？此操作不可恢复，该用户的所有文章也将被删除。`,
      '删除用户',
      { 
        type: 'error',
        confirmButtonText: '确认删除',
        confirmButtonClass: 'el-button--danger'
      }
    );

    await apiClient.delete(`/users/${user.id}`);
    ElMessage.success('用户已删除');
    loadUsers();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
}

// 生命周期
onMounted(() => {
  loadUsers();
  loadStats();
});
</script>

<style scoped>
.user-management {
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

.header-stats {
  display: flex;
  gap: 20px;
}

.stat-card {
  text-align: center;
  min-width: 80px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.stat-value.active {
  color: #10b981;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.filter-toolbar {
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
  width: 220px;
}

.filter-right {
  display: flex;
  gap: 8px;
}

.user-list-container {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}

.user-details {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 2px;
}

.user-email {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 2px;
}

.user-bio {
  font-size: 12px;
  color: #9ca3af;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.article-stats {
  text-align: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

.join-date, .last-active {
  font-size: 14px;
  color: #6b7280;
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

/* 用户详情对话框样式 */
.user-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #1f2937;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-item .label {
  font-weight: 500;
  color: #6b7280;
  min-width: 60px;
}

.detail-item .value {
  color: #1f2937;
}

.bio-content {
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
}

.social-json {
  background: #f3f4f6;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #6b7280;
  overflow-x: auto;
}

.stats-grid {
  display: flex;
  gap: 20px;
}

.stat-box {
  text-align: center;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  min-width: 80px;
}

.stat-number {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.stat-text {
  font-size: 14px;
  color: #6b7280;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .filter-toolbar {
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
  .header-stats {
    align-self: stretch;
    justify-content: space-around;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .user-bio {
    max-width: 150px;
  }
}
</style>