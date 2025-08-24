<template>
  <div class="user-management">
    <!-- 现代化页面头部 -->
    <div class="modern-page-header">
      <div class="page-header">
        <div class="title-container">
          <div class="title-icon">
            <el-icon size="28"><User /></el-icon>
          </div>
          <div class="header-content">
            <h1 class="page-title">用户管理</h1>
            <p class="page-description">管理用户账户、角色分配和权限控制</p>
          </div>
        </div>
        <div class="header-actions">
          <button @click="handleRefresh" :disabled="loading" class="action-btn secondary">
            <el-icon size="16" :class="{ 'is-loading': loading }"><Refresh /></el-icon>
            <span>刷新</span>
          </button>
        </div>
      </div>
      
      <!-- 统计面板 -->
      <div class="modern-stats">
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><DataBoard /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">总用户数</span>
              <span class="stat-value">{{ stats.total }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><User /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">今日活跃</span>
              <span class="stat-value active">{{ stats.activeToday }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><UserFilled /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">管理员</span>
              <span class="stat-value admin">{{ getAdminCount() }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 现代化筛选工具栏 -->
    <div class="modern-filter-container">
      <div class="filter-row">
        <div class="filter-group">
          <div class="modern-select">
            <el-select v-model="filters.role" placeholder="角色筛选" clearable @change="handleFilterChange" class="role-select">
              <el-option label="全部角色" value="" />
              <el-option label="管理员" value="admin" />
              <el-option label="编辑" value="editor" />
              <el-option label="作者" value="author" />
            </el-select>
          </div>

          <div class="modern-search-input">
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
          </div>

          <div class="modern-date-picker">
            <el-date-picker
              v-model="filters.dateRange"
              type="daterange"
              start-placeholder="注册开始日期"
              end-placeholder="注册结束日期"
              @change="handleFilterChange"
              size="default"
              class="date-range-picker"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 现代化用户列表 -->
    <div class="modern-user-list-container">
      <el-table
        :data="users"
        v-loading="loading"
        row-key="id"
        class="modern-table"
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
            <div class="modern-role-badge">
              <div class="role-indicator" :class="getRoleClass(row.role)">
                <el-icon size="14"><component :is="getRoleIcon(row.role)" /></el-icon>
                <span class="role-text">{{ getRoleText(row.role) }}</span>
              </div>
            </div>
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
            <div class="modern-status-badge">
              <div class="status-indicator" :class="row.is_active ? 'active' : 'inactive'">
                <el-icon size="14">
                  <component :is="row.is_active ? 'UserFilled' : 'Lock'" />
                </el-icon>
                <span class="status-text">{{ row.is_active ? '正常' : '禁用' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <div class="modern-action-buttons">
              <button 
                @click="viewUserDetail(row)"
                class="table-btn view"
              >
                <el-icon size="14"><View /></el-icon>
                <span>详情</span>
              </button>
              
              <el-dropdown 
                @command="(command) => handleUserAction(row, command)"
                :disabled="row.id === userStore.user?.id"
                class="modern-dropdown"
              >
                <button class="table-btn more" :disabled="row.id === userStore.user?.id">
                  <span>操作</span>
                  <el-icon size="14"><ArrowDown /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu class="modern-dropdown-menu">
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
  Lock, Unlock, Key, Delete, DataBoard 
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

function getAdminCount(): number {
  return users.value.filter(user => user.role === 'admin').length;
}

// 角色样式类获取
function getRoleClass(role: string): string {
  const roleClasses = {
    admin: 'role-admin',
    editor: 'role-editor', 
    author: 'role-author'
  };
  return roleClasses[role] || 'role-author';
}

// 角色图标获取
function getRoleIcon(role: string) {
  const roleIcons = {
    admin: UserFilled,
    editor: User,
    author: User
  };
  return roleIcons[role] || User;
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
  
  // 固定列透明度修复已完成
});
</script>

<style scoped>
/* ===== 现代化用户管理页面样式 ===== */
.user-management {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
}

/* 现代化页面头部 */
.modern-page-header {
  position: relative;
  background: 
    radial-gradient(circle at 20% 80%, rgba(6, 182, 212, 0.06) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
    radial-gradient(circle at 40% 40%, rgba(14, 165, 233, 0.06) 0%, transparent 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 2rem;
  margin-bottom: 2rem;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 4px 20px rgba(6, 182, 212, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.02);
  position: relative;
  overflow: hidden;
}

.modern-page-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg, 
    transparent 0%, 
    rgba(6, 182, 212, 0.3) 25%, 
    rgba(59, 130, 246, 0.3) 75%, 
    transparent 100%
  );
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.title-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #0891b2 0%, #3b82f6 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 20px rgba(6, 182, 212, 0.25);
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

.header-content h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #0f172a 0%, #0891b2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
}

.page-description {
  margin: 0;
  color: #64748b;
  font-size: 1rem;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 12px;
  border: 1px solid;
  backdrop-filter: blur(8px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  text-decoration: none;
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.8);
  border-color: rgba(6, 182, 212, 0.2);
  color: #0891b2;
}

.action-btn.secondary:hover:not(:disabled) {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(6, 182, 212, 0.15);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.action-btn .el-icon.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 统计面板 */
.modern-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  padding: 1.5rem;
  backdrop-filter: blur(12px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #06b6d4, #3b82f6);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(6, 182, 212, 0.15);
  border-color: rgba(6, 182, 212, 0.3);
}

.stat-card:hover::before {
  opacity: 1;
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(59, 130, 246, 0.1));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0891b2;
  border: 1px solid rgba(6, 182, 212, 0.2);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1;
}

.stat-value.active {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-value.admin {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 现代化筛选容器 - 修复溢出问题 */
.modern-filter-container {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  backdrop-filter: blur(12px);
  box-shadow: 0 2px 12px rgba(6, 182, 212, 0.08);
  overflow: hidden;
}

/* 完全重写固定列样式 */
.user-management :deep(.el-table__fixed-right) {
  background: #ffffff !important;
  box-shadow: -2px 0 8px rgba(0,0,0,0.1) !important;
}

.user-management :deep(.el-table__fixed-right .el-table__header),
.user-management :deep(.el-table__fixed-right .el-table__body) {
  background: #ffffff !important;
}

.user-management :deep(.el-table__fixed-right th),
.user-management :deep(.el-table__fixed-right td) {
  background-color: #ffffff !important;
  background: #ffffff !important;
}

/* 终极解决方案：针对Element Plus真正的固定列结构 */
:deep(.el-table-fixed-column--right) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
  z-index: 10 !important;
}

:deep(th.el-table-fixed-column--right) {
  background: #f8fafc !important;
  background-color: #f8fafc !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
  border-left: 1px solid rgba(6, 182, 212, 0.15) !important;
}

:deep(td.el-table-fixed-column--right) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
  border-left: 1px solid rgba(6, 182, 212, 0.1) !important;
}

/* 悬停状态的固定列 */
:deep(tr:hover td.el-table-fixed-column--right) {
  background: #f0f9ff !important;
  background-color: #f0f9ff !important;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  min-width: 0;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
  flex-wrap: wrap;
  min-width: 0;
}

.modern-select,
.modern-search-input {
  flex: 1;
  min-width: 200px;
}

.modern-date-picker {
  flex: 0 0 auto;
  width: 260px;
  min-width: 260px;
  max-width: 260px;
}

.modern-date-picker .el-date-editor {
  width: 100% !important;
}

/* Element Plus 组件样式覆盖 */
:deep(.role-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

:deep(.role-select .el-input__wrapper:hover) {
  border-color: rgba(6, 182, 212, 0.3);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.1);
}

:deep(.search-input .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

:deep(.search-input .el-input__wrapper:hover) {
  border-color: rgba(6, 182, 212, 0.3);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.1);
}

:deep(.date-range-picker .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

:deep(.date-range-picker .el-input__wrapper:hover) {
  border-color: rgba(6, 182, 212, 0.3);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.1);
}

:deep(.date-range-picker.el-date-editor) {
  width: 100% !important;
  max-width: 100% !important;
}

:deep(.date-range-picker .el-input__inner) {
  width: 100% !important;
}

/* 现代化表格容器 - 彻底移除透明效果 */
.modern-user-list-container {
  background: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  backdrop-filter: none !important;
  box-shadow: 0 4px 20px rgba(6, 182, 212, 0.08);
  overflow: hidden;
}

:deep(.modern-table) {
  background: #ffffff;
}

:deep(.modern-table .el-table__header) {
  background: rgba(6, 182, 212, 0.05);
  border-radius: 0;
}

:deep(.modern-table .el-table__header th) {
  background: rgba(6, 182, 212, 0.05);
  border: none;
  color: #0f172a;
  font-weight: 600;
  font-size: 0.875rem;
  padding: 1rem 0.75rem;
}

:deep(.modern-table .el-table__body tr) {
  background: #ffffff !important;
  transition: all 0.3s ease;
}

:deep(.modern-table .el-table__body tr:hover) {
  background: rgba(6, 182, 212, 0.05) !important;
}

:deep(.modern-table .el-table__body td) {
  background: #ffffff !important;
  border: none;
  padding: 1rem 0.75rem;
  border-bottom: 1px solid rgba(6, 182, 212, 0.1);
}

/* 修复固定列的层级问题 - 彻底的不透明背景 */
:deep(.modern-table .el-table__fixed-right) {
  z-index: 10 !important;
  background: #ffffff !important;
  backdrop-filter: none !important;
  box-shadow: -4px 0 12px rgba(6, 182, 212, 0.08);
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right-patch) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  z-index: 10 !important;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__header) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__header th) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  border-left: 1px solid rgba(6, 182, 212, 0.15);
  position: relative;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__body) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__body td) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  border-left: 1px solid rgba(6, 182, 212, 0.1);
  position: relative;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__body tr) {
  background: #ffffff !important;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__body tr:hover) {
  background: #ffffff !important;
  opacity: 1 !important;
}

