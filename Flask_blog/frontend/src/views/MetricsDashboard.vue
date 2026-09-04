<template>
  <div class="metrics-dashboard">
    <AdminPageHeader title="站点数据看板" description="查看内容、评论与社区的总量和待处理事项。">
      <el-button :loading="loading" @click="() => fetchStats()">↻ 刷新</el-button>
    </AdminPageHeader>

    <!-- 加载骨架 -->
    <section v-if="loading" class="card">
      <div class="card-body state-body">
        <el-skeleton :rows="5" animated />
      </div>
    </section>

    <!-- 错误态(05 §31:统一形态,提供 reload) -->
    <template v-else-if="error">
      <AdminStateBlock
        kind="error"
        title="数据加载失败"
        :description="error + '。请确认后端服务运行中,且账号具备 editor/admin 权限。'"
        @reload="() => fetchStats()"
      >
        <el-button size="small" @click="() => fetchStats(999)">使用备用数据源</el-button>
      </AdminStateBlock>
    </template>

    <template v-else>
      <!-- 总量条(04 §14:同一容器+内部分隔,无彩色无图标) -->
      <AdminSummaryStrip :items="summaryItems" />

      <div class="grid">
        <!-- 待处理 -->
        <section class="card">
          <div class="card-head">
            <h2>待处理</h2>
            <router-link class="head-link" to="/admin/reviews">审核队列 →</router-link>
          </div>
          <div class="card-body">
            <div v-if="queueEmpty" class="queue-empty">
              <AdminStatus kind="success" label="全部处理完毕" />
              <p>没有待审核的文章或评论。</p>
            </div>
            <template v-else>
              <div class="queue-row">
                <div>
                  <b>待审核文章</b>
                  <small>提交后进入审核队列</small>
                </div>
                <div class="queue-side">
                  <AdminStatus
                    :kind="stats.articles.pending > 0 ? 'warning' : 'success'"
                    :label="stats.articles.pending > 0 ? `${stats.articles.pending} 篇待审` : '暂无待审'"
                  />
                  <router-link class="row-link" to="/admin/reviews">去处理 →</router-link>
                </div>
              </div>
              <div class="queue-row">
                <div>
                  <b>待审核评论</b>
                  <small>来自公开文章的读者评论</small>
                </div>
                <div class="queue-side">
                  <AdminStatus
                    :kind="stats.comments.pending > 0 ? 'warning' : 'success'"
                    :label="stats.comments.pending > 0 ? `${stats.comments.pending} 条待审` : '暂无待审'"
                  />
                  <router-link class="row-link" to="/admin/comments">去处理 →</router-link>
                </div>
              </div>
            </template>
          </div>
        </section>

        <!-- 内容构成 -->
        <section class="card">
          <div class="card-head">
            <h2>内容构成</h2>
          </div>
          <div class="card-body">
            <div class="kv-list">
              <div class="kv-row">
                <label>已发布文章</label>
                <span class="kv-value">{{ stats.articles.published }} 篇</span>
              </div>
              <div class="kv-row">
                <label>草稿</label>
                <span class="kv-value">{{ stats.articles.draft }} 篇</span>
              </div>
              <div class="kv-row">
                <label>已批准评论</label>
                <span class="kv-value">{{ stats.comments.approved }} 条</span>
              </div>
              <div class="kv-row">
                <label>标签</label>
                <span class="kv-value">{{ stats.taxonomy.tags }} 个</span>
              </div>
              <div class="kv-row">
                <label>注册用户</label>
                <span class="kv-value">{{ stats.users.total }} 人</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * 站点数据看板(A4 决策:Pattern 化保留,Dashboard/Status Cards)
 * AdminPageHeader + AdminSummaryStrip(总量)+ 待处理队列 + 内容构成;
 * 数据面保持原状:API.getMetricsSummary(10s 超时、网络错误自动重试 ×2、备用数据源)。
 */
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import AdminPageHeader from '../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../components/admin/AdminSummaryStrip.vue';
import AdminStatus from '../components/admin/AdminStatus.vue';
import AdminStateBlock from '../components/admin/AdminStateBlock.vue';
import { API } from '../api';
import { setMeta } from '../composables/useMeta';

const loading = ref(true);
/** @type {import('vue').Ref<string | null>} */
const error = ref(null);
const stats = ref({
  articles: { total: 0, published: 0, draft: 0, pending: 0 },
  comments: { total: 0, pending: 0, approved: 0 },
  users: { total: 0 },
  taxonomy: { tags: 0, categories: 0 },
});

const summaryItems = computed(() => [
  {
    label: '文章',
    value: stats.value.articles.total,
    note: `草稿 ${stats.value.articles.draft} · 待审核 ${stats.value.articles.pending}`,
    to: '/admin/articles',
  },
  {
    label: '评论',
    value: stats.value.comments.total,
    note: `待处理 ${stats.value.comments.pending}`,
    to: '/admin/comments',
  },
  {
    label: '分类',
    value: stats.value.taxonomy.categories,
    note: `标签 ${stats.value.taxonomy.tags} 个`,
    to: '/admin/categories',
  },
  {
    label: '用户',
    value: stats.value.users.total,
    note: '注册用户',
    to: '/admin/users',
  },
]);

