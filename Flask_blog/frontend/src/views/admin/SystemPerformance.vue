<template>
  <div class="performance-page">
    <AdminPageHeader title="性能监控" description="查看应用响应、资源使用和核心依赖健康状态。">
      <span class="freshness">每 10 秒自动刷新<template v-if="lastUpdateTime"> · 更新于 {{ lastUpdateTime }}</template></span>
      <button type="button" class="ghost-btn" :disabled="loading" @click="refreshAll">↻ 刷新</button>
    </AdminPageHeader>

    <!-- Current State:回答「机器现在怎么样」 -->
    <AdminSummaryStrip
      :items="summaryItems"
    />

    <!-- Runtime + Services:「运行状态」层 -->
    <div class="grid-two">
      <section class="card">
        <div class="card-head">
          <h2>运行概览</h2>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row"><label>进程数</label><div>{{ currentStats.process_count || '—' }}</div></div>
            <div class="kv-row"><label>网络流入</label><div>{{ formatNetwork(currentStats.networkIn) }}</div></div>
            <div class="kv-row"><label>网络流出</label><div>{{ formatNetwork(currentStats.networkOut) }}</div></div>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>服务状态</h2>
          <AdminStatus :kind="allServicesOk ? 'success' : 'warning'" :label="allServicesOk ? '全部正常' : '部分异常'" />
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row">
              <label>Web API</label>
              <div class="svc-line">
                <AdminStatus :kind="probes.api ? 'success' : 'danger'" :label="probes.api ? '正常' : '异常'" />
                <span v-if="probes.api && apiLatency != null" class="svc-latency">{{ apiLatency }} ms</span>
              </div>
            </div>
            <div class="kv-row">
              <label>数据库</label>
              <div class="svc-line">
                <AdminStatus :kind="probes.db ? 'success' : 'danger'" :label="probes.db ? '正常' : '异常'" />
                <span v-if="probes.db && dbLatency != null" class="svc-latency">{{ dbLatency }} ms</span>
              </div>
            </div>
            <div class="kv-row">
              <label>媒体存储</label>
              <div class="svc-line">
                <AdminStatus :kind="probes.media ? 'success' : 'warning'" :label="probes.media ? '正常' : '未知'" />
                <span v-if="probes.media && mediaLatency != null" class="svc-latency">{{ mediaLatency }} ms</span>
              </div>
            </div>
          </div>
          <div class="probe-note">状态由页面会话内的真实请求探测得出,每 10 秒更新。</div>
        </div>
      </section>
    </div>

    <!-- 主机信息:低权重单行,静态规格 -->
    <div class="host-line">主机信息　{{ hostSpecLine }}</div>
  </div>
</template>

<script setup>
/**
 * 性能监控(V2 系统页面原型 + 二轮信息分层修订)
 * 分层:顶部 Summary = Current State;运行概览 = Runtime;
 * 主机信息 = Machine Spec(低权重单行);服务状态 = 真实请求探测(+时延)。
 * 数据新鲜度统一到页头右上角(自动刷新说明 + 更新时间 + 刷新按钮)。
 * 无历史采样/P95 接口,不做趋势图;后台任务无队列接口,不伪造状态行。
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';

const loading = ref(false);
const lastUpdateTime = ref('');

const currentStats = reactive({
  cpu: 0,
  memory: 0,
  disk: 0,
  networkIn: 0,
  networkOut: 0,
  uptime_hours: 0,
  process_count: 0,
  memory_total_gb: 0,
  disk_total_gb: 0,
  cpu_count: 0,
  cpu_count_physical: 0,
  cpu_freq: 0
});

// 服务探测结果(页面会话内真实请求,含时延)
const probes = reactive({
  api: false,
  db: false,
  media: false
});
/** @type {import('vue').Ref<number | null>} */
const apiLatency = ref(null);
/** @type {import('vue').Ref<number | null>} */
const dbLatency = ref(null);
/** @type {import('vue').Ref<number | null>} */
const mediaLatency = ref(null);

const allServicesOk = computed(() => probes.api && probes.db && probes.media);

const uptimeText = computed(() => {
  const h = currentStats.uptime_hours || 0;
  if (h < 24) return `${Math.round(h)} 小时`;
  const days = Math.floor(h / 24);
  return days > 365 ? `${(h / 8760).toFixed(1)} 年` : `${days} 天`;
});

// Summary 小字:当前状态补充(非硬件规格)
const cpuNote = computed(() => {
  const c = currentStats.cpu || 0;
  if (c >= 90) return '负载过高';
  if (c >= 70) return '负载偏高';
  return '当前负载正常';
});

const memNote = computed(() => {
  const total = currentStats.memory_total_gb || 0;
  if (!total) return '—';
  const used = (total * (currentStats.memory || 0)) / 100;
  return `已使用 ${used.toFixed(1)} / ${total} GB`;
});