:deep(.modern-table .el-table__fixed-right .el-table__body tr:hover td) {
  background: #f0f9ff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

/* 覆盖所有可能的透明度设置 */
:deep(.modern-table .el-table__fixed-right *) {
  opacity: 1 !important;
  background-color: inherit;
}

:deep(.modern-table .el-table__fixed-right .cell) {
  background: transparent !important;
  opacity: 1 !important;
}

/* 最强制的固定列不透明度控制 */
:deep(.el-table__fixed-right) {
  background: #ffffff !important;
  z-index: 100 !important;
}

:deep(.el-table__fixed-right::before) {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff !important;
  z-index: -1;
}

:deep(.el-table__fixed-right .el-table__header),
:deep(.el-table__fixed-right .el-table__body),
:deep(.el-table__fixed-right .el-table__header th),
:deep(.el-table__fixed-right .el-table__body td),
:deep(.el-table__fixed-right .el-table__body tr) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

/* 专门针对表头固定列的强制不透明样式 */
:deep(.el-table__fixed-right .el-table__header-wrapper) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

:deep(.el-table__fixed-right .el-table__header-wrapper .el-table__header) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

:deep(.el-table__fixed-right .el-table__header-wrapper .el-table__header th) {
  background: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

/* 确保表头固定列有额外的白色背景层 */
:deep(.el-table__fixed-right .el-table__header-wrapper::before) {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff !important;
  z-index: -1;
}

/* 最强制的表头固定列样式 - 使用通配符覆盖所有可能的元素 */
:deep(.el-table__fixed-right *) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
}

/* 特别针对表头区域的强制样式 */
:deep(.modern-table .el-table__fixed-right) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
  z-index: 999 !important;
}

