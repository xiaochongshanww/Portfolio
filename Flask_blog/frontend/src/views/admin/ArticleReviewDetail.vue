<template>
  <div class="review-detail">
    <!-- Head(原型:标题 + 返回队列) -->
    <section class="page-head">
      <div>
        <h1>审核文章</h1>
        <p>阅读完整内容并决定是否允许发布。</p>
      </div>
      <RouterLink to="/admin/reviews" class="back-link">← 返回审核队列</RouterLink>
    </section>

    <!-- loading -->
    <AdminStateBlock v-if="loading" kind="empty" title="加载中…" compact />

    <!-- error / 404 -->
    <AdminStateBlock
      v-else-if="notFound"
      kind="error"
      title="没有找到这篇文章"
      description="它可能已被删除,或不在审核队列中。"
      compact
      @reload="load"
    />
    <AdminStateBlock v-else-if="error" kind="error" title="文章加载失败" compact @reload="load" />

    <!-- Review 双栏(05 V2 补充 §4:预览 | 面板 360px) -->
    <div v-else-if="article" class="review-grid">
      <!-- Article Preview:复用 ArticleRenderer 渲染管线 -->
      <section class="card">
        <div class="card-head">
          <h2>文章预览</h2>
          <AdminStatus
            :kind="statusKind(article.status)"
            :label="statusText(article.status)"
          />
        </div>
        <div class="card-body">
          <article class="article-preview">
            <div class="topic">{{ article.category?.name || article.category || '' }}</div>
            <h2 class="a-title">{{ article.title }}</h2>
            <p v-if="article.summary" class="deck">{{ article.summary }}</p>
            <ArticleRenderer v-if="previewBlocks.length" :blocks="previewBlocks" />
            <!-- content_html 回退(存量文章无 content_md) -->
            <div v-else-if="article.content_html" class="html-fallback" v-html="article.content_html" />
            <p v-else class="no-content">这篇文章没有正文内容。</p>
          </article>
        </div>
      </section>

      <!-- Review Panel(360px sticky) -->
      <aside class="card panel">
        <div class="card-head">
          <h2>审核信息</h2>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row"><label>状态</label><div><AdminStatus :kind="statusKind(article.status)" :label="statusText(article.status)" /></div></div>
            <div class="kv-row"><label>提交人</label><div>{{ article.author?.nickname || article.author?.email || '—' }}</div></div>
            <div class="kv-row"><label>专题</label><div><AdminTag v-if="article.category" :label="article.category.name || article.category" tone="blue" bordered /><span v-else>—</span></div></div>
            <div class="kv-row"><label>标签</label><div class="tag-wrap"><AdminTag v-for="t in tagList" :key="t" :label="t" /></div></div>
            <div class="kv-row"><label>提交时间</label><div>{{ formatFull(article.updated_at) }}</div></div>
            <div class="kv-row"><label>最后更新</label><div>{{ formatFull(article.updated_at) }}</div></div>
          </div>

          <!-- 审核历史(getAuditLogs:action/actor/time/note,不可覆盖) -->
          <div class="history-title">审核历史</div>
          <div v-if="history.length" class="history-list">
            <div v-for="(h, i) in history" :key="i" class="history-item">
              <b>{{ historyActionText(h.action) }}</b>
              <span>{{ historyActor(h) }} · {{ formatFull(h.created_at) }}</span>
              <span v-if="h.note" class="history-note">{{ h.note }}</span>
            </div>
          </div>
          <div v-else class="history-empty">暂无审核记录。</div>

          <div class="review-note">审核应基于完整文章内容,而不是只根据标题或摘要直接通过。</div>

          <!-- 主动作(仅待审核可操作) -->
          <div v-if="article.status === 'pending'" class="actions">
            <el-button type="danger" @click="rejectVisible = true">驳回</el-button>
            <el-button type="success" @click="approve">通过并发布</el-button>
          </div>
          <div v-else class="actions-done">
            {{ article.status === 'published' ? '该文章已通过并发布。' : '该文章已被驳回,等待作者修改后重新提交。' }}
          </div>
        </div>
      </aside>
    </div>

    <!-- 驳回 Dialog(05 V2 补充 §5) -->
    <RejectArticleDialog
      :visible="rejectVisible"
      :loading="rejecting"
      @update:visible="rejectVisible = $event"
      @confirm="confirmReject"
    />
  </div>
