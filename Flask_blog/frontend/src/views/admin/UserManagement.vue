<template>
  <div class="user-management">
    <AdminPageHeader title="用户管理" description="管理后台账号、角色和账户状态。" />

    <!-- Summary Strip(05 §20) -->
    <AdminSummaryStrip :items="summaryItems" />

    <!-- Toolbar(05 §5) -->
    <AdminToolbar
      v-model:search="filters.search"
      search-placeholder="搜索用户名或邮箱"
      :result-count="error ? null : meta.total"
      refreshable
      @update:search="onSearchInput"
      @refresh="loadUsers"
    >
      <template #filters>
        <select v-model="filters.role" class="adm-select" aria-label="按角色筛选" @change="handleFilterChange">
          <option value="">全部角色</option>
          <option value="admin">管理员</option>
          <option value="editor">编辑</option>
          <option value="author">作者</option>
        </select>
      </template>
    </AdminToolbar>

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="用户列表加载失败"
        compact
        @reload="loadUsers"
      />
      <AdminStateBlock
        v-else-if="!loading && !users.length"
        kind="empty"
        title="暂无用户"
        description="当前筛选条件下没有用户。"
        compact
      />
      <div v-else class="table-wrap">
        <el-table :data="users" row-key="id" class="adm-table">
          <el-table-column label="用户" min-width="260">
            <template #default="{ row }">
              <div class="user-cell">
                <img
                  v-if="row.avatar"
                  :src="row.avatar"
                  :alt="row.nickname || row.email"
                  class="user-avatar"
                  @error="handleAvatarError"
                >
                <span v-else class="user-avatar avatar-fallback">{{ avatarInitial(row) }}</span>
                <span class="user-copy">
                  <b>{{ row.nickname || '未设置昵称' }}</b>
                  <small>{{ row.email }}</small>
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="100">
            <template #default="{ row }">
              <AdminTag :label="getRoleText(row.role)" :tone="roleTone(row.role)" />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <AdminStatus :kind="row.is_active ? 'success' : 'danger'" :label="row.is_active ? '正常' : '已禁用'" />
            </template>
          </el-table-column>
          <el-table-column label="文章" width="70">
            <template #default="{ row }">
              <span class="num">{{ row.article_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="注册时间" width="110">
            <template #default="{ row }">
              <span class="cell-text">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column width="150" fixed="right" align="right">
            <template #default="{ row }">
              <AdminActionMenu :test-id="`user-${row.id}`">
                <button type="button" class="edit-btn" :disabled="row.id === userStore.user?.id" @click="viewUserDetail(row)">
                  详情
                </button>
                <template #menu>
                  <el-dropdown-item :disabled="row.id === userStore.user?.id" @click="handleUserAction(row, 'changeRole')">修改角色</el-dropdown-item>
                  <el-dropdown-item :disabled="row.id === userStore.user?.id" @click="handleUserAction(row, row.is_active ? 'disable' : 'enable')">
                    {{ row.is_active ? '禁用账户' : '启用账户' }}
                  </el-dropdown-item>
                  <el-dropdown-item :disabled="row.id === userStore.user?.id" divided @click="handleUserAction(row, 'resetPassword')">重置密码</el-dropdown-item>
                  <el-dropdown-item danger :disabled="row.role === 'admin' || row.id === userStore.user?.id" @click="handleUserAction(row, 'delete')">删除用户</el-dropdown-item>
                </template>
              </AdminActionMenu>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ meta.total }} 个用户</span>
        <el-pagination
          layout="prev, pager, next, sizes"
          :total="meta.total"
          :current-page="meta.page"
          :page-size="meta.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :pager-count="5"
          small
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>

    <!-- 用户详情对话框(暂留 Dialog;Drawer 化留待详情内容扩权时) -->
    <UserDetailDialog
      :visible="detailDialog.visible"
      :user="detailDialog.user"
      @update:visible="detailDialog.visible = $event"
    />

    <!-- 修改角色对话框 -->
    <ChangeRoleDialog
      :visible="roleDialog.visible"
      :loading="roleDialog.loading"
      :user="roleDialog.user"
      @update:visible="roleDialog.visible = $event"
      @confirm="handleRoleConfirm"
    />
  </div>
</template>

<script setup>
/**
 * 用户管理(05 §20 List + Detail):外壳套 Pattern,业务/对话框全保留。
 * 详情 Drawer 化待 UserDetailDialog 内容扩展后进行(当前仅展示 Profile)。
 */
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';
import { API } from '../../api';
import UserDetailDialog from '../../components/admin/UserDetailDialog.vue';
import ChangeRoleDialog from '../../components/admin/ChangeRoleDialog.vue';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminTag from '../../components/admin/AdminTag.vue';
import AdminActionMenu from '../../components/admin/AdminActionMenu.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const userStore = useUserStore();

const loading = ref(false);
const error = ref(false);
/** @type {import('vue').Ref<any[]>} */
const users = ref([]);

const stats = reactive({ total: 0 });

const filters = reactive({
  role: '',
  search: '',
});

const meta = reactive({ total: 0, page: 1, page_size: 20 });

const detailDialog = reactive({
  visible: false,
  /** @type {any} */
  user: null,
});

const roleDialog = reactive({
  visible: false,
  loading: false,
  /** @type {any} */
  user: null,
});

const summaryItems = computed(() => [
  { label: '用户', value: stats.total, note: '后台账号' },
  { label: '管理员', value: getAdminCount(), note: '完整权限' },
  { label: '编辑/作者', value: users.value.filter((u) => u.role !== 'admin').length, note: '内容协作' },
  { label: '已禁用', value: users.value.filter((u) => u.is_active === false).length, note: '不可登录' },
]);