/* 覆盖任何可能的透明度设置 */
:deep(.modern-table .el-table__fixed-right),
:deep(.modern-table .el-table__fixed-right *),
:deep(.modern-table .el-table__fixed-right::before),
:deep(.modern-table .el-table__fixed-right::after) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  backdrop-filter: none !important;
  filter: none !important;
  opacity: 1 !important;
}

/* 移除所有伪元素装饰，确保完全不透明 */
:deep(.modern-table .el-table__fixed-right .el-table__header th::before) {
  display: none;
}

:deep(.modern-table .el-table__fixed-right .el-table__body tr:hover td::before) {
  display: none;
}

/* 最终解决方案：暴力覆盖所有透明度相关属性 */
.modern-user-list-container :deep(.el-table__fixed-right),
.modern-user-list-container :deep(.el-table__fixed-right-patch),
.modern-user-list-container :deep(.el-table__fixed-right *) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  background-image: none !important;
  backdrop-filter: none !important;
  filter: none !important;
  opacity: 1 !important;
  -webkit-backdrop-filter: none !important;
  z-index: inherit !important;
}

/* 强制覆盖表头固定列的所有背景属性 */
.modern-user-list-container :deep(.el-table__fixed-right .el-table__header),
.modern-user-list-container :deep(.el-table__fixed-right .el-table__header *) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  background-image: none !important;
  backdrop-filter: none !important;
  filter: none !important;
  opacity: 1 !important;
  -webkit-backdrop-filter: none !important;
}