const diskNote = computed(() => {
  const total = currentStats.disk_total_gb || 0;
  if (!total) return '—';
  const used = (total * (currentStats.disk || 0)) / 100;
  return `已使用约 ${Math.round(used)} / ${total} GB`;
});

const startNote = computed(() => {
  const h = currentStats.uptime_hours || 0;
  if (!h) return '—';
  const start = new Date(Date.now() - h * 3600000);
  return `最近启动于 ${start.getMonth() + 1}/${start.getDate()}`;
});

const summaryItems = computed(() => [
  { label: 'CPU 使用率', value: Math.round(currentStats.cpu) + '%', note: cpuNote.value },
  { label: '内存使用率', value: Math.round(currentStats.memory) + '%', note: memNote.value },
  { label: '磁盘使用率', value: Math.round(currentStats.disk) + '%', note: diskNote.value },
  { label: '运行时长', value: uptimeText.value, note: startNote.value },
]);

// 主机信息单行(静态规格,低权重)
const hostSpecLine = computed(() => {
  const parts = [];
  if (currentStats.cpu_count) parts.push(`${currentStats.cpu_count} 核`);
  if (currentStats.cpu_freq) parts.push(`${currentStats.cpu_freq} MHz`);
  if (currentStats.memory_total_gb) parts.push(`${currentStats.memory_total_gb} GB RAM`);
  if (currentStats.disk_total_gb) {
    const tb = currentStats.disk_total_gb / 1024;
    parts.push(tb >= 1 ? `${tb.toFixed(1)} TB Disk` : `${currentStats.disk_total_gb} GB Disk`);
  }
  return parts.join(' · ') || '—';
});

/** @param {number | undefined} kb */
function formatNetwork(kb) {
  if (!kb || kb <= 0) return '—';
  if (kb > 1024 * 1024) return (kb / 1024 / 1024).toFixed(1) + ' GB';
  if (kb > 1024) return (kb / 1024).toFixed(1) + ' MB';
  return Math.round(kb) + ' KB';
}

async function fetchPerformanceData() {
  loading.value = true;
  try {
    const t0 = performance.now();
    const response = await API.getSystemHealth();
    apiLatency.value = Math.round(performance.now() - t0);
    if (response.data.code === 0) {
      Object.assign(currentStats, response.data.data);
      lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN');
      probes.api = true;
    } else {
      probes.api = false;
    }
  } catch (e) {
    probes.api = false;
  } finally {
    loading.value = false;
  }
}

/** 独立探测:数据库(公开文章列表,真实查询 DB)与媒体存储(列表接口),记录时延 */
async function probeDependencies() {
  try {
    const t0 = performance.now();
    const r = await API.getPublicArticles({ page: 1, page_size: 1 });
    dbLatency.value = Math.round(performance.now() - t0);
    probes.db = r?.data?.code === 0;
  } catch (e) {
    probes.db = false;
  }
  try {
    const t0 = performance.now();
    const r = await API.getMediaList({ page: 1, page_size: 1 });
    mediaLatency.value = Math.round(performance.now() - t0);
    probes.media = r?.data?.code === 0 || r?.status === 200;
  } catch (e) {
    probes.media = false;
  }
}

function refreshAll() {
  fetchPerformanceData();
  probeDependencies();
}

/** @type {ReturnType<typeof setInterval> | null} */
let refreshTimer = null;

onMounted(() => {
  refreshAll();
  refreshTimer = setInterval(refreshAll, 10000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.performance-page {
  width: 100%;
}

/* 数据新鲜度:页头右上角统一呈现 */
.freshness {
  font-size: 12px;
  color: var(--adm-muted);
  align-self: center;
}

.ghost-btn {
  height: 34px;
  padding: 0 11px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 13px;
  cursor: pointer;
}
.ghost-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

.grid-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
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

/* 系统概览 KV(仅动态运行数据) */
.kv-list {
  display: grid;
}
.kv-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 14px;
  padding: 11px 0;
  border-top: 1px solid var(--adm-border);
  font-size: 13px;
  color: var(--adm-text-2);
}
.kv-row:first-child {
  border-top: 0;
}
.kv-row label {
  color: var(--adm-muted);
}

/* 服务状态:状态 + 右对齐时延 */
.svc-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.svc-latency {
  font-size: 12px;
  color: var(--adm-muted);
  font-variant-numeric: tabular-nums;
}

.probe-note {
  margin-top: 12px;
  font-size: 12px;
  color: var(--adm-muted);
}

/* 主机信息单行(静态规格,低权重) */
.host-line {
  margin-top: 18px;
  padding: 10px 0 0;
  border-top: 1px solid var(--adm-border);
  font-size: 12px;
  color: var(--adm-muted);
  letter-spacing: 0.01em;
}

@media (max-width: 1000px) {
  .grid-two {
    grid-template-columns: 1fr;
  }
}
</style>