/** @param {any} user */
function avatarInitial(user) {
  return (user?.nickname || user?.email || 'U').slice(0, 1).toUpperCase();
}

function getAdminCount() {
  return users.value.filter((user) => user.role === 'admin').length;
}

/** @param {string | undefined} role */
function getRoleText(role) {
  switch (role) {
    case 'admin': return '管理员';
    case 'editor': return '编辑';
    case 'author': return '作者';
    default: return '用户';
  }
}

/** @param {string | undefined} role @returns {'blue'|'green'|'neutral'} */
function roleTone(role) {
  switch (role) {
    case 'admin': return 'blue';
    case 'editor': return 'green';
    default: return 'neutral';
  }
}

/** @param {string | undefined} dateStr */
function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '—';
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())}`;
}

/** @param {Event} e */
function handleAvatarError(e) {
  const img = /** @type {HTMLImageElement} */ (e.target);
  img.style.display = 'none';
}

async function loadUsers() {
  loading.value = true;
  error.value = false;
  try {
    /** @type {Record<string, any>} */
    const params = { page: meta.page, page_size: meta.page_size };
    if (filters.role) params.role = filters.role;
    if (filters.search) params.search = filters.search;

    const response = await API.getUsers(params);
    const data = response.data.data;
    users.value = data?.list || [];
    meta.total = data?.total || 0;
    meta.page = data?.page || 1;
    meta.page_size = data?.page_size || 20;
    stats.total = meta.total;
  } catch (e) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

/** @type {ReturnType<typeof setTimeout> | undefined} */
let searchTimer;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => handleFilterChange(), 300);
}

function handleFilterChange() {
  meta.page = 1;
  loadUsers();
}

/** @param {number} page */
function handlePageChange(page) {
  meta.page = page;
  loadUsers();
}

/** @param {number} size */
function handleSizeChange(size) {
  meta.page_size = size;
  meta.page = 1;
  loadUsers();
}

/** @param {any} user */
function viewUserDetail(user) {
  detailDialog.user = user;
  detailDialog.visible = true;
}

/** @param {any} user @param {string} action */
async function handleUserAction(user, action) {
  switch (action) {
    case 'changeRole':
      roleDialog.user = user;
      roleDialog.visible = true;
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

/** @param {string} newRole */
async function handleRoleConfirm(newRole) {
  const user = roleDialog.user;
  if (!newRole) {
    ElMessage.warning('请选择新角色');
    return;
  }
  if (newRole === user.role) {
    ElMessage.warning('新角色与当前角色相同');
    return;
  }
  roleDialog.loading = true;
  try {
    await API.updateUser(user.id, { role: newRole });
    ElMessage.success('角色修改成功');
    roleDialog.visible = false;
    loadUsers();
  } catch (e) {
    ElMessage.error('角色修改失败');
  } finally {
    roleDialog.loading = false;
  }
}

/** @param {any} user @param {boolean} isActive */
async function toggleUserStatus(user, isActive) {
  const action = isActive ? '启用' : '禁用';
  try {
    await ElMessageBox.confirm(
      `${action}用户「${user.nickname || user.email}」?${isActive ? '' : '禁用后该用户将无法登录。'}`,
      `${action}用户`,
      { type: 'warning', confirmButtonText: `${action}用户`, cancelButtonText: '取消' },
    );
    await API.updateUser(user.id, { is_active: isActive });
    ElMessage.success(`用户已${action}`);
    loadUsers();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(`${action}失败`);
  }
}

/** @param {any} user */
async function resetUserPassword(user) {
  try {
    await ElMessageBox.confirm(
      `重置用户「${user.nickname || user.email}」的密码?新密码将发送到用户邮箱。`,
      '重置密码',
      { type: 'warning', confirmButtonText: '重置密码', cancelButtonText: '取消' },
    );
    await API.resetUserPassword(user.id);
    ElMessage.success('密码重置成功，新密码已发送到用户邮箱');
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('密码重置失败');
  }
}

/** @param {any} user */
async function deleteUser(user) {
  if (user.role === 'admin') {
    ElMessage.warning('无法删除管理员账户');
    return;
  }
  try {
    await ElMessageBox.confirm(
      `删除用户「${user.nickname || user.email}」?该用户的所有文章也将被删除,操作不可恢复。`,
      '删除用户',
      { type: 'warning', confirmButtonText: '删除用户', cancelButtonText: '取消' },
    );
    await API.deleteUser(user.id);
    ElMessage.success('用户已删除');
    loadUsers();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败');
  }
}

onMounted(() => {
  loadUsers();
});
</script>

<style scoped>
.user-management {
  width: 100%;
}
.user-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.user-management :deep(.el-table) {
  width: 100%;
}

.adm-select {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  outline: none;
}
.adm-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}

/* 用户单元格(05 §17 两层:昵称+邮箱) */
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  object-fit: cover;
  flex-shrink: 0;
}
.avatar-fallback {
  display: grid;
  place-items: center;
  background: #eef2f7;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}
.user-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.user-copy b {
  font-size: 12px;
  color: var(--adm-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-copy small {
  font-size: 11px;
  color: var(--adm-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.num {
  font-variant-numeric: tabular-nums;
  color: var(--adm-text-2);
}
.cell-text {
  font-size: 12px;
  color: var(--adm-text-2);
}

.edit-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 11px;
  cursor: pointer;
}
.edit-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.edit-btn:hover:not(:disabled) {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

.table-card {
  border: 1px solid var(--adm-border);
  border-radius: 0 0 var(--adm-r-container) var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
}
.table-wrap {
  overflow: auto;
}
.table-footer {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 12px;
  border-top: 1px solid var(--adm-border);
  color: var(--adm-muted);
  font-size: 11px;
}
</style>