/* 使用CSS变量强制覆盖Element Plus的内部样式 */
.modern-user-list-container {
  --el-table-bg-color: #ffffff;
  --el-table-tr-bg-color: #ffffff;
  --el-table-header-bg-color: #ffffff;
  --el-bg-color: #ffffff;
  --el-bg-color-page: #ffffff;
}

/* 终极解决方案：直接覆盖Element Plus的固定列样式类 */
.modern-user-list-container :deep(.el-table__fixed-right) {
  background: #ffffff !important;
  background-color: #ffffff !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
  z-index: 999 !important;
}

.modern-user-list-container :deep(.el-table__fixed-right::after) {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ffffff !important;
  pointer-events: none;
  z-index: 1;
}

/* 确保固定列的所有子元素都有正确的背景和层级 */
:deep(.modern-table .el-table__fixed-right *) {
  z-index: inherit;
}

:deep(.modern-table .el-table__fixed-right .cell) {
  background: transparent;
  position: relative;
  z-index: 1;
}

/* 用户信息样式 */
.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid rgba(6, 182, 212, 0.2);
  transition: all 0.3s ease;
}

.user-avatar:hover {
  border-color: rgba(6, 182, 212, 0.4);
  transform: scale(1.05);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(59, 130, 246, 0.1));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0891b2;
}

.user-details {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 0.25rem;
  font-size: 1rem;
}

.user-email {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 0.125rem;
}

.user-bio {
  font-size: 0.75rem;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

/* 现代化角色徽章 */
.modern-role-badge {
  display: flex;
  justify-content: center;
}

.role-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

.role-admin {
  background: rgba(220, 38, 38, 0.1);
  border-color: rgba(220, 38, 38, 0.2);
  color: #dc2626;
}

.role-editor {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.role-author {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.2);
  color: #0891b2;
}

.role-indicator:hover {
  transform: scale(1.05);
}

/* 文章统计样式 */
.article-stats {
  text-align: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.stat-item .stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0891b2;
}

.stat-item .stat-label {
  font-size: 0.75rem;
  color: #64748b;
}

/* 日期和活跃时间样式 */
.join-date, .last-active {
  font-size: 0.875rem;
  color: #64748b;
  text-align: center;
  font-weight: 500;
}

/* 现代化状态徽章 */
.modern-status-badge {
  display: flex;
  justify-content: center;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

.status-indicator.active {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-indicator.inactive {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.status-indicator:hover {
  transform: scale(1.05);
}

/* 现代化操作按钮 */
.modern-action-buttons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
}

.table-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 8px;
  border: 1px solid;
  backdrop-filter: blur(8px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  text-decoration: none;
}

.table-btn.view {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.2);
  color: #0891b2;
}

.table-btn.view:hover {
  background: rgba(6, 182, 212, 0.2);
  border-color: rgba(6, 182, 212, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.2);
}

.table-btn.more {
  background: rgba(100, 116, 139, 0.1);
  border-color: rgba(100, 116, 139, 0.2);
  color: #64748b;
}

.table-btn.more:hover:not(:disabled) {
  background: rgba(100, 116, 139, 0.2);
  border-color: rgba(100, 116, 139, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(100, 116, 139, 0.2);
}

.table-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

/* 现代化下拉菜单 */
.modern-dropdown {
  display: inline-block;
}

:deep(.modern-dropdown-menu) {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(6, 182, 212, 0.15);
  padding: 0.5rem;
}

:deep(.modern-dropdown-menu .el-dropdown-menu__item) {
  border-radius: 8px;
  margin-bottom: 0.25rem;
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

:deep(.modern-dropdown-menu .el-dropdown-menu__item:hover) {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.2);
  color: #0891b2;
}

:deep(.modern-dropdown-menu .el-dropdown-menu__item:last-child) {
  margin-bottom: 0;
}

:deep(.modern-dropdown-menu .el-dropdown-menu__item .el-icon) {
  margin-right: 0.5rem;
}

/* 分页样式 */
.pagination-container {
  padding: 2rem;
  display: flex;
  justify-content: center;
  background: rgba(6, 182, 212, 0.02);
  border-top: 1px solid rgba(6, 182, 212, 0.1);
}

:deep(.el-pagination) {
  --el-pagination-bg-color: rgba(255, 255, 255, 0.8);
  --el-pagination-button-bg-color: rgba(255, 255, 255, 0.6);
  --el-pagination-hover-color: #0891b2;
}

:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next),
:deep(.el-pagination .el-pager li) {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(6, 182, 212, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
  margin: 0 0.125rem;
}

:deep(.el-pagination .btn-prev:hover),
:deep(.el-pagination .btn-next:hover),
:deep(.el-pagination .el-pager li:hover) {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.2);
}

:deep(.el-pagination .el-pager li.is-active) {
  background: linear-gradient(135deg, #0891b2, #3b82f6);
  color: white;
  border-color: transparent;
}

/* 用户详情对话框样式 */
:deep(.el-dialog) {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(6, 182, 212, 0.15);
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.05), rgba(59, 130, 246, 0.05));
  border-bottom: 1px solid rgba(6, 182, 212, 0.1);
  border-radius: 16px 16px 0 0;
  padding: 1.5rem 2rem;
}

:deep(.el-dialog__title) {
  font-weight: 700;
  color: #0f172a;
  font-size: 1.25rem;
}

:deep(.el-dialog__body) {
  padding: 2rem;
}

.user-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h4 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0891b2;
  border-bottom: 2px solid rgba(6, 182, 212, 0.2);
  padding-bottom: 0.5rem;
  position: relative;
}

