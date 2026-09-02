<template>
  <el-table
    :data="backups"
    :loading="loading"
    stripe
    empty-text="暂无备份记录"
    class="backup-table"
  >
    <el-table-column prop="backup_id" label="备份ID" width="200">
      <template #default="{ row }">
        <el-tooltip :content="row.backup_id" placement="top">
          <span class="backup-id">{{ row.backup_id }}</span>
        </el-tooltip>
      </template>
    </el-table-column>

    <el-table-column prop="backup_type" label="类型" width="100">
      <template #default="{ row }">
        <el-tag
          :type="getBackupTypeTagType(row.backup_type)"
          size="small"
        >
          {{ getBackupTypeLabel(row.backup_type) }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column prop="status" label="状态" width="100">
      <template #default="{ row }">
        <el-tag
          :type="getStatusTagType(row.status)"
          size="small"
        >
          {{ getStatusLabel(row.status) }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column prop="file_size" label="大小" width="120">
      <template #default="{ row }">
        <span v-if="row.file_size">{{ formatFileSize(row.file_size) }}</span>
        <span v-else class="text-muted">-</span>
      </template>
    </el-table-column>

    <el-table-column prop="created_at" label="创建时间" width="160">
      <template #default="{ row }">
        <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
      </template>
    </el-table-column>

    <el-table-column prop="duration" label="耗时" width="100">
      <template #default="{ row }">
        <span v-if="row.duration !== null">{{ row.duration }}s</span>
        <span v-else class="text-muted">-</span>
      </template>
    </el-table-column>

    <el-table-column prop="extra_data" label="描述" min-width="150">
      <template #default="{ row }">
        <span class="description">
          {{ row.extra_data?.description || '无描述' }}
        </span>
      </template>
    </el-table-column>

    <el-table-column label="操作" width="200" fixed="right">
      <template #default="{ row }">
        <div class="action-buttons">
          <el-button
            size="small"
            title="查看详情"
            @click="emit('detail', row)"
          >
            <el-icon><View /></el-icon>
          </el-button>

          <el-button
            v-if="canDownloadBackup(row)"
            size="small"
            type="success"
            title="下载备份"
            @click="emit('download', row)"
          >
            <el-icon><Download /></el-icon>
          </el-button>

          <el-button
            v-if="canRestoreBackup(row)"
            size="small"
            type="warning"
            title="恢复备份"
            @click="emit('restore', row)"
          >
            <el-icon><RefreshLeft /></el-icon>
          </el-button>

          <el-button
            size="small"
            type="danger"
            title="删除备份"
            @click="emit('delete', row)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </template>
    </el-table-column>
  </el-table>

  <!-- 分页 -->
  <div class="pagination-wrapper">
    <el-pagination
      :current-page="pagination.page"
      :page-size="pagination.per_page"
      :total="pagination.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="emit('size-change', $event)"
      @current-change="emit('current-change', $event)"
    />
  </div>
</template>

<script setup>
/** @typedef {import('../../types').BackupRecord} BackupRecord */

defineProps({
  backups: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  pagination: { type: Object, required: true },
  canDownloadBackup: { type: Function, required: true },
  canRestoreBackup: { type: Function, required: true },
})

const emit = defineEmits(['detail', 'download', 'restore', 'delete', 'size-change', 'current-change'])

/** @param {number | string | undefined} bytes */
const formatFileSize = (bytes) => {
  if (!bytes || bytes === '0' || bytes === 0) return '0 B'
  const size = parseInt(String(bytes)) || 0
  if (size === 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let currentSize = size
  let unitIndex = 0

  while (currentSize >= 1024 && unitIndex < units.length - 1) {
    currentSize /= 1024
    unitIndex++
  }

  return currentSize.toFixed(unitIndex === 0 ? 0 : 1) + ' ' + units[unitIndex]
}

/** @param {string | undefined} dateStr */
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/** @param {string | undefined} type */
const getBackupTypeLabel = (type) => {
  /** @type {Record<string, string>} */
  const labels = {
    full: '全量',
    incremental: '增量',
    snapshot: '快照'
  }
  return labels[type || ''] || type
}

/**
 * @param {string | undefined} type
 * @returns {'info' | 'success' | 'primary' | 'warning' | 'danger'}
 */
const getBackupTypeTagType = (type) => {
  /** @type {Record<string, 'info' | 'success' | 'primary' | 'warning' | 'danger'>} */
  const types = {
    full: 'primary',
    incremental: 'success',
    snapshot: 'warning'
  }
  return types[type || ''] || 'info'
}

/** @param {string | undefined} status */
const getStatusLabel = (status) => {
  /** @type {Record<string, string>} */
  const statusMap = {
    'pending': '等待中',
    'running': '执行中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消'
  }
  return statusMap[status || ''] || status
}

/**
 * @param {string | undefined} status
 * @returns {'info' | 'success' | 'primary' | 'warning' | 'danger'}
 */
const getStatusTagType = (status) => {
  /** @type {Record<string, 'info' | 'success' | 'primary' | 'warning' | 'danger'>} */
  const typeMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'cancelled': 'warning'
  }
  return typeMap[status || ''] || 'info'
}
</script>

<style scoped>
.backup-table {
  width: 100%;
}

.backup-id {
  font-family: monospace;
  font-size: 12px;
  color: #374151;
}

.time-text {
  color: #6b7280;
  font-size: 13px;
}

.description {
  color: #374151;
  font-size: 13px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-muted {
  color: #9ca3af;
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