const queueEmpty = computed(
  () => stats.value.articles.pending === 0 && stats.value.comments.pending === 0,
);

const api = {
  getSummary: () => API.getMetricsSummary(),
  getTest: () => API.getMetricsTest(),
  getFallbackStats: async () => {
    // 备用方案：从多个简单API获取基础数据
    try {
      const [articles, categories] = await Promise.all([
        API.getPublicV1('/articles?per_page=1').catch(() => ({ data: { data: [] } })),
        API.getPublicV1('/categories').catch(() => ({ data: { data: [] } }))
      ]);

      return {
        data: {
          code: 0,
          data: {
            users: { total: 0 },
            articles: {
              total: articles.data.data?.length || 0,
              published: articles.data.data?.length || 0,
              draft: 0,
              pending: 0
            },
            comments: { total: 0, pending: 0, approved: 0 },
            taxonomy: {
              tags: 0,
              categories: categories.data.data?.length || 0
            }
          }
        }
      };
    } catch (err) {
      throw new Error('备用数据源也无法访问');
    }
  }
};

const fetchStats = async (retryCount = 0) => {
  loading.value = true;
  error.value = null;

  try {
    // 设置超时时间为10秒
    const response = await Promise.race([
      api.getSummary(),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('请求超时')), 10000)
      )
    ]);

    if (response.data.code === 0) {
      stats.value = response.data.data;
      ElMessage.success('数据加载完成');
    } else {
      throw new Error(response.data.message || '服务器返回错误');
    }

  } catch (err) {
    const e = /** @type {{ message?: string, code?: string, response?: { status?: number, data?: { message?: string } } }} */ (err);

    // 根据错误类型提供不同的错误信息
    let errorMsg = '加载数据失败';

    if (e.message === '请求超时') {
      errorMsg = '服务器响应超时，请检查后端服务是否正常运行';
    } else if (e.code === 'NETWORK_ERROR' || e.message?.includes('Network Error')) {
      errorMsg = '网络连接失败，请检查后端服务连接';
    } else if (e.response?.status === 403) {
      errorMsg = '没有权限访问数据，请确保您有editor或admin权限';
    } else if (e.response?.status === 401) {
      errorMsg = '身份验证失败，请重新登录';
    } else if (e.response?.data?.message) {
      errorMsg = e.response.data.message;
    } else if (e.message) {
      errorMsg = e.message;
    }

    error.value = errorMsg;

    // 如果是网络问题且重试次数少于2次，自动重试
    if ((e.message === '请求超时' || e.code === 'NETWORK_ERROR') && retryCount < 2) {
      ElMessage.warning(`连接失败，正在重试... (${retryCount + 1}/2)`);

      setTimeout(() => {
        fetchStats(retryCount + 1);
      }, 2000 * (retryCount + 1)); // 递增延迟
    } else if (retryCount >= 2) {
      // 重试失败后尝试备用数据源
      ElMessage.info('主数据源不可用，正在尝试备用数据源...');

      try {
        const fallbackResponse = await api.getFallbackStats();
        stats.value = fallbackResponse.data.data;
        ElMessage.success('已使用备用数据源加载基础数据');
        error.value = null; // 清除错误状态
      } catch (fallbackErr) {
        error.value = '主数据源和备用数据源均不可用，请检查网络连接或联系管理员';
        ElMessage.error('所有数据源均不可用');
      }
    } else {
      ElMessage.error(errorMsg);
    }

  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  setMeta({
    title: '站点数据看板',
    description: '实时监控站点各项指标和运行状态'
  });
  fetchStats();
});
</script>

<style scoped>
.metrics-dashboard {
  width: 100%;
}

/* 卡片(同后台其他页的统一卡形) */
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
.head-link {
  font-size: 12px;
  color: var(--adm-muted);
}
.head-link:hover {
  color: var(--adm-primary);
}
.card-body {
  padding: 6px 16px 12px;
}
.state-body {
  padding: 16px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

/* 待处理队列行 */
.queue-empty {
  padding: 14px 0;
}
.queue-empty p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--adm-muted);
}
.queue-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 13px 0;
  border-top: 1px solid var(--adm-border);
}
.queue-row:first-of-type {
  border-top: 0;
}
.queue-row b {
  display: block;
  font-size: 13px;
  font-weight: 650;
  color: var(--adm-text);
}
.queue-row small {
  display: block;
  margin-top: 3px;
  font-size: 12px;
  color: var(--adm-muted);
}
.queue-side {
  display: flex;
  align-items: center;
  gap: 14px;
}
.row-link {
  font-size: 12px;
  color: var(--adm-muted);
}
.row-link:hover {
  color: var(--adm-primary);
}

/* 内容构成 KV */
.kv-list {
  display: grid;
}
.kv-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 11px 0;
  border-top: 1px solid var(--adm-border);
}
.kv-row:first-child {
  border-top: 0;
}
.kv-row label {
  font-size: 12px;
  color: var(--adm-muted);
}
.kv-value {
  font-size: 13px;
  font-weight: 650;
  color: var(--adm-text);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1050px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
