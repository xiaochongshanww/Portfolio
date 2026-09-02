<template>
  <div class="performance-page">
    <AdminPageHeader title="性能监控" description="查看应用响应、资源使用和核心依赖健康状态。">
      <button type="button" class="ghost-btn" :disabled="loading" @click="fetchPerformanceData">↻ 刷新</button>
    </AdminPageHeader>

    <!-- Summary Strip(「现在怎么样」层;真实字段,无 P95/错误率虚构) -->
    <AdminSummaryStrip
      :items="[
        { label: 'CPU 使用率', value: Math.round(currentStats.cpu) + '%', note: '逻辑核 ' + (currentStats.cpu_count || '—') + ' 核' },
        { label: '内存使用率', value: Math.round(currentStats.memory) + '%', note: '总量 ' + (currentStats.memory_total_gb || '—') + ' GB' },
        { label: '磁盘使用率', value: Math.round(currentStats.disk) + '%', note: '总量 ' + (currentStats.disk_total_gb || '—') + ' GB' },
        { label: '运行时长', value: uptimeText, note: '进程 ' + (currentStats.process_count || '—') + ' 个' },
      ]"
    />

    <!-- Grid2:「机器是什么状态」层:系统概览 + 服务状态(真实探测) -->
    <div class="grid-two">
      <section class="card">
        <div class="card-head">
          <h2>系统概览</h2>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row"><label>CPU 核数</label><div>{{ currentStats.cpu_count || '—' }} 逻辑核（物理 {{ currentStats.cpu_count_physical || '—' }} 核）</div></div>
            <div class="kv-row"><label>CPU 频率</label><div>{{ currentStats.cpu_freq ? currentStats.cpu_freq + ' MHz' : '—' }}</div></div>
            <div class="kv-row"><label>内存总量</label><div>{{ currentStats.memory_total_gb || '—' }} GB</div></div>
            <div class="kv-row"><label>磁盘总量</label><div>{{ currentStats.disk_total_gb || '—' }} GB</div></div>
            <div class="kv-row"><label>进程数</label><div>{{ currentStats.process_count || '—' }}</div></div>
            <div class="kv-row"><label>网络流入</label><div>{{ formatNetwork(currentStats.networkIn) }}</div></div>
            <div class="kv-row"><label>网络流出</label><div>{{ formatNetwork(currentStats.networkOut) }}</div></div>
            <div class="kv-row"><label>最后更新</label><div>{{ lastUpdateTime || '—' }}</div></div>
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
              <div><AdminStatus :kind="probes.api ? 'success' : 'danger'" :label="probes.api ? '正常' : '异常'" /></div>
            </div>
            <div class="kv-row">
              <label>数据库</label>
              <div><AdminStatus :kind="probes.db ? 'success' : 'danger'" :label="probes.db ? '正常' : '异常'" /></div>
            </div>
            <div class="kv-row">
              <label>媒体存储</label>
              <div><AdminStatus :kind="probes.media ? 'success' : 'warning'" :label="probes.media ? '正常' : '未知'" /></div>
            </div>
          </div>
          <div class="probe-note">状态由页面会话内的真实请求探测得出,每 10 秒更新。</div>
        </div>
      </section>
    </div>

    <!-- 自动刷新提示 -->
    <div class="refresh-note">
      数据每 10 秒自动刷新一次;手动刷新请点击右上角按钮。
    </div>
  </div>
</template>

<script setup>
/**
 * 性能监控(V2 系统页面原型 + 评审修订)
 * 修订:消除重复表达——顶部 Summary 只回答「现在怎么样」(CPU/内存/磁盘/时长);
 * 系统概览回答「机器是什么状态」(静态规格 + 进程/网络);
 * 服务状态由页面会话内的真实请求探测派生,不伪造。
 * 无历史采样/P95 接口,不做趋势图;10s 自动轮询保留。
 */
import { ref, reactive, computed, onMounted, onUnmounted, reactive as _reactive } from 'vue';
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

// 服务探测结果(页面会话内真实请求)
const probes = reactive({
  api: false,
  db: false,
  media: false
});

const allServicesOk = computed(() => probes.api && probes.db && probes.media);

const uptimeText = computed(() => {
  const h = currentStats.uptime_hours || 0;
  if (h < 24) return `${Math.round(h)} 小时`;
  const days = Math.floor(h / 24);
  return days > 365 ? `${(h / 8760).toFixed(1)} 年` : `${days} 天`;
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
    const response = await API.getSystemHealth();
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

/** 独立探测:数据库(公开文章列表,真实查询 DB)与媒体存储(列表接口) */
async function probeDependencies() {
  try {
    const r = await API.getPublicArticles({ page: 1, page_size: 1 });
    probes.db = r?.data?.code === 0;
  } catch (e) {
    probes.db = false;
  }
  try {
    const r = await API.getMediaList({ page: 1, page_size: 1 });
    probes.media = r?.data?.code === 0 || r?.status === 200;
  } catch (e) {
    probes.media = false;
  }
}

/** @type {ReturnType<typeof setInterval> | null} */
let refreshTimer = null;

onMounted(() => {
  fetchPerformanceData();
  probeDependencies();
  refreshTimer = setInterval(() => {
    fetchPerformanceData();
    probeDependencies();
  }, 10000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.performance-page {
  width: 100%;
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

/* 系统概览 KV */
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

.probe-note {
  margin-top: 12px;
  font-size: 12px;
  color: var(--adm-muted);
}

.refresh-note {
  margin-top: 18px;
  font-size: 12px;
  color: var(--adm-muted-light);
}

@media (max-width: 1000px) {
  .grid-two {
    grid-template-columns: 1fr;
  }
}
</style>
