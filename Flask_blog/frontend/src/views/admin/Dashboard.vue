<template>
  <div class="dashboard-page">
    <AdminPageHeader title="仪表盘" description="查看内容状态和近期需要处理的事项。" />

    <!-- Metric Row(05 §14:约 4 个,无四色 KPI) -->
    <section class="metric-row">
      <div class="metric">
        <label>文章</label>
        <strong>{{ stats.totalArticles }}</strong>
        <small>待审核 {{ stats.pendingArticles }}</small>
      </div>
      <div class="metric">
        <label>评论</label>
        <strong>{{ commentStats.total }}</strong>
        <small>待处理 {{ commentStats.pending }}</small>
      </div>
      <div class="metric">
        <label>专题</label>
        <strong>{{ topicCount }}</strong>
        <small>长期维护</small>
      </div>
      <div class="metric">
        <label>项目</label>
        <strong>{{ projectCount }}</strong>
        <small>开发中 {{ projectActiveCount }}</small>
      </div>
    </section>

    <!-- Main Grid(05 §13):最近更新 + 待处理 -->
    <div class="grid-two">
      <section class="card">
        <div class="card-head">
          <h2>最近更新</h2>
          <RouterLink to="/admin/articles" class="card-link">查看文章</RouterLink>
        </div>
        <div class="card-body">
          <div v-if="loading" class="card-loading">
            <el-skeleton :rows="3" animated />
          </div>
          <AdminStateBlock
            v-else-if="!recentArticles.length"
            kind="empty"
            title="还没有文章"
            description="发布第一篇文章后会显示在这里。"
            compact
          />
          <div v-else class="kv-list">
            <div v-for="a in recentArticles" :key="a.id" class="kv-row">
              <label>{{ shortDate(a.updated_at || a.created_at) }}</label>
              <div class="kv-main">
                <RouterLink :to="`/article/${a.slug}`" class="kv-title" target="_blank">{{ a.title }}</RouterLink>
                <span class="kv-sub">{{ statusText(a.status) }}<template v-if="a.category"> · {{ a.category.name || a.category }}</template></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>待处理</h2>
        </div>
        <div class="card-body">
          <div v-if="loading" class="card-loading">
            <el-skeleton :rows="3" animated />
          </div>
          <AdminStateBlock
            v-else-if="!todoItems.length"
            kind="empty"
            title="暂无待办事项"
            description="当前没有需要处理的内容。"
            compact
          />
          <div v-else class="kv-list">
            <div v-for="t in todoItems" :key="t.label + t.value" class="kv-row">
              <label>{{ t.label }}</label>
              <div class="kv-main">
                <RouterLink :to="t.to" class="kv-title">{{ t.value }}</RouterLink>
                <span class="kv-sub">{{ t.note }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 内容概览 + 快速操作 -->
    <div class="grid-two grid-gap-top">
      <section class="card">
        <div class="card-head">
          <h2>内容概览</h2>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row"><label>已发布</label><div class="kv-plain">{{ stats.publishedArticles }} 篇</div></div>
            <div class="kv-row"><label>草稿与待审</label><div class="kv-plain">{{ draftPendingCount }} 篇</div></div>
            <div class="kv-row"><label>未使用标签</label><div class="kv-plain">{{ unusedTagCount }} 个</div></div>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>快速操作</h2>
        </div>
        <div class="card-body quick-actions">
          <RouterLink to="/articles/new" class="quick-btn primary">＋ 新建文章</RouterLink>
          <RouterLink to="/admin/media" class="quick-btn">上传媒体</RouterLink>
          <RouterLink to="/admin/categories" class="quick-btn">新建专题</RouterLink>
          <RouterLink to="/admin/projects" class="quick-btn">新建项目</RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
/**
 * 仪表盘(05 §13/§14 Dashboard Pattern):回答"现在有什么需要处理/最近发生了什么",
 * 不是"能放多少图表"。按角色可见范围加载(admin/editor 全量,author 本人)。
 */
import { ref, reactive, computed, onMounted } from 'vue';
import { useUserStore } from '../../stores/user';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const userStore = useUserStore();
const loading = ref(true);

const stats = reactive({
  totalArticles: 0,
  pendingArticles: 0,
  publishedArticles: 0,
});

const commentStats = reactive({ total: 0, pending: 0 });
/** @type {import('vue').Ref<any[]>} */
const recentArticles = ref([]);
/** @type {import('vue').Ref<any[]>} */
const topics = ref([]);
/** @type {import('vue').Ref<any[]>} */
const projects = ref([]);
const unusedTagCount = ref(0);

const topicCount = computed(() => topics.value.length);
const projectCount = computed(() => projects.value.length);
const projectActiveCount = computed(() => projects.value.filter((p) => p.status === 'active').length);
const draftPendingCount = computed(
  () => stats.totalArticles - stats.publishedArticles,
);

/** 待处理清单(05 §13:可点击直达) */
const todoItems = computed(() => {
  /** @type {Array<{label:string, value:string, note:string, to:string}>} */
  const list = [];
  if (stats.pendingArticles > 0 && userStore.canModerateContent) {
    list.push({
      label: '文章审核',
      value: `${stats.pendingArticles} 篇待审核`,
      note: '点击进入文章列表',
      to: '/admin/articles',
    });
  }
  if (commentStats.pending > 0) {
    list.push({
      label: '评论审核',
      value: `${commentStats.pending} 条待处理`,
      note: '来自评论管理',
      to: '/admin/comments',
    });
  }
  if (unusedTagCount.value > 0) {
    list.push({
      label: '标签清理',
      value: `${unusedTagCount.value} 个未使用`,
      note: '可考虑清理',
      to: '/admin/tags',
    });
  }
  return list;
});

/** @param {string} s */
function shortDate(s) {
  if (!s) return '';
  return String(s).slice(5, 10).replace('-', '/');
}

/** @param {string | undefined} status */
function statusText(status) {
  switch (status) {
    case 'published': return '已发布';
    case 'pending': return '待审核';
    case 'draft': return '草稿';
    case 'rejected': return '已拒绝';
    default: return status || '';
  }
}

/** 全部 settle,单项失败不拖垮仪表盘
 * @param {Promise<any>} promise
 */
async function safe(promise) {
  try {
    return await promise;
  } catch (e) {
    return null;
  }
}

async function loadDashboardData() {
  loading.value = true;
  const isAuthor = userStore.user?.role === 'author';
  const canModerate = userStore.canModerateContent;
  const userId = userStore.user?.id;

  const authorParams = isAuthor ? { author_id: userId } : {};

  await Promise.all([
    // 文章计数
    safe(API.getArticles({ page: 1, page_size: 1, ...authorParams })).then((r) => {
      stats.totalArticles = r?.data?.data?.total || 0;
    }),
    safe(API.getArticles({ page: 1, page_size: 1, status: 'pending', ...authorParams })).then((r) => {
      stats.pendingArticles = r?.data?.data?.total || 0;
    }),
    safe(API.getPublicArticles({ page: 1, page_size: 1, ...authorParams })).then((r) => {
      stats.publishedArticles = r?.data?.data?.total || 0;
    }),
    // 最近更新
    safe(API.getArticles({ page: 1, page_size: 5, sort: 'created_at:desc', ...authorParams })).then((r) => {
      recentArticles.value = r?.data?.data?.list || [];
    }),
    // 评论计数(editor/admin)
    canModerate
      ? safe(API.getCommentStats()).then((r) => {
          if (r?.data?.code === 0) {
            commentStats.total = r.data.data.total || 0;
            commentStats.pending = r.data.data.pending || 0;
          }
        })
      : Promise.resolve(),
    // 专题/项目(editor/admin 可管理场景;author 静默跳过)
    safe(API.getPublicTaxonomy()).then((r) => {
      topics.value = r?.data?.data?.categories || [];
    }),
    safe(API.getPublicProjects()).then((r) => {
      projects.value = r?.data?.data?.list || [];
    }),
    // 未使用标签(editor/admin)
    safe(API.getTaxonomyStats()).then((r) => {
      if (r?.data?.code === 0) {
        unusedTagCount.value = r.data.data?.summary?.unused_tags || 0;
      }
    }),
  ]);

  loading.value = false;
}

onMounted(() => {
  loadDashboardData();
});
</script>

<style scoped>
.dashboard-page {
  width: 100%;
}

/* Metric Row(原型 metricRow) */
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.metric {
  padding: 15px;
  border: 1px solid var(--adm-border);
  border-radius: 11px;
  background: var(--adm-surface);
}
.metric label {
  font-size: 11px;
  color: var(--adm-muted);
}
.metric strong {
  display: block;
  margin-top: 5px;
  font-size: 20px;
  letter-spacing: -0.03em;
  color: var(--adm-text);
  font-variant-numeric: tabular-nums;
}
.metric small {
  font-size: 10px;
  color: var(--adm-muted-light);
}

/* 卡片栅格(原型 two) */
.grid-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.grid-gap-top {
  margin-top: 16px;
}
.card {
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
}
.card-head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--adm-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.card-head h2 {
  font-size: 13px;
  margin: 0;
  color: var(--adm-text);
}
.card-link {
  font-size: 12px;
  color: var(--adm-muted);
}
.card-link:hover {
  color: var(--adm-primary);
}
.card-body {
  padding: 16px;
}
.card-loading {
  padding: 4px 0;
}

/* KV 行(原型 kv) */
.kv-list {
  display: grid;
}
.kv-row {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 14px;
  padding: 11px 0;
  border-top: 1px solid var(--adm-border);
}
.kv-row:first-child {
  border-top: 0;
  padding-top: 2px;
}
.kv-row label {
  font-size: 12px;
  color: var(--adm-muted);
}
.kv-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.kv-title {
  font-size: 13px;
  font-weight: 650;
  color: var(--adm-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
a.kv-title:hover {
  color: var(--adm-primary);
}
.kv-sub {
  font-size: 11px;
  color: var(--adm-muted);
}
.kv-plain {
  font-size: 12px;
  color: var(--adm-text-2);
}

/* 快速操作 */
.quick-actions {
  display: grid;
  gap: 8px;
}
.quick-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  text-decoration: none;
  cursor: pointer;
}
.quick-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}
.quick-btn.primary {
  background: var(--adm-primary);
  border-color: var(--adm-primary);
  color: #fff;
  font-weight: 650;
}
.quick-btn.primary:hover {
  opacity: 0.92;
  color: #fff;
}

@media (max-width: 950px) {
  .metric-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .grid-two {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 719.98px) {
  .metric-row {
    grid-template-columns: 1fr;
  }
}
</style>
