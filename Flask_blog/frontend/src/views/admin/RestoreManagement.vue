<template>
  <div class="restore-management">
    <AdminPageHeader title="恢复管理" description="从历史备份恢复站点数据，并查看恢复记录。" />

    <!-- 恢复警告(原型 notice) -->
    <div class="restore-notice">
      <b>恢复操作会修改当前数据。</b>
      建议先创建最新备份。恢复开始后，后台将暂时进入维护状态。
    </div>

    <!-- Grid2:选择恢复点 + 最近恢复记录 -->
    <div class="grid-two">
      <!-- 选择恢复点 -->
      <section class="card">
        <div class="card-head">
          <h2>选择恢复点</h2>
        </div>
        <div class="card-body">
          <div v-if="backupsLoading" class="card-loading">
            <el-skeleton :rows="3" animated />
          </div>
          <AdminStateBlock
            v-else-if="!completedBackups.length"
            kind="empty"
            title="暂无可用备份"
            description="先在备份管理中创建备份，才能执行恢复。"
            compact
          >
            <RouterLink to="/admin/backup" class="ghost-btn">前往备份管理</RouterLink>
          </AdminStateBlock>
          <div v-else class="restore-form">
            <label class="field-label">备份版本</label>
            <select v-model="selectedBackupId" class="adm-select w-full" aria-label="选择备份版本">
              <option v-for="b in completedBackups" :key="b.backup_id" :value="b.backup_id">
                {{ b.backup_id }} · {{ shortTime(b.created_at) }}
              </option>
            </select>

            <label class="field-label">恢复范围</label>
            <select v-model="restoreType" class="adm-select w-full" aria-label="选择恢复范围">
              <option value="full">完整恢复（数据库 + 文件）</option>
              <option value="database_only">仅数据库</option>
              <option value="files_only">仅文件</option>
            </select>

            <div class="protect-row">✓ 恢复前自动创建当前状态备份</div>

            <el-button
              type="danger"
              :loading="starting"
              :disabled="!selectedBackupId"
              @click="startRestore"
            >开始恢复</el-button>
          </div>
        </div>
      </section>

      <!-- 恢复前检查(评审修订:替代与下方表格重复的"最近恢复记录";
           每项均来自真实数据:最新备份=已完成备份列表,DB=记录加载成功) -->
      <section class="card">
        <div class="card-head">
          <h2>恢复前检查</h2>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row">
              <label>最新备份</label>
              <div>
                <template v-if="latestBackup">{{ latestBackup.backup_id }}<span class="kv-sub"> · {{ shortTime(latestBackup.created_at) }}</span></template>
                <template v-else><span class="check-bad">无可用备份</span></template>
              </div>
            </div>
            <div class="kv-row">
              <label>数据库状态</label>
              <div><AdminStatus :kind="dbReachable ? 'success' : 'danger'" :label="dbReachable ? '正常' : '异常'" /></div>
            </div>
            <div class="kv-row">
              <label>存储空间</label>
              <div>{{ storageText }}</div>
            </div>
            <div class="kv-row">
              <label>当前写入任务</label>
              <div>{{ runningRestoreCount }} 个恢复任务执行中</div>
            </div>
            <div class="kv-row">
              <label>维护状态</label>
              <div><AdminStatus :kind="maintenanceActive ? 'warning' : 'success'" :label="maintenanceActive ? '维护中' : '未启用'" /></div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 筛选 Toolbar(记录较多时使用) -->
    <AdminToolbar
      :result-count="pagination.total"
      refreshable
      @refresh="loadRestoreRecords"
    >
      <template #filters>
        <select v-model="filters.status" class="adm-select" aria-label="按状态筛选" @change="loadRestoreRecords">
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">执行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="cancelled">已取消</option>
        </select>
        <select v-model="filters.restore_type" class="adm-select" aria-label="按恢复类型筛选" @change="loadRestoreRecords">
          <option value="">全部类型</option>
          <option value="full">完整恢复</option>
          <option value="database_only">仅数据库</option>
          <option value="files_only">仅文件</option>
          <option value="partial">部分恢复</option>
        </select>
      </template>
      <template #right>
        <button
          v-if="hasStuckTasks"
          type="button"
          class="ghost-danger-btn"
          :disabled="cleaningUp"
          @click="cleanupStuckTasks"
        >清理卡住的任务</button>
      </template>
    </AdminToolbar>

    <!-- 恢复记录表 -->
    <section class="table-card">
      <AdminStateBlock
        v-if="loadError"
        kind="error"
        title="恢复记录加载失败"
        compact
        @reload="loadRestoreRecords"
      />
      <AdminStateBlock
        v-else-if="!loading && !restoreRecords.length"
        kind="empty"
        title="暂无恢复记录"
        compact
      />
      <div v-else class="table-wrap">
        <el-table :data="restoreRecords" row-key="restore_id" class="adm-table">
          <el-table-column label="恢复任务" min-width="220">
            <template #default="{ row }">
              <span class="cell-strong">{{ row.restore_id }}</span>
              <span v-if="row.backup_info" class="cell-sub">源备份 {{ row.backup_info.backup_id }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="110">
            <template #default="{ row }">{{ getRestoreTypeText(row.restore_type) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <AdminStatus :kind="statusKind(row.status)" :label="getStatusText(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="进度" width="140">
            <template #default="{ row }">
              <span class="cell-text">{{ row.progress != null ? row.progress + '%' : '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="150">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column width="150" fixed="right" align="right">
            <template #default="{ row }">
              <div class="row-actions-inline">
                <button type="button" class="edit-btn" @click="showRestoreDetail(row)">详情</button>
                <button
                  v-if="canCancel(row.status)"
                  type="button"
                  class="edit-btn danger-btn"
                  :disabled="row._cancelling"
                  @click="cancelRestore(row.restore_id)"
                >取消</button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ pagination.total }} 条恢复记录</span>
        <el-pagination
          layout="prev, pager, next, sizes"
          :total="pagination.total"
          :current-page="pagination.page"
          :page-size="pagination.per_page"
          :page-sizes="[10, 20, 50]"
          :pager-count="5"
          small
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>

    <!-- 恢复流程(原型 5 步 KV) -->
    <section class="card flow-card">
      <div class="card-head">
        <h2>恢复流程</h2>
      </div>
      <div class="card-body">
        <div class="kv-list">
          <div class="kv-row"><label>1. 创建保护备份</label><div>保存恢复前的当前状态</div></div>
          <div class="kv-row"><label>2. 进入维护状态</label><div>阻止新的写入操作</div></div>
          <div class="kv-row"><label>3. 恢复数据</label><div>恢复数据库与所选文件</div></div>
          <div class="kv-row"><label>4. 完整性检查</label><div>确认数据库和媒体引用一致</div></div>
          <div class="kv-row"><label>5. 恢复服务</label><div>退出维护状态并记录审计日志</div></div>
        </div>
      </div>
    </section>

    <!-- 恢复详情对话框(保留进度监控) -->
    <el-dialog
      v-model="detailDialog.visible"
      :title="'恢复任务详情 - ' + detailDialog.data?.restore_id"
      width="720px"
      :close-on-click-modal="false"
      @close="stopProgressMonitoring"
    >
      <div v-if="detailDialog.data" class="detail-body">
        <div class="kv-row"><label>恢复 ID</label><div>{{ detailDialog.data.restore_id }}</div></div>
        <div class="kv-row"><label>类型</label><div>{{ getRestoreTypeText(detailDialog.data.restore_type) }}</div></div>
        <div class="kv-row"><label>状态</label><div><AdminStatus :kind="statusKind(detailDialog.data.status)" :label="getStatusText(detailDialog.data.status)" /></div></div>
        <div class="kv-row">
          <label>进度</label>
          <div>
            <el-progress
              :percentage="detailDialog.data.progress || 0"
              :status="getProgressStatus(detailDialog.data.status)"
            />
            <div v-if="detailDialog.data.status_message" class="kv-sub">{{ detailDialog.data.status_message }}</div>
          </div>
        </div>
        <div v-if="detailDialog.data.backup_info" class="kv-row">
          <label>源备份</label>
          <div>
            {{ detailDialog.data.backup_info.backup_id }}
            <span class="kv-sub">({{ formatFileSize(detailDialog.data.backup_info.file_size) }})</span>
          </div>
        </div>
        <div class="kv-row"><label>创建时间</label><div>{{ formatDateTime(detailDialog.data.created_at) }}</div></div>
        <div class="kv-row"><label>完成时间</label><div>{{ detailDialog.data.completed_at ? formatDateTime(detailDialog.data.completed_at) : '—' }}</div></div>
        <div v-if="canCancel(detailDialog.data.status)" class="kv-row">
          <label>操作</label>
          <div>
            <el-button type="danger" size="small" @click="cancelRestoreFromDialog(detailDialog.data.restore_id)">取消任务</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 恢复管理(05 V2 系统页面原型)
 * - 选择恢复点:从已完成备份发起恢复(restoreBackup + 进度监控);
 * - 最近恢复记录 + 记录表:状态/进度/取消;
 * - 恢复流程五步说明卡。
 * 保留:进度轮询、取消(表格/详情)、清理卡住任务、?highlight= 联动。
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { API } from '../../api'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import AdminToolbar from '../../components/admin/AdminToolbar.vue'
import AdminStatus from '../../components/admin/AdminStatus.vue'
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue'

const route = useRoute()

// 数据
/** @type {import('vue').Ref<any[]>} */
const restoreRecords = ref([])
const loading = ref(false)
const loadError = ref(false)
const cleaningUp = ref(false)
const starting = ref(false)

/** @type {import('vue').Ref<any[]>} */
const completedBackups = ref([])
const backupsLoading = ref(false)
/** @type {import('vue').Ref<string>} */
const selectedBackupId = ref('')
const restoreType = ref('full')

// 恢复前检查(§ 恢复前检查卡):各项均由真实数据派生
const dbReachable = ref(true)
/** @type {import('vue').Ref<{free?: number, total?: number} | null>} */
const storageInfo = ref(null)
const latestBackup = computed(() => completedBackups.value[0] || null)
const runningRestoreCount = computed(() =>
  restoreRecords.value.filter((/** @type {any} */ r) => r.status === 'running' || r.status === 'pending').length,
)
const maintenanceActive = computed(() => runningRestoreCount.value > 0)
const storageText = computed(() => {
  const st = storageInfo.value
  if (!st || !st.total) return '—'
  return `可用 ${formatFileSize(st.free)} / 总量 ${formatFileSize(st.total)}`
})
const hasStuckTasks = computed(() =>
  restoreRecords.value.some(
    (/** @type {any} */ r) =>
      (r.status === 'running' || r.status === 'pending') &&
      r.created_at &&
      Date.now() - new Date(r.created_at).getTime() > 10 * 60 * 1000,
  ),
)

// 筛选条件
const filters = reactive({
  status: '',
  restore_type: ''
})

// 分页
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

// 详情对话框
const detailDialog = reactive({
  visible: false,
  /** @type {any} */
  data: null
})

// 进度监控定时器
/** @type {ReturnType<typeof setInterval> | null} */
let progressTimer = null

// 高亮显示的恢复任务ID
/** @type {import('vue').Ref<string | null>} */
const highlightRestoreId = ref(null)

// 加载恢复记录
const loadRestoreRecords = async () => {
  loading.value = true
  loadError.value = false
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      ...filters
    }

    const response = await API.getRestoreRecords(params)
    if (response.data.code === 0) {
      restoreRecords.value = response.data.data.items
      pagination.total = response.data.data.total
      dbReachable.value = true
    } else {
      dbReachable.value = false
      loadError.value = true
    }
  } catch (error) {
    dbReachable.value = false
    loadError.value = true
  } finally {
    loading.value = false
  }
}

