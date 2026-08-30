<template>
  <div class="comment-management">
    <AdminPageHeader title="评论管理" description="审核评论并维护讨论质量。" />

    <!-- Summary Strip(05 §15):待审核/今日/已通过/已拒绝 -->
    <AdminSummaryStrip :items="summaryItems" />

    <!-- Toolbar:状态/文章筛选 + 内容搜索 + 结果数/刷新;批量在选中后出现 -->
    <AdminToolbar
      v-model:search="filters.content"
      search-placeholder="搜索评论内容"
      :result-count="error ? null : pagination.total"
      refreshable
      @update:search="onSearchInput"
      @refresh="loadComments"
    >
      <template #filters>
        <select v-model="filters.status" class="adm-select" aria-label="按状态筛选" @change="handleFilterChange">
          <option value="">全部状态</option>
          <option value="pending">待审核</option>
          <option value="approved">已通过</option>
          <option value="rejected">已拒绝</option>
        </select>
        <input
          v-model="filters.article_id"
          class="adm-input"
          type="text"
          placeholder="文章 ID"
          aria-label="按文章 ID 筛选"
          @keyup.enter="handleFilterChange"
        >
      </template>
    </AdminToolbar>

    <!-- 批量操作条(05 §10) -->
    <div v-if="selectedComments.length" class="bulk-bar">
      <span>已选择 {{ selectedComments.length }} 项</span>
      <button type="button" class="bulk-btn success" @click="handleBatchAction('approve')">批量通过</button>
      <button type="button" class="bulk-btn danger" @click="handleBatchAction('reject')">批量拒绝</button>
      <button type="button" class="bulk-btn" @click="selectedComments = []">取消选择</button>
    </div>

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="评论列表加载失败"
        compact
        @reload="loadComments"
      />
      <AdminStateBlock
        v-else-if="!loading && !comments.length"
        kind="empty"
        title="暂无评论"
        description="当前筛选条件下没有评论。"
        compact
      />
      <div v-else class="table-wrap">
        <el-table
          :data="comments"
          row-key="id"
          class="adm-table"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="42" />
          <el-table-column label="评论" min-width="320">
            <template #default="{ row }">
              <div class="comment-body">{{ row.content }}</div>
              <div class="comment-sub">
                文章 #{{ row.article_id }}
                <template v-if="row.parent_id">· 回复 #{{ row.parent_id }}</template>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="96">
            <template #default="{ row }">
              <AdminStatus :kind="statusKind(row.status)" :label="statusText(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="用户" width="80">
            <template #default="{ row }">
              <span class="cell-text">#{{ row.user_id }}</span>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="130">
            <template #default="{ row }">
              <span class="cell-text">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column width="180" fixed="right" align="right">
            <template #default="{ row }">
              <div class="row-actions-inline">
                <!-- 待审核:通过/拒绝直达(05 §15);已审核:撤销直达 -->
                <template v-if="row.status === 'pending'">
                  <button
                    type="button"
                    class="act-btn success"
                    :disabled="moderatingIds.has(row.id)"
                    @click="handleModerate(row, 'approve')"
                  >通过</button>
                  <button
                    type="button"
                    class="act-btn danger"
                    :disabled="moderatingIds.has(row.id)"
                    @click="handleModerate(row, 'reject')"
                  >拒绝</button>
                </template>
                <button
                  v-else
                  type="button"
                  class="edit-btn"
                  :disabled="moderatingIds.has(row.id)"
                  @click="handleModerate(row, row.status === 'approved' ? 'reject' : 'approve')"
                >{{ row.status === 'approved' ? '撤销' : '恢复' }}</button>
                <AdminActionMenu :test-id="`comment-${row.id}`">
                  <template #menu>
                    <el-dropdown-item @click="viewArticle(row.article_id)">查看文章</el-dropdown-item>
                    <el-dropdown-item divided danger @click="handleModerate(row, 'reject')">拒绝评论</el-dropdown-item>
                  </template>
                </AdminActionMenu>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ pagination.total }} 条</span>
        <el-pagination
          layout="prev, pager, next, sizes"
          :total="pagination.total"
          :current-page="pagination.page"
          :page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :pager-count="5"
          small
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminActionMenu from '../../components/admin/AdminActionMenu.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const router = useRouter();

const loading = ref(false);
const error = ref(false);
/** @type {import('vue').Ref<any[]>} */
const comments = ref([]);
/** @type {import('vue').Ref<any[]>} */
const selectedComments = ref([]);
/** @type {import('vue').Ref<Set<any>>} */
const moderatingIds = ref(new Set());

const stats = reactive({ pending: 0, today: 0, approved: 0, rejected: 0 });

const filters = reactive({ status: '', article_id: '', content: '' });

const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const summaryItems = computed(() => [
  { label: '待审核', value: stats.pending, note: '需要处理' },
  { label: '今日评论', value: stats.today, note: '过去 24 小时' },
  { label: '已通过', value: stats.approved, note: '公开显示' },
  { label: '已拒绝', value: stats.rejected, note: '历史累计' },
]);

/** @param {string | undefined} status @returns {'success'|'warning'|'neutral'|'danger'} */
function statusKind(status) {
  switch (status) {
    case 'approved': return 'success';
    case 'pending': return 'warning';
    case 'rejected': return 'danger';
    default: return 'neutral';
  }
}