</template>

<script setup>
/**
 * 审核详情(05 V2 补充 §4 Review Detail Pattern)
 * - 预览复用 blocksFromMarkdown → ArticleRenderer(公开站同一渲染管线);
 * - 面板:状态/提交人/专题/标签/时间/审核历史;
 * - 通过=发布(明确确认),驳回=原因+意见(RejectArticleDialog);
 * - 版本说明(§10):面板展示最后更新时间供审核者对照;
 *   ReviewRequest/版本绑定留待后端实体化(规格长期建议)。
 */
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { blocksFromMarkdown } from '../../utils/blocksFromMarkdown';
import ArticleRenderer from '../../components/article/ArticleRenderer.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminTag from '../../components/admin/AdminTag.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';
import RejectArticleDialog from '../../components/admin/RejectArticleDialog.vue';


const route = useRoute();
const router = useRouter();

const loading = ref(true);
const error = ref(false);
const notFound = ref(false);
/** @type {import('vue').Ref<any>} */
const article = ref(null);
/** @type {import('vue').Ref<any[]>} */
const previewBlocks = ref([]);
/** @type {import('vue').Ref<any[]>} */
const history = ref([]);
const rejectVisible = ref(false);
const rejecting = ref(false);

const tagList = computed(() => {
  const t = article.value?.tags;
  if (!Array.isArray(t)) return [];
  return t.map((x) => (typeof x === 'string' ? x : x?.name)).filter(Boolean);
});

/** @param {string | undefined} status @returns {'success'|'warning'|'neutral'|'danger'} */
function statusKind(status) {
  switch (status) {
    case 'published': return 'success';
    case 'pending': return 'warning';
    case 'rejected': return 'danger';
    default: return 'neutral';
  }
}

/** @param {string | undefined} status */
function statusText(status) {
  switch (status) {
    case 'published': return '已发布';
    case 'pending': return '待审核';
    case 'rejected': return '已退回';
    case 'draft': return '草稿';
    default: return status || '未知';
  }
}

/** @param {string | undefined} action */
function historyActionText(action) {
  /** @type {Record<string, string>} */
  const names = {
    submit: '提交审核',
    approve: '审核通过',
    reject: '驳回',
    resubmit: '重新提交',
    create: '创建文章',
    update: '更新文章',
  };
  return names[action || ''] || action || '操作';
}

/** @param {any} h */
function historyActor(h) {
  return h.operator_name || h.operator || `用户 #${h.operator_id ?? '—'}`;
}

/** @param {string | undefined} t */
function formatFull(t) {
  if (!t) return '—';
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return String(t);
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function load() {
  const id = route.params.reviewId;
  loading.value = true;
  error.value = false;
  notFound.value = false;
  try {
    const resp = await API.getArticle(Number(id));
    article.value = resp?.data?.data || null;
    if (!article.value) {
      notFound.value = true;
      return;
    }
    // 预览渲染:优先 Markdown 管线,html 回退
    const md = article.value.content_md;
    if (md) {
      try {
        previewBlocks.value = blocksFromMarkdown(md);
      } catch (e) {
        previewBlocks.value = [];
      }
    }
    // 审核历史(失败静默,不阻塞预览)
    try {
      const hResp = await API.getAuditLogs(article.value.id);
      history.value = hResp?.data?.data || [];
    } catch (e) {
      history.value = [];
    }
  } catch (e) {
    const status = /** @type {{response?: {status?: number}}} */ (e)?.response?.status;
    if (status === 404) notFound.value = true;
    else error.value = true;
  } finally {
    loading.value = false;
  }
}

async function approve() {
  if (!article.value) return;
  try {
    await ElMessageBox.confirm(
      `通过并发布「${article.value.title}」？文章将立即在公开站可访问。`,
      '通过并发布',
      { type: 'warning', confirmButtonText: '通过并发布', cancelButtonText: '取消' },
    );
    await API.approveArticle(article.value.id);
    ElMessage.success('文章已通过并发布');
    await load();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败');
  }
}

/** @param {string} reason */
async function confirmReject(reason) {
  if (!article.value) return;
  rejecting.value = true;
  try {
    await API.rejectArticle(article.value.id, { reason });
    ElMessage.success('文章已驳回');
    rejectVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error('驳回失败');
  } finally {
    rejecting.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.review-detail {
  width: 100%;
}

/* Head(原型) */
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}
.page-head h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.04em;
  color: var(--adm-text);
}
.page-head p {
  margin: 8px 0 0;
  color: var(--adm-muted);
  font-size: 14px;
}
.back-link {
  height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 11px;
  border: 1px solid var(--adm-border);
  border-radius: 8px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 13px;
  text-decoration: none;
}
.back-link:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

/* 双栏(§4:预览 | 360px 面板) */
.review-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
}
.card {
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
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
  font-size: 14px;
  margin: 0;
  color: var(--adm-text);
}
.card-body {
  padding: 16px;
}