// 可用恢复点:已完成的备份
const loadBackups = async () => {
  backupsLoading.value = true
  try {
    const response = await API.getBackupRecords({ status: 'completed', page: 1, per_page: 50 })
    const data = response.data?.data || response.data || {}
    completedBackups.value = data.records || []
    if (!selectedBackupId.value && completedBackups.value.length) {
      selectedBackupId.value = completedBackups.value[0].backup_id
    }
  } catch (e) {
    completedBackups.value = []
  } finally {
    backupsLoading.value = false
  }
}

// 发起恢复(原型:开始恢复)
const startRestore = async () => {
  if (!selectedBackupId.value) return
  const backup = completedBackups.value.find((b) => b.backup_id === selectedBackupId.value)
  try {
    await ElMessageBox.confirm(
      `从「${selectedBackupId.value}」恢复站点数据？恢复开始后后台将暂时进入维护状态。`,
      '开始恢复',
      { type: 'warning', confirmButtonText: '开始恢复', cancelButtonText: '取消' }
    )
    starting.value = true
    const response = await API.restoreBackup(selectedBackupId.value, {
      restore_type: restoreType.value
    })
    if (response.data.code === 0) {
      ElMessage.success('恢复任务已开始')
      const restoreId = response.data.data?.restore_id
      await loadRestoreRecords()
      // 开始进度监控
      if (restoreId) {
        const record = restoreRecords.value.find((r) => r.restore_id === restoreId)
        if (record) showRestoreDetail(record)
        else startProgressMonitoring(restoreId)
      }
    } else {
      ElMessage.error(response.data.message || '恢复任务启动失败')
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('恢复任务启动失败')
  } finally {
    starting.value = false
  }
}

// 显示恢复详情
/** @param {any} record */
const showRestoreDetail = async (record) => {
  detailDialog.data = { ...record }
  detailDialog.visible = true
  if (record.status === 'running') {
    startProgressMonitoring(record.restore_id)
  }
}

// 开始进度监控
/** @param {string | undefined} restoreId */
const startProgressMonitoring = (restoreId) => {
  if (progressTimer) {
    clearInterval(progressTimer)
  }
  progressTimer = setInterval(async () => {
    try {
      const response = await API.getRestoreProgress(restoreId)
      if (response.data.code === 0) {
        detailDialog.data = response.data.data
        if (['completed', 'failed', 'cancelled'].includes(response.data.data.status)) {
          stopProgressMonitoring()
          loadRestoreRecords()
        }
      }
    } catch (error) {
      stopProgressMonitoring()
    }
  }, 2000)
}

// 停止进度监控
const stopProgressMonitoring = () => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

const handleSelectionChange = () => {}

/** @param {string | undefined} status */
const getProgressStatus = (status) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  return undefined
}

