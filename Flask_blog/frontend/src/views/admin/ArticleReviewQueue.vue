<template>
  <div class="review-queue">
    <AdminPageHeader title="文章审核" description="审核待发布文章，保证公开内容质量。" />

    <!-- Summary(05 V2 补充 §2 + 评审修订):两卡收紧为统一 Strip;
         第二卡为「今日已审核」(通过 N · 退回 N),已退回下沉为 Tab/筛选 -->
    <section class="summary-strip">
      <div class="sum-card">
        <label>待审核</label>
        <strong>{{ pendingCount }}</strong>
        <small>当前审核队列</small>
      </div>
      <div class="sum-card">
        <label>今日已审核</label>
        <strong>{{ approvedToday }}</strong>
        <small>通过 {{ approvedToday }} · 退回 {{ rejectedToday }}</small>
      </div>
    </section>

    <!-- Tabs(05 V2 补充 §2):普通 Selected State -->
    <div class="tabs">
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'pending' }"
        @click="switchTab('pending')"
      >待审核 {{ pendingCount }}</button>
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'recent' }"
        @click="switchTab('recent')"
      >最近处理</button>

    </div>

    <!-- Toolbar -->
    <AdminToolbar
      v-model:search="search"
      :search-placeholder="tab === 'pending' ? '搜索文章标题或提交人' : '搜索文章标题'"
      :result-count="error ? null : filteredRows.length"
      refreshable
      @update:search="() => {}"
      @refresh="loadTab"
    >
      <template #filters>
        <select v-model="topicFilter" class="adm-select" aria-label="按专题筛选">
          <option value="">全部专题</option>
          <option v-for="t in topicOptions" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-if="tab === 'pending'" v-model="sortAsc" class="adm-select" aria-label="排序方式">
          <option :value="true">最早提交优先</option>
          <option :value="false">最晚提交优先</option>
        </select>
        <select v-if="tab === 'recent'" v-model="resultFilter" class="adm-select" aria-label="按审核结果筛选">
          <option value="">全部结果</option>
          <option value="published">已通过</option>
          <option value="rejected">已退回</option>
        </select>
      </template>
    </AdminToolbar>

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="审核队列加载失败"
        compact
        @reload="loadTab"
      />
      <AdminStateBlock
        v-else-if="!loading && !filteredRows.length"
        kind="empty"
        :title="tab === 'pending' ? '暂无待审核文章' : tab === 'rejected' ? '没有已退回的文章' : '暂无最近处理记录'"
        :description="tab === 'pending' ? '新的审核请求会出现在这里。' : undefined"
        compact
      />
      <div v-else class="table-wrap">
        <el-table :data="filteredRows" row-key="id" class="adm-table">
          <el-table-column label="文章" min-width="320">
            <template #default="{ row }">
              <div class="cell-title">{{ row.title }}</div>
              <div v-if="row.summary" class="cell-sub">{{ row.summary }}</div>
            </template>
          </el-table-column>
          <el-table-column label="提交人" width="110">
            <template #default="{ row }">
              {{ row.author?.nickname || row.author?.email || '—' }}
            </template>
          </el-table-column>
          <el-table-column label="专题" width="120">
            <template #default="{ row }">
              <AdminTag v-if="row.category" :label="row.category.name || row.category" tone="blue" bordered />
              <span v-else class="cell-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" width="130">
            <template #default="{ row }">
              <span class="cell-text">{{ shortTime(row.updated_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column v-if="tab === 'pending'" label="等待时长" width="120">
            <template #default="{ row }">
              <AdminStatus kind="warning" :label="waitingDuration(row.updated_at)" />
            </template>
          </el-table-column>
          <el-table-column v-else-if="tab === 'rejected'" label="驳回原因" min-width="180">
            <template #default="{ row }">
              <span class="cell-sub" :title="row.reject_reason || ''">{{ row.reject_reason || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column width="130" fixed="right" align="right">
            <template #default="{ row }">
              <RouterLink
                v-if="tab === 'pending'"
                :to="`/admin/reviews/${row.id}`"
                class="primary-btn-sm"
              >开始审核</RouterLink>
              <RouterLink v-else :to="`/admin/reviews/${row.id}`" class="edit-btn">查看</RouterLink>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ filteredRows.length }} 条{{ tab === 'pending' ? '待审核' : '' }}</span>
        <span class="foot-note">{{ tab === 'pending' ? '默认按提交时间升序' : '' }}</span>
      </div>
    </section>
  </div>
</template>

<script setup>
/**
 * 文章审核队列(05 V2 补充 §2 Review Queue Pattern)
 * 职责:Pending Review 工作队列。列表只提供"开始审核",
 * 不直接通过/驳回——必须进入完整预览(§3)。
 */
import { ref, computed, onMounted } from 'vue';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminTag from '../../components/admin/AdminTag.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const loading = ref(true);
const error = ref(false);
const tab = ref('pending');
const search = ref('');
const topicFilter = ref('');
const sortAsc = ref(true);

/** @type {import('vue').Ref<any[]>} */
const pendingRows = ref([]);
/** @type {import('vue').Ref<any[]>} */
const recentRows = ref([]);
const pendingCount = computed(() => pendingRows.value.length);
const approvedToday = ref(0);
const rejectedToday = ref(0);

/** @type {import('vue').Ref<string>} */
const resultFilter = ref('');

const rowsByTab = computed(() => {
  if (tab.value === 'recent') {
    if (resultFilter.value === 'published') {
      return recentRows.value.filter((/** @type {any} */ r) => r.status === 'published');
    }
    if (resultFilter.value === 'rejected') {
      return recentRows.value.filter((/** @type {any} */ r) => r.status === 'rejected');
    }
    return recentRows.value;
  }
  return pendingRows.value;
});

const topicOptions = computed(() => {
  const set = new Set();
  for (const r of rowsByTab.value) {
    const name = r.category?.name || r.category;
    if (name) set.add(name);
  }
  return [...set];
});

const filteredRows = computed(() => {
  let rows = rowsByTab.value;
  const kw = search.value.trim().toLowerCase();
  if (kw) {
    rows = rows.filter(
      (r) =>
        String(r.title || '').toLowerCase().includes(kw) ||
        String(r.author?.nickname || r.author?.email || '').toLowerCase().includes(kw),
    );
  }
  if (topicFilter.value) {
    rows = rows.filter((r) => (r.category?.name || r.category) === topicFilter.value);
  }
  if (tab.value === 'pending') {
    rows = [...rows].sort((a, b) => {
      const ta = a.updated_at || '';
      const tb = b.updated_at || '';
      return sortAsc.value ? ta.localeCompare(tb) : tb.localeCompare(ta);
    });
  }
  return rows;
});

/** @param {string} t */
/** @param {string} t */
function switchTab(t) {
  tab.value = t;
  search.value = '';
  topicFilter.value = '';
  resultFilter.value = '';
  // pending 数据常驻缓存;其它 Tab 首次进入或刷新时加载
  if (t === 'pending' && pendingRows.value.length) return;
  loadTab();
}

/** @param {string | undefined} t */
function shortTime(t) {
  if (!t) return '—';
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return '—';
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 等待时长:now - 提交时间(updated_at 近似) */
/** @param {string | undefined} t */
function waitingDuration(t) {
  if (!t) return '—';
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return '—';
  const mins = Math.max(1, Math.floor((Date.now() - d.getTime()) / 60000));
  if (mins < 60) return `${mins} 分钟`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时`;
  return `${Math.floor(hours / 24)} 天`;
}

async function loadTab() {
  loading.value = true;
  error.value = false;
  try {
    if (tab.value === 'pending') {
      const r = await API.getArticles({ status: 'pending', page: 1, page_size: 50, sort: 'updated_at:asc' });
      pendingRows.value = r?.data?.data?.list || [];
    } else if (tab.value === 'recent') {
      // 最近处理 = 已通过 + 已退回(两个状态并行拉取后合并,按更新时间倒序)
      const [pub, rej] = await Promise.all([
        API.getArticles({ status: 'published', page: 1, page_size: 20, sort: 'updated_at:desc' }),
        API.getArticles({ status: 'rejected', page: 1, page_size: 20, sort: 'updated_at:desc' }),
      ]);
      const merged = [
        ...(pub?.data?.data?.list || []),
        ...(rej?.data?.data?.list || []),
      ].sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
      recentRows.value = merged;
    }
  } catch (e) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  // 今日统计独立于当前 Tab(切到最近处理/已退回时 summary 仍正确)
  try {
    API.getReviewStats().then((/** @type {any} */ r) => {
      if (r?.data?.code === 0) {
        approvedToday.value = r.data.data.approved_today || 0;
        rejectedToday.value = r.data.data.rejected_today || 0;
      }
    });
  } catch (e) { /* 统计失败静默 */ }
  loadTab();
});
</script>

<style scoped>
.review-queue {
  width: 100%;
}
.review-queue :deep(.admin-toolbar) {
  border-bottom: 0;
}
.review-queue :deep(.el-table) {
  width: 100%;
}

/* Summary(评审修订:两卡收紧为统一 Strip,同一容器 + 内部分隔) */
/* 评审修订:Summary 是紧凑信息组,不与列表等宽(控制在 ~600px) */
.summary-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 300px));
  max-width: 600px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
  margin-bottom: 16px;
}
.sum-card {
  padding: 15px 16px;
  border-right: 1px solid var(--adm-border);
}
.sum-card:last-child {
  border-right: 0;
}
.sum-card label {
  font-size: 12px;
  color: var(--adm-muted);
}
.sum-card strong {
  display: block;
  font-size: 24px;
  margin-top: 5px;
  color: var(--adm-text);
  font-variant-numeric: tabular-nums;
}
.sum-card small {
  font-size: 12px;
  color: var(--adm-muted);
}

/* Tabs(普通 Selected State,无渐变) */
.tabs {
  display: flex;
  gap: 4px;
  width: max-content;
  background: var(--adm-surface);
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 12px;
}
.tab {
  height: 34px;
  border: 0;
  background: transparent;
  border-radius: 7px;
  padding: 0 12px;
  color: var(--adm-muted);
  font-size: 13px;
  cursor: pointer;
}
.tab.active {
  background: var(--adm-primary-soft);
  color: var(--adm-primary);
  font-weight: 650;
}

.adm-select {
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 13px;
  outline: none;
}
.adm-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
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

/* 队列第一列(原型:title 14 + sub 12) */
.cell-title {
  font-size: 14px;
  font-weight: 680;
  color: var(--adm-text);
}
.cell-sub {
  font-size: 12px;
  color: var(--adm-muted);
  margin-top: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cell-text {
  font-size: 12px;
  color: var(--adm-text-2);
  font-variant-numeric: tabular-nums;
}
.cell-muted {
  color: var(--adm-muted-light);
}

.primary-btn-sm {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--adm-primary);
  border-radius: 8px;
  background: var(--adm-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 650;
  text-decoration: none;
  cursor: pointer;
}
.primary-btn-sm:hover {
  opacity: 0.92;
}
.edit-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.edit-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

.table-footer {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 10px 12px;
  border-top: 1px solid var(--adm-border);
  color: var(--adm-muted);
  font-size: 12px;
}
.foot-note {
  font-size: 12px;
  color: var(--adm-muted);
}

@media (max-width: 900px) {
  .summary-row {
    grid-template-columns: 1fr;
  }
}
</style>
