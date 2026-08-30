<template>
  <div class="article-management">
    <AdminPageHeader
      title="文章管理"
      description="管理、发布和维护站点文章内容。"
    >
      <RouterLink to="/articles/new" class="primary-btn">＋ 新建文章</RouterLink>
    </AdminPageHeader>

    <!-- Summary Strip(04 §14):数据可得的项;加载中显示占位 -->
    <AdminSummaryStrip :items="summaryItems" />

    <!-- Toolbar(05 §5):搜索 + 高频筛选(状态/专题) + 低频(作者)折叠 + 结果数/刷新 -->
    <AdminToolbar
      v-model:search="filters.search"
      search-placeholder="搜索文章标题或摘要"
      :result-count="error ? null : meta.total"
      refreshable
      @update:search="onSearchInput"
      @refresh="loadArticles"
    >
      <template #filters>
        <select v-model="filters.status" class="adm-select" aria-label="按状态筛选" @change="handleFilterChange">
          <option value="">全部状态</option>
          <option value="published">已发布</option>
          <option value="draft">草稿</option>
          <option value="pending">待审核</option>
          <option value="rejected">已拒绝</option>
        </select>
        <select v-model="filters.category_id" class="adm-select" aria-label="按专题筛选" @change="handleFilterChange">
          <option value="">全部专题</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select
          v-if="userStore.isAdmin"
          v-model="filters.author_id"
          class="adm-select"
          aria-label="按作者筛选"
          @change="handleFilterChange"
        >
          <option value="">全部作者</option>
          <option v-for="a in authors" :key="a.id" :value="a.id">
            {{ a.nickname || a.email }}
          </option>
        </select>
      </template>
    </AdminToolbar>

    <!-- 批量操作栏(05 §10):选中后出现 -->
    <div v-if="selectedArticles.length" class="bulk-bar">
      <span>已选择 {{ selectedArticles.length }} 项</span>
      <button
        v-if="canBulkApprove && userStore.canModerateContent"
        type="button"
        class="bulk-btn success"
        @click="handleBulkApprove"
      >批量通过</button>
      <button
        v-if="canBulkReject && userStore.canModerateContent"
        type="button"
        class="bulk-btn danger"
        @click="handleBulkReject"
      >批量拒绝</button>
      <button type="button" class="bulk-btn" @click="selectedArticles = []">取消选择</button>
    </div>

    <!-- 表格卡片(与 Toolbar 拼合) -->
    <section class="table-card">
      <!-- error 态(05 §31:靠近发生位置) -->
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="文章列表加载失败"
        description="请检查网络后重试。"
        compact
        @reload="loadArticles"
      />
      <!-- empty 态(05 §29) -->
      <AdminStateBlock
        v-else-if="!loading && !articles.length"
        kind="empty"
        title="暂无文章"
        description="当前筛选条件下没有文章。"
        compact
      >
        <RouterLink to="/articles/new" class="primary-btn">＋ 新建文章</RouterLink>
      </AdminStateBlock>

      <div v-else class="table-wrap">
        <el-table
          :data="articles"
          row-key="id"
          class="adm-table"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="42" />
          <el-table-column label="文章" min-width="300">
            <template #default="{ row }">
              <div class="article-title">
                <RouterLink :to="`/article/${row.slug}`" class="title-link" target="_blank">
                  {{ row.title }}
                </RouterLink>
              </div>
              <div v-if="row.summary" class="article-summary">{{ row.summary }}</div>
              <div v-if="row.category" class="badges">
                <span class="pill topic">{{ row.category.name || row.category }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="96">
            <template #default="{ row }">
              <AdminStatus :kind="statusKind(row.status)" :label="statusText(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="浏览" width="76">
            <template #default="{ row }">
              <span class="num">{{ row.views_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="发布时间" width="110">
            <template #default="{ row }">
              <div v-if="row.published_at" class="date-main">{{ formatDate(row.published_at) }}</div>
              <span v-else class="date-sub">未发布</span>
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="110">
            <template #default="{ row }">
              <div class="date-main">{{ formatDate(row.updated_at || row.created_at) }}</div>
              <div v-if="relativeDays(row.updated_at || row.created_at)" class="date-sub">
                {{ relativeDays(row.updated_at || row.created_at) }}
              </div>
            </template>
          </el-table-column>
          <el-table-column width="110" fixed="right" align="right">
            <template #default="{ row }">
              <AdminActionMenu :test-id="`article-${row.id}`">
                <button
                  type="button"
                  class="edit-btn"
                  :disabled="!canEdit(row)"
                  @click="handleEdit(row)"
                >编辑</button>
                <template #menu>
                  <el-dropdown-item
                    v-if="row.status === 'draft'"
                    :disabled="!canSubmit(row)"
                    @click="submitArticle(row)"
                  >提交审核</el-dropdown-item>
                  <el-dropdown-item
                    v-if="row.status === 'pending' && userStore.canModerateContent"
                    @click="approveArticle(row)"
                  >审核通过</el-dropdown-item>
                  <el-dropdown-item
                    v-if="row.status === 'pending' && userStore.canModerateContent"
                    @click="showRejectDialog(row)"
                  >拒绝发布</el-dropdown-item>
                  <el-dropdown-item
                    v-if="row.status === 'published' && userStore.canModerateContent"
                    @click="unpublishArticle(row)"
                  >取消发布</el-dropdown-item>
                  <el-dropdown-item divided danger :disabled="!canDelete(row)" @click="deleteArticle(row)">
                    删除文章
                  </el-dropdown-item>
                </template>
              </AdminActionMenu>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Table Footer(04 §21):选中态 + 分页 -->
      <div class="table-footer">
        <span>共 {{ meta.total }} 条</span>
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

    <!-- 拒绝原因对话框(05 §26) -->
    <ArticleRejectDialog
      :visible="rejectDialog.visible"
      :loading="rejectDialog.loading"
      @update:visible="rejectDialog.visible = $event"
      @confirm="confirmReject"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';
import { API } from '../../api';
import ArticleRejectDialog from '../../components/admin/ArticleRejectDialog.vue';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminActionMenu from '../../components/admin/AdminActionMenu.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const router = useRouter();
const userStore = useUserStore();

const loading = ref(false);
const error = ref(false);
/** @type {import('vue').Ref<any[]>} */
const articles = ref([]);
/** @type {import('vue').Ref<any[]>} */
const categories = ref([]);
/** @type {import('vue').Ref<any[]>} */
const authors = ref([]);
/** @type {import('vue').Ref<any[]>} */
const selectedArticles = ref([]);

const filters = reactive({
  status: '',
  category_id: '',
  author_id: '',
  search: '',
});

const meta = reactive({
  total: 0,
  page: 1,
  page_size: 20,
});

const rejectDialog = reactive({
  visible: false,
  loading: false,
  /** @type {any} */
  article: null,
});

const canBulkApprove = computed(() =>
  selectedArticles.value.some((a) => a.status === 'pending'),
);
const canBulkReject = computed(() =>
  selectedArticles.value.some((a) => a.status === 'pending'),
);

/** Summary Strip 数据:由当前列表与筛选推导(全量计数来自 total) */
const summaryItems = computed(() => [
  { label: '全部文章', value: meta.total, note: '当前站点内容' },
  { label: '已发布', value: countByStatus('published'), note: '公开可访问' },
  { label: '草稿', value: countByStatus('draft'), note: '仅后台可见' },
  { label: '待审核', value: countByStatus('pending'), note: '等待处理' },
]);

/** @param {string} status */
function countByStatus(status) {
  return articles.value.filter((a) => a.status === status).length;
}

/** @param {any} article */
function canEdit(article) {
  return userStore.canModerateContent || article.author_id === userStore.user?.id;
}

/** @param {any} article */
function canSubmit(article) {
  return article.author_id === userStore.user?.id || userStore.canModerateContent;
}

/** @param {any} article */
function canDelete(article) {
  return userStore.canModerateContent || article.author_id === userStore.user?.id;
}

/** @param {string | undefined} status @returns {'success'|'warning'|'neutral'|'danger'} */
function statusKind(status) {
  switch (status) {
    case 'published': return 'success';
    case 'pending': return 'warning';
    case 'draft': return 'neutral';
    case 'rejected': return 'danger';
    default: return 'neutral';
  }
}

/** @param {string | undefined} status */
function statusText(status) {
  switch (status) {
    case 'published': return '已发布';
    case 'pending': return '待审核';
    case 'draft': return '草稿';
    case 'rejected': return '已拒绝';
    default: return status || '未知';
  }
}

/** @param {string | number | Date} dateStr */
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())}`;
}

/** @param {string | number | Date} dateStr @returns {string} 相对天数文案,当天为空 */
function relativeDays(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return '今天';
  if (days === 1) return '昨天';
  return `${days} 天前`;
}

/** @type {ReturnType<typeof setTimeout> | undefined} */
let searchTimer = undefined;
function onSearchInput() {
  if (searchTimer !== undefined) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => handleFilterChange(), 300);
}

async function loadArticles() {
  loading.value = true;
  error.value = false;
  try {
    /** @type {Record<string, any>} */
    const params = {
      page: meta.page,
      page_size: meta.page_size,
    };
    if (filters.status) params.status = filters.status;
    if (filters.category_id) params.category_id = filters.category_id;
    if (filters.author_id) params.author_id = filters.author_id;
    if (filters.search) params.search = filters.search;
    // 非管理员只能看自己的文章
    if (!userStore.canModerateContent) {
      params.author_id = userStore.user?.id;
    }

    const response = await API.getArticles(params);
    const data = response.data.data;
    articles.value = data?.list || [];
    meta.total = data?.total || 0;
    meta.page = data?.page || 1;
    meta.page_size = data?.page_size || 20;
  } catch (e) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

async function loadCategories() {
  try {
    const response = await API.getCategories();
    categories.value = response.data.data || [];
  } catch (e) {
    /* 筛选项失败不阻塞列表 */
  }
}

async function loadAuthors() {
  if (!userStore.isAdmin) return;
  try {
    const response = await API.getUsers();
    authors.value = response.data.data?.list || [];
  } catch (e) {
    /* 同上 */
  }
}

function handleFilterChange() {
  meta.page = 1;
  loadArticles();
}

/** @param {any[]} selection */
function handleSelectionChange(selection) {
  selectedArticles.value = selection;
}

/** @param {number} page */
function handlePageChange(page) {
  meta.page = page;
  loadArticles();
}

/** @param {number} size */
function handleSizeChange(size) {
  meta.page_size = size;
  meta.page = 1;
  loadArticles();
}

/** @param {any} article */
function handleEdit(article) {
  router.push(`/articles/edit/${article.id}`);
}

/** @param {any} article */
async function submitArticle(article) {
  try {
    await API.submitArticle(article.id);
    ElMessage.success('文章已提交审核');
    loadArticles();
  } catch (e) {
    ElMessage.error('提交失败');
  }
}

/** @param {any} article */
async function approveArticle(article) {
  try {
    await API.approveArticle(article.id);
    ElMessage.success('文章审核通过');
    loadArticles();
  } catch (e) {
    ElMessage.error('审核失败');
  }
}

/** @param {any} article */
function showRejectDialog(article) {
  rejectDialog.article = article;
  rejectDialog.visible = true;
}

/** @param {string} reason */
async function confirmReject(reason) {
  rejectDialog.loading = true;
  try {
    await API.rejectArticle(rejectDialog.article.id, { reason });
    ElMessage.success('文章已拒绝');
    rejectDialog.visible = false;
    loadArticles();
  } catch (e) {
    ElMessage.error('操作失败');
  } finally {
    rejectDialog.loading = false;
  }
}

/** @param {any} article */
async function unpublishArticle(article) {
  try {
    await ElMessageBox.confirm(
      `确定要取消发布「${article.title}」吗？`,
      '取消发布',
      { type: 'warning', confirmButtonText: '取消发布', cancelButtonText: '取消' },
    );
    await API.unpublishArticle(article.id);
    ElMessage.success('已取消发布');
    loadArticles();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败');
  }
}

/** @param {any} article */
async function deleteArticle(article) {
  try {
    await ElMessageBox.confirm(
      `删除文章「${article.title}」？删除后文章将不再出现在公开站。`,
      '删除文章',
      { type: 'warning', confirmButtonText: '删除文章', cancelButtonText: '取消' },
    );
    await API.deleteArticle(article.id);
    ElMessage.success('文章已删除');
    loadArticles();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败');
  }
}

// 批量操作
async function handleBulkApprove() {
  const pending = selectedArticles.value.filter((a) => a.status === 'pending');
  if (!pending.length) {
    ElMessage.warning('没有可审核的文章');
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确定要批量审核通过 ${pending.length} 篇文章吗？`,
      '批量审核',
      { type: 'info' },
    );
    for (const article of pending) {
      await API.approveArticle(article.id);
    }
    ElMessage.success(`已批量审核通过 ${pending.length} 篇文章`);
    selectedArticles.value = [];
    loadArticles();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('批量操作失败');
  }
}