.detail-section h4::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 3rem;
  height: 2px;
  background: linear-gradient(90deg, #0891b2, #3b82f6);
  border-radius: 1px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(6, 182, 212, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(6, 182, 212, 0.1);
}

.detail-item .label {
  font-weight: 600;
  color: #64748b;
  min-width: 80px;
}

.detail-item .value {
  color: #0f172a;
  font-weight: 500;
}

.bio-content {
  padding: 1rem;
  background: rgba(6, 182, 212, 0.05);
  border-radius: 12px;
  color: #475569;
  line-height: 1.6;
  margin: 0;
  border: 1px solid rgba(6, 182, 212, 0.1);
}

.social-json {
  background: rgba(100, 116, 139, 0.05);
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.75rem;
  color: #64748b;
  overflow-x: auto;
  border: 1px solid rgba(100, 116, 139, 0.1);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.stat-box {
  text-align: center;
  padding: 1.5rem 1rem;
  background: rgba(6, 182, 212, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(6, 182, 212, 0.2);
  transition: all 0.3s ease;
}

.stat-box:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.15);
}

.stat-number {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #0891b2, #3b82f6);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.5rem;
}

.stat-text {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .user-management {
    padding: 1rem;
  }
  
  .modern-page-header {
    padding: 1.5rem;
  }
  
  .page-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .title-container {
    justify-content: center;
    text-align: center;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  .modern-stats {
    grid-template-columns: 1fr;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: stretch;
  }
  
  .modern-select,
  .modern-search-input {
    min-width: auto;
  }
  
  .modern-date-picker {
    width: 100%;
    min-width: auto;
    max-width: 100%;
  }
}

@media (max-width: 768px) {
  .title-container {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }
  
  .header-content h1 {
    font-size: 1.75rem;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .modern-action-buttons {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .user-bio {
    max-width: 150px;
  }
}

@media (max-width: 640px) {
  .modern-page-header {
    padding: 1rem;
  }
  
  .modern-filter-container {
    padding: 1rem;
  }
  
  :deep(.el-dialog) {
    margin: 1rem;
    width: calc(100% - 2rem);
  }
  
  :deep(.el-dialog__body) {
    padding: 1rem;
  }
}

/* 角色修改对话框样式 */
:deep(.el-form-item__label) {
  font-weight: 600;
  color: #0f172a;
}

:deep(.el-form-item__content) {
  display: flex;
  align-items: center;
}

:deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

:deep(.el-select .el-input__wrapper:hover) {
  border-color: rgba(6, 182, 212, 0.3);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.1);
}

:deep(.el-dialog__footer) {
  padding: 1.5rem 2rem;
  border-top: 1px solid rgba(6, 182, 212, 0.1);
  background: rgba(6, 182, 212, 0.02);
  border-radius: 0 0 16px 16px;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

:deep(.el-button) {
  border-radius: 8px;
  font-weight: 600;
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #0891b2, #3b82f6);
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.2);
}

:deep(.el-button--primary:hover) {
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
  transform: translateY(-1px);
}

:deep(.el-button--default) {
  background: rgba(255, 255, 255, 0.8);
  border-color: rgba(100, 116, 139, 0.2);
  color: #64748b;
}

:deep(.el-button--default:hover) {
  background: rgba(100, 116, 139, 0.1);
  border-color: rgba(100, 116, 139, 0.3);
  transform: translateY(-1px);
}
</style>