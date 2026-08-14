<template>
  <el-dialog
    :model-value="visible"
    title="备份详情"
    width="800px"
    :z-index="9999"
    append-to-body
    @update:model-value="emit('update:visible', $event)"
  >
    <div v-if="backup" class="backup-detail">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="备份ID">
          {{ backup.backup_id }}
        </el-descriptions-item>
        <el-descriptions-item label="备份类型">
          <el-tag :type="getBackupTypeTagType(backup.backup_type)">
            {{ getBackupTypeLabel(backup.backup_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(backup.status)">
            {{ getStatusLabel(backup.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="文件大小">
          {{ backup.file_size ? formatFileSize(backup.file_size) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="压缩大小">
          {{ backup.compressed_size ? formatFileSize(backup.compressed_size) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="压缩比">
          {{ backup.compression_ratio ? (backup.compression_ratio * 100).toFixed(1) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="文件数量">
          {{ backup.files_count || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="数据库数量">
          {{ backup.databases_count || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="是否加密">
          <el-tag :type="backup.encryption_enabled ? 'success' : 'info'">
            {{ backup.encryption_enabled ? '是' : '否' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="校验和">
          <code v-if="backup.checksum" class="checksum">
            {{ backup.checksum }}
          </code>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(backup.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ backup.started_at ? formatDateTime(backup.started_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="完成时间">
          {{ backup.completed_at ? formatDateTime(backup.completed_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="耗时">
          {{ backup.duration !== null ? backup.duration + 's' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="存储位置" :span="2">
          <div v-if="backup.storage_providers" class="storage-providers">
            <el-tag
              v-for="(info, provider) in backup.storage_providers"
              :key="provider"
              :type="info.status === 'success' ? 'success' : 'danger'"
              size="small"
              class="provider-tag"
            >
              {{ String(provider).toUpperCase() }}: {{ info.status }}
            </el-tag>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item v-if="backup.extra_data?.description" label="描述" :span="2">
          {{ backup.extra_data.description }}
        </el-descriptions-item>
        <el-descriptions-item v-if="backup.error_message" label="错误信息" :span="2">
          <el-alert type="error" :title="backup.error_message" :closable="false" />
        </el-descriptions-item>
      </el-descriptions>
    </div>
  </el-dialog>
</template>

<script setup>
/** @typedef {import('../../types').BackupRecord} BackupRecord */

const props = defineProps({
  visible: { type: Boolean, default: false },
  backup: { type: Object, default: null },
})
void props

const emit = defineEmits(['update:visible'])

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
.checksum {
  word-break: break-all;
  font-size: 12px;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.storage-providers {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.provider-tag {
  margin: 0;
}
</style>