/** @param {string | undefined} status */
function statusText(status) {
  switch (status) {
    case 'pending': return '待审核';
    case 'approved': return '已通过';
    case 'rejected': return '已拒绝';
    default: return '未知';
  }
}

/** @param {string | number | Date} dateStr */
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** @type {ReturnType<typeof setTimeout> | undefined} */
let searchTimer;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => handleFilterChange(), 300);
}

async function loadComments() {
  if (loading.value) return;
  loading.value = true;
  error.value = false;
  try {
    /** @type {Record<string, any>} */
    const params = { page: pagination.page, page_size: pagination.page_size };
    if (filters.status) params.status = filters.status;
    if (filters.article_id) params.article_id = filters.article_id;
    if (filters.content) params.content = filters.content;

    const response = await API.getAdminComments(params);
    if (response.data.code === 0) {
      const data = response.data.data;
      comments.value = data.list || [];
      pagination.total = data.total || 0;
      await loadStats();
    } else {
      error.value = true;
    }
  } catch (e) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  try {
    const response = await API.getCommentStats();
    if (response.data.code === 0) {
      Object.assign(stats, response.data.data);
    }
  } catch (e) {
    /* 统计失败不阻塞列表 */
  }
}

/** @param {any[]} selection */
function handleSelectionChange(selection) {
  selectedComments.value = selection;
}

function handleFilterChange() {
  pagination.page = 1;
  loadComments();
}

/** @param {number} page */
function handlePageChange(page) {
  pagination.page = page;
  loadComments();
}

/** @param {number} size */
function handleSizeChange(size) {
  pagination.page_size = size;
  pagination.page = 1;
  loadComments();
}

/** @param {any} comment @param {string} action */
async function handleModerate(comment, action) {
  if (moderatingIds.value.has(comment.id)) return;
  try {
    moderatingIds.value.add(comment.id);
    const response = await API.moderateComment(comment.id, { action });
    if (response.data.code === 0) {
      ElMessage.success(action === 'approve' ? '评论已通过' : '评论已拒绝');
      await loadComments();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (e) {
    ElMessage.error('操作失败');
  } finally {
    moderatingIds.value.delete(comment.id);
  }
}

/** @param {string} action */
async function handleBatchAction(action) {
  const targets = selectedComments.value;
  if (!targets.length) {
    ElMessage.warning('请先选择评论');
    return;
  }
  const actionText = action === 'approve' ? '通过' : '拒绝';
  try {
    await ElMessageBox.confirm(
      `确定要批量${actionText} ${targets.length} 条评论吗？`,
      `批量${actionText}`,
      { type: 'warning', confirmButtonText: `批量${actionText}`, cancelButtonText: '取消' },
    );
    let ok = 0;
    for (const c of targets) {
      try {
        const r = await API.moderateComment(c.id, { action });
        if (r.data.code === 0) ok += 1;
      } catch (e) {
        /* 单条失败继续(05 §10 Partial failure) */
      }
    }
    ElMessage.success(`已${actionText} ${ok}/${targets.length} 条评论`);
    selectedComments.value = [];
    await loadComments();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(`批量${actionText}失败`);
  }
}

/** @param {any} articleId */
function viewArticle(articleId) {
  const url = router.resolve({ name: 'ArticleDetail', params: { id: articleId } }).href;
  window.open(url, '_blank');
}

onMounted(() => {
  loadComments();
});
</script>

<style scoped>
.comment-management {
  width: 100%;
}
.comment-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.comment-management :deep(.el-table) {
  width: 100%;
}

/* 原生筛选控件(34px 体系) */
.adm-select,
.adm-input {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  outline: none;
}
.adm-select:focus,
.adm-input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}

/* 批量条 */
.bulk-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: -1px;
  padding: 8px 12px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container) var(--adm-r-container) 0 0;
  background: var(--adm-primary-soft);
  color: var(--adm-primary);
  font-size: 12px;
}
.bulk-btn {
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 11px;
  cursor: pointer;
}
.bulk-btn.success {
  color: var(--adm-success);
  border-color: var(--adm-success);
}
.bulk-btn.danger {
  color: var(--adm-danger);
  border-color: var(--adm-danger);
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

/* 评论列:内容 + 弱化副行(05 §17) */
.comment-body {
  font-size: 12px;
  color: var(--adm-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.comment-sub {
  margin-top: 4px;
  font-size: 11px;
  color: var(--adm-muted);
}
.cell-text {
  font-size: 12px;
  color: var(--adm-text-2);
  font-variant-numeric: tabular-nums;
}

/* 行内审核按钮(05 §15) */
.row-actions-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.act-btn,
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
.act-btn.success {
  color: var(--adm-success);
  border-color: var(--adm-success);
}
.act-btn.success:hover:not(:disabled) {
  background: var(--adm-success-soft);
}
.act-btn.danger {
  color: var(--adm-danger);
  border-color: var(--adm-danger);
}
.act-btn.danger:hover:not(:disabled) {
  background: var(--adm-danger-soft);
}
.act-btn:disabled,
.edit-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.edit-btn:hover:not(:disabled) {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
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