/** @param {string | undefined} status */
const canCancel = (status) => ['pending', 'running'].includes(status || '')

/** @param {string | undefined} status @returns {'success'|'warning'|'neutral'|'danger'} */
function statusKind(status) {
  /** @type {Record<string, 'success'|'warning'|'neutral'|'danger'>} */
  const kinds = { completed: 'success', running: 'warning', failed: 'danger' }
  return kinds[status || ''] || 'neutral'
}

/** @param {string | undefined} status */
const getStatusText = (status) => {
  /** @type {Record<string, string>} */
  const statusMap = {
    'pending': '等待中',
    'running': '执行中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消'
  }
  return statusMap[status || ''] || status || '未知'
}

/** @param {string | undefined} type */
const getRestoreTypeText = (type) => {
  /** @type {Record<string, string>} */
  const typeMap = {
    'full': '完整恢复',
    'database_only': '仅数据库',
    'files_only': '仅文件',
    'partial': '部分恢复'
  }
  return typeMap[type || ''] || type
}

/** @param {number | null | undefined} bytes */
const formatFileSize = (bytes) => {
  if (!bytes || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i += 1
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

/** @param {string | undefined} t */
const shortTime = (t) => {
  if (!t) return '—'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** @param {string | undefined} dateString */
const formatDateTime = (dateString) => {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleString('zh-CN')
}

// 取消恢复任务（从表格发起）
/** @param {string} restoreId */
const cancelRestore = async (restoreId) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消这个恢复任务吗？正在进行的恢复操作将被中止。',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const record = restoreRecords.value.find(r => r.restore_id === restoreId)
    if (record) {
      record._cancelling = true
    }
    if (detailDialog.data?.restore_id === restoreId && detailDialog.data) {
      detailDialog.data._cancelling = true
    }

    const response = await API.cancelRestore(restoreId)
    if (response.data.code === 0) {
      ElMessage.success('恢复任务已取消')
      await loadRestoreRecords()

      if (detailDialog.visible && detailDialog.data?.restore_id === restoreId) {
        detailDialog.visible = false
      }
    } else {
      ElMessage.error(response.data.message || '取消恢复任务失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消恢复任务失败')
    }
  } finally {
    const record = restoreRecords.value.find(r => r.restore_id === restoreId)
    if (record) {
      record._cancelling = false
    }
    if (detailDialog.data?.restore_id === restoreId && detailDialog.data) {
      detailDialog.data._cancelling = false
    }
  }
}

// 从详情对话框取消恢复任务
/** @param {string} restoreId */
const cancelRestoreFromDialog = async (restoreId) => {
  const wasDetailDialogVisible = detailDialog.visible
  const originalDialogData = detailDialog.data
  try {
    const response = await API.cancelRestore(restoreId)
    if (response.data.code === 0) {
      ElMessage.success('恢复任务已取消')
      await loadRestoreRecords()
      detailDialog.visible = false
    } else {
      ElMessage.error(response.data.message || '取消恢复任务失败')
      if (wasDetailDialogVisible && originalDialogData?.restore_id === restoreId) {
        detailDialog.data = originalDialogData
        detailDialog.visible = true
      }
    }
  } catch (error) {
    if (error === 'cancel') {
      if (wasDetailDialogVisible && originalDialogData?.restore_id === restoreId) {
        detailDialog.data = originalDialogData
        detailDialog.visible = true
      }
    } else {
      ElMessage.error('取消恢复任务失败')
      if (wasDetailDialogVisible && originalDialogData?.restore_id === restoreId) {
        detailDialog.data = originalDialogData
        detailDialog.visible = true
      }
    }
  }
}

// 清理卡住的任务
const cleanupStuckTasks = async () => {
  try {
    await ElMessageBox.confirm(
      '此操作将清理所有运行时间超过10分钟的卡住任务。确定继续吗？',
      '清理卡住的任务',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    cleaningUp.value = true
    const response = await API.cleanupStuckRestores()

    if (response.data.code === 0) {
      const cleanedCount = response.data.data.cleaned_count
      if (cleanedCount > 0) {
        ElMessage.success(`成功清理了 ${cleanedCount} 个卡住的任务`)
        await loadRestoreRecords()
      } else {
        ElMessage.info('没有发现卡住的任务')
      }
    } else {
      ElMessage.error(response.data.message || '清理任务失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清理卡住任务失败')
    }
  }
}

/** @param {number} page */
function handlePageChange(page) {
  pagination.page = page
  loadRestoreRecords()
}

/** @param {number} size */
function handleSizeChange(size) {
  pagination.per_page = size
  pagination.page = 1
  loadRestoreRecords()
}

onMounted(async () => {
  await loadRestoreRecords()

  // 检查URL查询参数，高亮显示特定的恢复任务(备份页发起恢复后跳转联动)
  const highlightId = route.query.highlight
  if (highlightId) {
    const targetRecord = restoreRecords.value.find(record => record.restore_id === highlightId)
    if (targetRecord) {
      if (targetRecord.status === 'running' || targetRecord.status === 'pending') {
        startProgressMonitoring(targetRecord.restore_id)
      }
      setTimeout(() => {
        highlightRestoreId.value = null
      }, 5000)
    }
  }

  // 正在运行的任务自动监控
  restoreRecords.value.forEach((record) => {
    if (record.status === 'running' || record.status === 'pending') {
      startProgressMonitoring(record.restore_id)
    }
  })

  // 恢复前检查:存储空间来自备份统计
  try {
    API.getBackupStatistics().then((/** @type {any} */ r) => {
      if (r?.data?.code === 0) {
        storageInfo.value = r.data.data?.storage || null
      }
    })
  } catch (e) { /* 静默 */ }

  loadBackups()
})

onUnmounted(() => {
  stopProgressMonitoring()
})
</script>

<style scoped>
.restore-management {
  width: 100%;
}
.restore-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.restore-management :deep(.el-table) {
  width: 100%;
}

/* 恢复警告(原型 notice) */
.restore-notice {
  padding: 13px 14px;
  border: 1px solid #fed7aa;
  background: #fff7ed;
  border-radius: 10px;
  color: #9a3412;
  font-size: 13px;
  line-height: 1.65;
  margin-bottom: 18px;
}
.restore-notice b {
  font-weight: 650;
}

.grid-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
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
.card-loading {
  padding: 4px 0;
}

/* 恢复点表单 */
.restore-form {
  display: grid;
  gap: 8px;
}
.field-label {
  font-size: 12px;
  font-weight: 650;
  color: var(--adm-text-2);
  margin-top: 4px;
}
.adm-select {
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text);
  font-size: 13px;
  outline: none;
}
.adm-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}
.w-full {
  width: 100%;
}
.protect-row {
  font-size: 12px;
  color: var(--adm-success);
  padding: 4px 0;
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

/* 记录 KV */
.kv-list {
  display: grid;
}
.kv-row {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 14px;
  padding: 12px 0;
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
  font-size: 12px;
  color: var(--adm-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kv-sub {
  font-size: 11px;
  color: var(--adm-muted);
}
.kv-row.highlight {
  background: var(--adm-primary-soft);
}

/* 记录表 */
.table-card {
  border: 1px solid var(--adm-border);
  border-radius: 0 0 var(--adm-r-container) var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
}
.table-wrap {
  overflow: auto;
}
.cell-strong {
  font-size: 12px;
  color: var(--adm-text);
  display: block;
}
.cell-sub {
  display: block;
  font-size: 11px;
  color: var(--adm-muted);
  margin-top: 2px;
}
.cell-text {
  font-size: 12px;
  color: var(--adm-text-2);
  font-variant-numeric: tabular-nums;
}
.row-actions-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
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
}
.edit-btn.danger-btn {
  color: var(--adm-danger);
  border-color: var(--adm-danger);
}
.edit-btn.danger-btn:hover:not(:disabled) {
  background: var(--adm-danger-soft);
}
.edit-btn:hover:not(:disabled) {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}
.edit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

/* 流程卡 */
.flow-card {
  margin-top: 18px;
}
.flow-card .kv-row {
  grid-template-columns: 180px 1fr;
  font-size: 13px;
  color: var(--adm-text-2);
}
.flow-card .kv-row label {
  font-weight: 650;
  color: var(--adm-text-2);
}

/* 详情 */
.detail-body {
  display: grid;
}
.detail-body .kv-row {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 14px;
  padding: 11px 0;
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
.kv-sub {
  font-size: 11px;
  color: var(--adm-muted);
}

@media (max-width: 1000px) {
  .grid-two {
    grid-template-columns: 1fr;
  }
}
</style>