/* 文章预览(原型 .article) */
.article-preview {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 10px 36px;
}
.article-preview .topic {
  font-size: 13px;
  color: var(--adm-primary);
  font-weight: 650;
}
.a-title {
  font-size: 34px;
  line-height: 1.2;
  letter-spacing: -0.04em;
  margin: 10px 0 12px;
  color: var(--adm-text);
}
.deck {
  font-size: 16px;
  color: var(--adm-muted);
  line-height: 1.7;
  margin-bottom: 24px;
}
.html-fallback {
  font-size: 15px;
  line-height: 1.9;
  color: var(--adm-text-2);
  overflow-wrap: break-word;
}
.no-content {
  color: var(--adm-muted);
  font-size: 13px;
  text-align: center;
  padding: 30px 0;
}
/* ArticleRenderer 消费 admin token 下的文字色 */
.article-preview :deep(.para-block) {
  color: var(--adm-text-2);
}
.article-preview :deep(.heading-block) {
  color: var(--adm-text);
}
.article-preview :deep(.cell-text) {
  color: var(--adm-text-2);
}

/* Panel(原型 sticky) */
.panel {
  position: sticky;
  top: 80px;
}
.kv-list {
  display: grid;
}
.kv-row {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 12px;
  padding: 11px 0;
  border-top: 1px solid var(--adm-border);
  font-size: 12px;
  color: var(--adm-text-2);
}
.kv-row:first-child {
  border-top: 0;
}
.kv-row label {
  color: var(--adm-muted);
}
.tag-wrap {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

/* 审核历史(§8:不可覆盖) */
.history-title {
  margin-top: 16px;
  font-size: 12px;
  font-weight: 650;
  color: var(--adm-text-2);
}
.history-list {
  display: grid;
}
.history-item {
  border-top: 1px solid var(--adm-border);
  padding: 11px 0;
  font-size: 12px;
  color: var(--adm-text-2);
}
.history-item b {
  display: block;
  font-size: 12px;
  color: var(--adm-text);
}
.history-item span {
  display: block;
  color: var(--adm-muted);
  font-size: 11px;
  margin-top: 4px;
}
.history-item .history-note {
  color: var(--adm-text-2);
  line-height: 1.6;
}
.history-empty {
  padding: 10px 0;
  font-size: 12px;
  color: var(--adm-muted);
}

.review-note {
  margin-top: 12px;
  padding: 11px;
  border: 1px solid var(--adm-border);
  border-radius: 8px;
  background: var(--adm-surface-subtle);
  color: var(--adm-muted);
  font-size: 12px;
  line-height: 1.6;
}

/* 动作(§6:通过明确=发布) */
.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 14px;
}
.actions-done {
  margin-top: 14px;
  padding: 11px;
  border-radius: 8px;
  background: var(--adm-surface-subtle);
  color: var(--adm-muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1000px) {
  .review-grid {
    grid-template-columns: 1fr;
  }
  .panel {
    position: static;
  }
}
</style>
