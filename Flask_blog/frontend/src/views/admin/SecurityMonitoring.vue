<template>
  <div class="security-center">
    <AdminPageHeader title="安全中心" description="查看账户、会话和后台访问安全状态。" />

    <!-- 05 §21 Status Cards Pattern:快速判断 正常/需要处理 -->
    <div class="grid-two">
      <!-- 安全状态 -->
      <section class="card">
        <div class="card-head">
          <h2>安全状态</h2>
          <AdminStatus :kind="overallKind" :label="overallText" />
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row"><label>今日事件</label><div class="kv-plain">{{ securityStats.todayEvents }} 次</div></div>
            <div class="kv-row"><label>失败登录</label><div class="kv-plain">{{ securityStats.blockedToday }} 次 / 24h</div></div>
            <div class="kv-row"><label>可疑访问</label><div class="kv-plain">{{ accessStats.suspiciousVisits }} 次</div></div>
            <div class="kv-row"><label>已拦截请求</label><div class="kv-plain">{{ accessStats.blockedRequests }} 次</div></div>
          </div>
        </div>
      </section>

      <!-- 登录与访问 -->
      <section class="card">
        <div class="card-head">
          <h2>访问概览</h2>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row"><label>总访问</label><div class="kv-plain">{{ accessStats.totalVisits }}</div></div>
            <div class="kv-row"><label>独立 IP</label><div class="kv-plain">{{ accessStats.uniqueIPs }}</div></div>
            <div class="kv-row"><label>运行时长</label><div class="kv-plain">{{ uptimeText }}</div></div>
            <div class="kv-row"><label>CPU / 内存</label><div class="kv-plain">{{ systemHealth.cpu }}% / {{ systemHealth.memory }}%</div></div>
          </div>
        </div>
      </section>
    </div>

    <!-- 最近安全事件 -->
    <section class="card event-card">
      <div class="card-head">
        <h2>最近安全事件</h2>
        <button type="button" class="ghost-btn" @click="refreshData">↻ 刷新</button>
      </div>
      <div class="card-body">
        <AdminStateBlock
          v-if="error"
          kind="error"
          title="安全数据加载失败"
          compact
          @reload="refreshData"
        />
        <AdminStateBlock
          v-else-if="!loading && !recentEvents.length"
          kind="empty"
          title="暂无异常事件"
          description="当前没有需要处理的安全事件。"
          compact
        />
        <div v-else class="table-wrap">
          <el-table :data="recentEvents" row-key="id" class="adm-table">
            <el-table-column label="时间" width="140">
              <template #default="{ row }">
                <span class="cell-text">{{ formatDateTime(row.timestamp) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="130">
              <template #default="{ row }">
                <AdminTag :label="getEventTypeName(row.type)" :tone="eventTypeTone(row.type)" />
              </template>
            </el-table-column>
            <el-table-column label="级别" width="96">
              <template #default="{ row }">
                <AdminStatus :kind="severityKind(row.severity)" :label="getSeverityName(row.severity)" />
              </template>
            </el-table-column>
            <el-table-column prop="source_ip" label="源 IP" width="130" show-overflow-tooltip />
            <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
            <el-table-column width="120" fixed="right" align="right">
              <template #default="{ row }">
                <div class="row-actions-inline">
                  <button type="button" class="edit-btn" @click="viewEventDetail(row)">详情</button>
                  <el-dropdown trigger="click" placement="bottom-end" :width="160">
                    <button type="button" class="more-btn" :aria-label="`事件操作:${row.id}`">···</button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item v-if="!row.handled" divided @click="handleEvent(row)">标记已处理</el-dropdown-item>
                        <el-dropdown-item v-else disabled>已处理</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </section>

    <!-- 事件详情 Drawer(05 §27) -->
    <el-drawer v-model="eventDetailVisible" title="安全事件详情" size="440px">
      <div v-if="selectedEvent" class="detail-body">
        <div class="kv-row"><label>事件 ID</label><div>{{ selectedEvent.id }}</div></div>
        <div class="kv-row"><label>时间</label><div>{{ formatDateTime(selectedEvent.timestamp) }}</div></div>
        <div class="kv-row"><label>类型</label><div>{{ getEventTypeName(selectedEvent.type) }}</div></div>
        <div class="kv-row"><label>级别</label><div>{{ getSeverityName(selectedEvent.severity) }}</div></div>
        <div class="kv-row"><label>源 IP</label><div>{{ selectedEvent.source_ip || '—' }}</div></div>
        <div class="kv-row"><label>描述</label><div>{{ selectedEvent.description }}</div></div>
        <div class="kv-row"><label>状态</label><div>{{ selectedEvent.handled ? '已处理' : '待处理' }}</div></div>
      </div>
      <template #footer>
        <el-button
          v-if="selectedEvent && !selectedEvent.handled"
          type="danger"
          @click="handleEvent(selectedEvent)"
        >标记已处理</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
/**
 * 安全中心(05 §21 Status Cards Pattern):不是普通 Table 页。
 * 保留:真实 API(health/stats/events/access) + 降级链,事件处理。
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminTag from '../../components/admin/AdminTag.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const loading = ref(false);
const error = ref(false);

const securityStats = reactive({
  todayEvents: 0,
  eventsTrend: 0,
  blockedAttacks: 0,
  blockedToday: 0,
  anomalousUsers: 0,
  userTrend: 0,
});

const systemHealth = reactive({
  cpu: 0,
  memory: 0,
  disk: 0,
  uptime_hours: 0,
});

const accessStats = reactive({
  totalVisits: 0,
  uniqueIPs: 0,
  suspiciousVisits: 0,
  blockedRequests: 0,
});

/** @type {import('vue').Ref<any[]>} */
const recentEvents = ref([]);
/** @type {import('vue').Ref<any>} */
const selectedEvent = ref(null);
const eventDetailVisible = ref(false);

/** 总体判断:今日事件与可疑访问驱动(05 §21:正常/需要处理) */
const overallKind = computed(() =>
  securityStats.todayEvents > 10 || accessStats.suspiciousVisits > 5 ? 'warning' : 'success',
);
const overallText = computed(() => (overallKind.value === 'success' ? '正常' : '需要处理'));

const uptimeText = computed(() => {
  const h = systemHealth.uptime_hours || 0;
  if (h < 24) return `${h} 小时`;
  return `${Math.floor(h / 24)} 天 ${h % 24} 小时`;
});

/** @param {string | undefined} type */
function getEventTypeName(type) {
  /** @type {Record<string, string>} */
  const names = {
    login_fail: '登录失败',
    rate_limit: '频率限制',
    sql_injection: '注入攻击',
    xss: 'XSS 攻击',
    unauthorized: '未授权访问',
  };
  return names[type || ''] || type || '未知事件';
}

/** @param {string | undefined} type @returns {'neutral'|'blue'|'orange'} */
function eventTypeTone(type) {
  if (type === 'login_fail' || type === 'rate_limit') return 'neutral';
  if (type === 'sql_injection' || type === 'xss') return 'orange';
  return 'blue';
}

/** @param {string | undefined} severity @returns {'success'|'warning'|'neutral'|'danger'} */
function severityKind(severity) {
  switch (severity) {
    case 'high': return 'danger';
    case 'medium': return 'warning';
    case 'low': return 'success';
    default: return 'neutral';
  }
}

/** @param {string | undefined} severity */
function getSeverityName(severity) {
  /** @type {Record<string, string>} */
  const names = { high: '高', medium: '中', low: '低' };
  return names[severity || ''] || severity || '低';
}

/** @param {string | number | null | undefined} t */
function formatDateTime(t) {
  if (!t) return '—';
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return String(t);
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** @param {Promise<any>} promise */
async function safe(promise) {
  try {
    return await promise;
  } catch (e) {
    return null;
  }
}

async function refreshData() {
  loading.value = true;
  error.value = false;

  const statsRes = await safe(API.getSecurityStats());
  if (statsRes?.data?.code === 0) {
    Object.assign(securityStats, statsRes.data.data);
  } else {
    // 统计不可用:按 0 展示,不虚构模拟数据
    error.value = !statsRes;
  }

  const healthRes = await safe(API.getSystemHealth());
  if (healthRes?.data?.code === 0) {
    Object.assign(systemHealth, healthRes.data.data);
  }

  const eventsRes = await safe(API.getSecurityEvents({ limit: 10 }));
  if (eventsRes?.data?.code === 0) {
    recentEvents.value = eventsRes.data.data || [];
  } else {
    recentEvents.value = [];
  }

  const accessRes = await safe(API.getAccessStatsToday());
  if (accessRes?.data?.code === 0) {
    Object.assign(accessStats, accessRes.data.data);
  }

  loading.value = false;
}

/** @param {any} event */
function viewEventDetail(event) {
  selectedEvent.value = event;
  eventDetailVisible.value = true;
}

/** @param {any} event */
async function handleEvent(event) {
  try {
    await ElMessageBox.confirm(
      `将事件「${getEventTypeName(event.type)}(${event.source_ip || '未知 IP'})」标记为已处理?`,
      '处理安全事件',
      { type: 'warning', confirmButtonText: '标记已处理', cancelButtonText: '取消' },
    );
    const response = await API.handleSecurityEvent(event.id);
    if (response.data.code === 0) {
      ElMessage.success('事件已标记为已处理');
      eventDetailVisible.value = false;
      await refreshData();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败');
  }
}

/** @type {ReturnType<typeof setInterval> | null} */
let refreshTimer = null;

onMounted(() => {
  refreshData();
  // 安全数据 60s 轮询(比日志页的 30s 克制)
  refreshTimer = setInterval(refreshData, 60000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.security-center {
  width: 100%;
}
.grid-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.card {
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
}
.event-card {
  margin-bottom: 16px;
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
.card-body {
  padding: 16px;
}

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
.kv-plain {
  font-size: 12px;
  color: var(--adm-text-2);
  font-variant-numeric: tabular-nums;
}

.ghost-btn {
  height: 30px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  cursor: pointer;
}
.ghost-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

.table-wrap {
  overflow: auto;
}
.cell-text {
  font-size: 12px;
  color: var(--adm-text-2);
}

.row-actions-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.edit-btn,
.more-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 11px;
  cursor: pointer;
}
.more-btn {
  width: 29px;
  padding: 0;
  color: var(--adm-muted);
  letter-spacing: 1px;
}
.edit-btn:hover,
.more-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

.detail-body {
  display: grid;
}
.detail-body .kv-row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 14px;
  padding: 12px 0;
  border-top: 1px solid var(--adm-border);
  font-size: 12px;
  color: var(--adm-text-2);
}
.detail-body .kv-row:first-child {
  border-top: 0;
}
.detail-body label {
  color: var(--adm-muted);
}

@media (max-width: 950px) {
  .grid-two {
    grid-template-columns: 1fr;
  }
}
</style>