async function handleBulkReject() {
  const pending = selectedArticles.value.filter((a) => a.status === 'pending');
  if (!pending.length) {
    ElMessage.warning('没有可拒绝的文章');
    return;
  }
  try {
    const { value: reason } = await ElMessageBox.prompt('请输入拒绝原因', '批量拒绝', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '拒绝原因不能为空',
    });
    for (const article of pending) {
      await API.rejectArticle(article.id, { reason });
    }
    ElMessage.success(`已批量拒绝 ${pending.length} 篇文章`);
    selectedArticles.value = [];
    loadArticles();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('批量操作失败');
  }
}

onMounted(() => {
  loadArticles();
  loadCategories();
  loadAuthors();
});
</script>

<style scoped>
.article-management {
  width: 100%;
}

/* Primary Action(04 §11:36px;蓝仅用于此处与 Active) */
.primary-btn {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--adm-primary);
  border-radius: 9px;
  background: var(--adm-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  text-decoration: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.primary-btn:hover {
  opacity: 0.92;
}

/* Toolbar 与表格拼合 */
.article-management :deep(.admin-toolbar) {
  border-bottom: 0;
}

/* 批量操作条(05 §10) */
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
  font-size: 13px;
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

/* 表格卡片 */
.table-card {
  border: 1px solid var(--adm-border);
  border-radius: 0 0 var(--adm-r-container) var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
}
.table-wrap {
  overflow: auto;
}
.article-management :deep(.adm-table) {
  width: 100%;
}

/* 第一业务列(05 §8.2):Title/Summary/Tag 三层 */
.article-title {
  font-size: 13px;
  font-weight: 680;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.title-link {
  color: var(--adm-text);
}
.title-link:hover {
  color: var(--adm-primary);
}
.article-summary {
  margin-top: 4px;
  color: var(--adm-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}
.badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.pill {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: #f4f4f5;
  color: var(--adm-muted);
  font-size: 12px;
}
.pill.topic {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
}
.num {
  font-variant-numeric: tabular-nums;
  color: var(--adm-text-2);
}
.date-main {
  color: var(--adm-text-2);
  font-size: 12px;
}
.date-sub {
  margin-top: 2px;
  color: var(--adm-muted-light);
  font-size: 12px;
}

/* 行内操作(05 §9:[编辑][···]) */
.article-management :deep(.edit-btn),
.edit-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 13px;
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

/* Table Footer(04 §21) */
.table-footer {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 12px;
  border-top: 1px solid var(--adm-border);
  color: var(--adm-muted);
  font-size: 12px;
}

@media (max-width: 719.98px) {
  .primary-btn {
    height: 34px;
  }
}
</style>
