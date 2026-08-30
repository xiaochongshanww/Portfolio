<template>
  <div class="log-management">
    <AdminPageHeader title="操作日志" description="查询后台操作和安全审计记录。" />

    <!-- 05 §22 Audit Table:高密度 Table,无 Summary Strip -->
    <AdminToolbar
      v-model:search="filters.keyword"
      search-placeholder="搜索操作、用户或资源"
      :result-count="error ? null : pagination.total"
      refreshable
      @update:search="onSearchInput"
      @refresh="loadLogs"
    >
      <template #filters>
        <select v-model="filters.level" class="adm-select" aria-label="按级别筛选" @change="handleSearch">
          <option value="">全部级别</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="INFO">INFO</option>
        </select>
        <select v-model="filters.source" class="adm-select" aria-label="按来源筛选" @change="handleSearch">
          <option value="">全部来源</option>
          <option v-for="s in availableSources" :key="s" :value="s">{{ s }}</option>
        </select>
        <select v-model="filters.userId" class="adm-select" aria-label="按用户筛选" @change="handleSearch">
          <option :value="null">全部用户</option>
          <option v-for="u in availableUsers" :key="u.id" :value="u.id">{{ u.username || u.id }}</option>
        </select>
      </template>
      <template #right>
        <button type="button" class="ghost-btn" @click="exportVisible = true">导出</button>
        <button type="button" class="ghost-danger-btn" @click="cleanupVisible = true">清理</button>
      </template>
    </AdminToolbar>

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="日志加载失败"
        compact
        @reload="loadLogs"
      />
      <AdminStateBlock
        v-else-if="!loading && !logs.length"
        kind="empty"
        title="暂无日志"
        description="当前筛选条件下没有日志记录。"
        compact
      />
      <div v-else class="table-wrap">
        <el-table :data="logs" row-key="id" class="adm-table">
          <el-table-column label="时间" width="150">
            <template #default="{ row }">
              <span class="cell-text">{{ formatTime(row.timestamp) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="级别" width="92">
            <template #default="{ row }">
              <AdminStatus :kind="levelKind(row.level)" :label="row.level || 'INFO'" />
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="110" show-overflow-tooltip />
          <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
          <el-table-column prop="user_name" label="用户" width="110" show-overflow-tooltip />
          <el-table-column prop="ip_address" label="IP" width="130" show-overflow-tooltip />
          <el-table-column width="70" fixed="right" align="right">
            <template #default="{ row }">
              <button type="button" class="edit-btn" @click="viewDetail(row)">详情</button>
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
          :page-size="pagination.size"
          :page-sizes="[20, 50, 100]"
          :pager-count="5"
          small
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>

    <!-- 详情 Drawer(05 §27:日志详情适合 Drawer) -->
    <el-drawer v-model="detailVisible" title="日志详情" size="480px">
      <div v-if="selectedLog" class="detail-body">
        <div class="kv-row">
          <label>时间</label>
          <div>{{ formatFullTime(selectedLog.timestamp) }}</div>
        </div>
        <div class="kv-row">
          <label>级别</label>
          <div><AdminStatus :kind="levelKind(selectedLog.level)" :label="selectedLog.level || 'INFO'" /></div>
        </div>
        <div class="kv-row">
          <label>来源</label>
          <div>{{ selectedLog.source || '—' }}</div>
        </div>
        <div class="kv-row">
          <label>用户</label>
          <div>{{ selectedLog.user_name || '—' }}</div>
        </div>
        <div class="kv-row">
          <label>IP</label>
          <div>{{ selectedLog.ip_address || '—' }}</div>
        </div>
        <div class="kv-row">
          <label>消息</label>
          <div>{{ selectedLog.message }}</div>
        </div>
        <div v-if="selectedLog.details" class="kv-row">
          <label>详情</label>
          <pre class="detail-json">{{ formatJSON(selectedLog.details) }}</pre>
        </div>
      </div>
    </el-drawer>

    <!-- 导出 Dialog(05 §26) -->
    <el-dialog v-model="exportVisible" title="导出日志" width="420px">
      <div class="dialog-form">
        <label>格式</label>
        <select v-model="exportForm.format" class="adm-select w-full">
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
        </select>
        <label>条数上限</label>
        <el-input-number v-model="exportForm.limit" :min="100" :max="10000" :step="100" />
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="exportVisible = false">取消</el-button>
          <el-button type="primary" :loading="exporting" @click="handleExport">导出</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 清理 Dialog(危险,05 §33) -->
    <el-dialog v-model="cleanupVisible" title="清理日志" width="420px">
      <p class="confirm-message">将删除 {{ cleanupForm.days }} 天前的所有日志,删除后不可恢复。</p>
      <div class="dialog-form">
        <label>保留天数</label>
        <el-input-number v-model="cleanupForm.days" :min="7" :max="365" />
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cleanupVisible = false">取消</el-button>
          <el-button type="danger" :loading="cleaning" @click="handleCleanup">确认清理</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 操作日志(05 §22 Audit Table Pattern):高密度表格,无 Summary Strip。
 * 保留:queryLogs(POST)/来源与用户筛选/导出下载/清理确认/详情。
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';

const loading = ref(false);
const error = ref(false);
/** @type {import('vue').Ref<any[]>} */
const logs = ref([]);
/** @type {import('vue').Ref<string[]>} */
const availableSources = ref([]);
/** @type {import('vue').Ref<any[]>} */
const availableUsers = ref([]);

const filters = reactive({
  keyword: '',
  level: '',
  source: '',
  userId: null,
  timeRange: [],
});

const pagination = reactive({ page: 1, size: 20, total: 0 });

/** @type {import('vue').Ref<any>} */
const selectedLog = ref(null);
const detailVisible = ref(false);
const exportVisible = ref(false);
const cleanupVisible = ref(false);

const exportForm = reactive({ format: 'json', limit: 1000 });
const cleanupForm = reactive({ days: 30 });
const exporting = ref(false);
const cleaning = ref(false);

/** @param {string | undefined} level @returns {'success'|'warning'|'neutral'|'danger'} */
function levelKind(level) {
  switch (level) {
    case 'ERROR': return 'danger';
    case 'WARNING': return 'warning';
    default: return 'neutral';
  }
}

/** @param {string | number | Date | null | undefined} timestamp */
function formatTime(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** @param {string | number | Date | null | undefined} timestamp */
function formatFullTime(timestamp) {
  if (!timestamp) return '-';
  return new Date(timestamp).toLocaleString('zh-CN');
}

/** @param {unknown} data */
function formatJSON(data) {
  try {
    return JSON.stringify(data, null, 2);
  } catch (e) {
    return String(data);
  }
}

/** @type {ReturnType<typeof setTimeout> | undefined} */
let searchTimer;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => handleSearch(), 300);
}

async function loadLogs() {
  loading.value = true;
  error.value = false;
  try {
    /** @type {Record<string, any>} */
    const params = {
      page: pagination.page,
      size: pagination.size,
      level: filters.level,
      source: filters.source,
      keyword: filters.keyword,
      user_id: filters.userId,
      start_time: null,
      end_time: null,
    };
    if (filters.timeRange && filters.timeRange.length === 2) {
      params.start_time = filters.timeRange[0];
      params.end_time = filters.timeRange[1];
    }
    const response = await API.queryLogs(params);
    if (response.data.code === 0) {
      logs.value = response.data.data.logs;
      pagination.total = response.data.data.total;
    } else {
      error.value = true;
    }
  } catch (e) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

async function loadOptions() {
  try {
    const sourcesResponse = await API.getLogSources();
    if (sourcesResponse.data.code === 0) {
      availableSources.value = (sourcesResponse.data.data || []).filter(
        /** @param {unknown} s */
        (s) => s,
      );
    }
    const usersResponse = await API.getLogUsers();
    if (usersResponse.data.code === 0) {
      availableUsers.value = (usersResponse.data.data || []).filter(
        /** @param {{ id?: number }} u */
        (u) => u && u.id,
      );
    }
  } catch (e) {
    /* 筛选项失败不阻塞列表 */
  }
}

function handleSearch() {
  pagination.page = 1;
  loadLogs();
}

/** @param {number} page */
function handlePageChange(page) {
  pagination.page = page;
  loadLogs();
}

/** @param {number} size */
function handleSizeChange(size) {
  pagination.size = size;
  pagination.page = 1;
  loadLogs();
}

/** @param {any} log */
function viewDetail(log) {
  selectedLog.value = log;
  detailVisible.value = true;
}

async function handleExport() {
  exporting.value = true;
  try {
    /** @type {Record<string, any>} */
    const params = {
      format: exportForm.format,
      limit: exportForm.limit,
      level: filters.level,
      source: filters.source,
      keyword: filters.keyword,
      start_time: null,
      end_time: null,
    };
    if (filters.timeRange && filters.timeRange.length === 2) {
      params.start_time = filters.timeRange[0];
      params.end_time = filters.timeRange[1];
    }
    const response = await API.exportLogs(params);
    if (response.data.code === 0) {
      const dataStr = JSON.stringify(response.data.data, null, 2);
      const blob = new Blob([dataStr], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `logs_export_${new Date().toISOString().slice(0, 10)}.${exportForm.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      ElMessage.success('导出成功');
      exportVisible.value = false;
    } else {
      ElMessage.error(response.data.message || '导出失败');
    }
  } catch (e) {
    ElMessage.error('导出失败');
  } finally {
    exporting.value = false;
  }
}

async function handleCleanup() {
  cleaning.value = true;
  try {
    const response = await API.cleanupLogs({ days: cleanupForm.days });
    if (response.data.code === 0) {
      ElMessage.success('日志清理完成');
      cleanupVisible.value = false;
      await loadLogs();
    } else {
      ElMessage.error(response.data.message || '清理失败');
    }
  } catch (e) {
    ElMessage.error('清理失败');
  } finally {
    cleaning.value = false;
  }
}

onMounted(() => {
  loadLogs();
  loadOptions();
});

onUnmounted(() => {
  clearTimeout(searchTimer);
});
</script>

<style scoped>
.log-management {
  width: 100%;
}
.log-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.log-management :deep(.el-table) {
  width: 100%;
}

.adm-select,
.adm-input {
  height: 34px;
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
.ghost-btn {
  height: 32px;
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
.ghost-danger-btn {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-danger);
  font-size: 12px;
  cursor: pointer;
}
.ghost-danger-btn:hover {
  border-color: var(--adm-danger);
  background: var(--adm-danger-soft);
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
.cell-text {
  font-size: 13px;
  color: var(--adm-text-2);
  font-variant-numeric: tabular-nums;
}

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
  padding: 8px 12px;
  border-top: 1px solid var(--adm-border);
  color: var(--adm-muted);
  font-size: 12px;
}

/* Drawer 详情(05 §27) */
.detail-body {
  display: grid;
}
.detail-body .kv-row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 14px;
  padding: 12px 0;
  border-top: 1px solid var(--adm-border);
  font-size: 13px;
  color: var(--adm-text-2);
}
.detail-body .kv-row:first-child {
  border-top: 0;
}
.detail-body label {
  color: var(--adm-muted);
}
.detail-json {
  margin: 0;
  padding: 10px;
  border: 1px solid var(--adm-border);
  border-radius: 8px;
  background: var(--adm-surface-subtle);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  overflow: auto;
  max-height: 300px;
}

.dialog-form {
  display: grid;
  gap: 8px;
  font-size: 12px;
  color: var(--adm-muted);
}
.dialog-form .w-full {
  width: 100%;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.confirm-message {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--adm-text-2);
}
</style>
