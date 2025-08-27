<template>
  <div class="restore-management">
    <div class="header">
      <h2>恢复任务管理</h2>
      <p class="description">查看和监控所有恢复任务的状态和进度</p>
    </div>

    <!-- 筛选器 -->
    <div class="filters">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select 
            v-model="filters.status" 
            placeholder="状态筛选" 
            clearable
            @change="loadRestoreRecords"
          >
            <el-option label="全部状态" value="" />
            <el-option label="等待中" value="pending" />
            <el-option label="执行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select 
            v-model="filters.restore_type" 
            placeholder="恢复类型" 
            clearable
            @change="loadRestoreRecords"
          >
            <el-option label="全部类型" value="" />
            <el-option label="完整恢复" value="full" />
            <el-option label="仅数据库" value="database_only" />
            <el-option label="仅文件" value="files_only" />
            <el-option label="部分恢复" value="partial" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="loadRestoreRecords" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 恢复记录表格 -->
    <el-table 
      :data="restoreRecords" 
      v-loading="loading" 
      style="width: 100%"
      @row-click="showRestoreDetail"
    >
      <el-table-column prop="restore_id" label="恢复ID" width="200" show-overflow-tooltip>
        <template #default="scope">
          <el-button type="text" @click="showRestoreDetail(scope.row)">
            {{ scope.row.restore_id }}
          </el-button>
        </template>
      </el-table-column>

      <el-table-column prop="backup_info" label="源备份" width="180" show-overflow-tooltip>
        <template #default="scope">
          <div v-if="scope.row.backup_info">
            <div>{{ scope.row.backup_info.backup_id }}</div>
            <div class="text-xs text-gray-500">
              {{ scope.row.backup_info.backup_type }}
            </div>
          </div>
          <div v-else class="text-gray-400">-</div>
        </template>
      </el-table-column>

      <el-table-column prop="restore_type" label="恢复类型" width="120">
        <template #default="scope">
          <el-tag 
            :type="getRestoreTypeTagType(scope.row.restore_type)" 
            size="small"
          >
            {{ getRestoreTypeText(scope.row.restore_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
          <el-tag 
            :type="getStatusTagType(scope.row.status)" 
            size="small"
          >
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="progress" label="进度" width="150">
        <template #default="scope">
          <div class="progress-container">
            <el-progress 
              :percentage="scope.row.progress || 0" 
              :status="getProgressStatus(scope.row.status)"
              :stroke-width="8"
              text-inside
            />
            <div v-if="scope.row.status_message" class="status-message text-xs text-gray-600 mt-1">
              {{ scope.row.status_message }}
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="scope">
          {{ formatDateTime(scope.row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column prop="started_at" label="开始时间" width="160">
        <template #default="scope">
          {{ scope.row.started_at ? formatDateTime(scope.row.started_at) : '-' }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button 
            type="primary" 
            size="small" 
            @click="showRestoreDetail(scope.row)"
          >
            查看详情
          </el-button>
          <el-button 
            v-if="canCancel(scope.row.status)"
            type="danger" 
            size="small" 
            @click="cancelRestore(scope.row.restore_id)"
            :loading="scope.row._cancelling"
          >
            取消
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadRestoreRecords"
        @current-change="loadRestoreRecords"
      />
    </div>

    <!-- 恢复详情对话框 -->
    <el-dialog
      v-model="detailDialog.visible"
      :title="'恢复任务详情 - ' + detailDialog.data?.restore_id"
      width="800px"
      @close="stopProgressMonitoring"
    >
      <div v-if="detailDialog.data" class="restore-detail">
        <!-- 基本信息 -->
        <div class="section">
          <h4>基本信息</h4>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="info-item">
                <label>恢复ID:</label>
                <span>{{ detailDialog.data.restore_id }}</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <label>恢复类型:</label>
                <el-tag :type="getRestoreTypeTagType(detailDialog.data.restore_type)" size="small">
                  {{ getRestoreTypeText(detailDialog.data.restore_type) }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <label>状态:</label>
                <el-tag :type="getStatusTagType(detailDialog.data.status)" size="small">
                  {{ getStatusText(detailDialog.data.status) }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <label>进度:</label>
                <span>{{ detailDialog.data.progress || 0 }}%</span>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 实时进度 -->
        <div class="section" v-if="detailDialog.data.status === 'running'">
          <h4>实时进度监控</h4>
          <el-progress 
            :percentage="detailDialog.data.progress || 0" 
            :status="getProgressStatus(detailDialog.data.status)"
            :stroke-width="20"
            text-inside
          />
          <div v-if="detailDialog.data.status_message" class="status-message mt-2 text-gray-600">
            当前状态: {{ detailDialog.data.status_message }}
          </div>
        </div>

        <!-- 源备份信息 -->
        <div class="section" v-if="detailDialog.data.backup_info">
          <h4>源备份信息</h4>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="info-item">
                <label>备份ID:</label>
                <span>{{ detailDialog.data.backup_info.backup_id }}</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <label>备份类型:</label>
                <span>{{ detailDialog.data.backup_info.backup_type }}</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <label>文件大小:</label>
                <span>{{ formatFileSize(detailDialog.data.backup_info.file_size) }}</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <label>创建时间:</label>
                <span>{{ formatDateTime(detailDialog.data.backup_info.created_at) }}</span>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 时间信息 -->
        <div class="section">
          <h4>时间信息</h4>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="info-item">
                <label>创建时间:</label>
                <span>{{ formatDateTime(detailDialog.data.created_at) }}</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="info-item">
                <label>开始时间:</label>
                <span>{{ detailDialog.data.started_at ? formatDateTime(detailDialog.data.started_at) : '-' }}</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="info-item">
                <label>完成时间:</label>
                <span>{{ detailDialog.data.completed_at ? formatDateTime(detailDialog.data.completed_at) : '-' }}</span>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 恢复配置 -->
        <div class="section" v-if="detailDialog.data.restore_options">
          <h4>恢复配置</h4>
          <pre class="config-display">{{ formatJSON(detailDialog.data.restore_options) }}</pre>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button 
            v-if="canCancel(detailDialog.data?.status)"
            type="danger" 
            @click="cancelRestore(detailDialog.data.restore_id)"
            :loading="detailDialog.data?._cancelling"
          >
            取消任务
          </el-button>
          <el-button @click="detailDialog.visible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { backupApi } from '@/api/backup'

// 数据
const restoreRecords = ref([])
const loading = ref(false)

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
  data: null
})

// 进度监控定时器
let progressTimer = null

// 加载恢复记录
const loadRestoreRecords = async () => {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      ...filters
    }
    
    const response = await backupApi.getRestoreRecords(params)
    if (response.data.code === 0) {
      restoreRecords.value = response.data.data.items
      pagination.total = response.data.data.total
    } else {
      ElMessage.error(response.data.message || '加载恢复记录失败')
    }
  } catch (error) {
    console.error('加载恢复记录失败:', error)
    ElMessage.error('加载恢复记录失败')
  } finally {
    loading.value = false
  }
}

// 显示恢复详情
const showRestoreDetail = async (record) => {
  try {
    detailDialog.data = { ...record }
    detailDialog.visible = true
    
    // 如果任务正在运行，启动进度监控
    if (record.status === 'running') {
      startProgressMonitoring(record.restore_id)
    }
  } catch (error) {
    console.error('显示恢复详情失败:', error)
    ElMessage.error('显示恢复详情失败')
  }
}

// 开始进度监控
const startProgressMonitoring = (restoreId) => {
  if (progressTimer) {
    clearInterval(progressTimer)
  }
  
  progressTimer = setInterval(async () => {
    try {
      const response = await backupApi.getRestoreProgress(restoreId)
      if (response.data.code === 0) {
        detailDialog.data = response.data.data
        
        // 如果任务已完成或失败，停止监控
        if (['completed', 'failed', 'cancelled'].includes(response.data.data.status)) {
          stopProgressMonitoring()
          // 刷新列表
          loadRestoreRecords()
        }
      }
    } catch (error) {
      console.error('获取恢复进度失败:', error)
      stopProgressMonitoring()
    }
  }, 2000) // 每2秒更新一次
}

// 停止进度监控
const stopProgressMonitoring = () => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

// 取消恢复任务
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
    
    // 设置取消loading状态
    const record = restoreRecords.value.find(r => r.restore_id === restoreId)
    if (record) {
      record._cancelling = true
    }
    if (detailDialog.data?.restore_id === restoreId) {
      detailDialog.data._cancelling = true
    }
    
    const response = await backupApi.cancelRestore(restoreId)
    if (response.data.code === 0) {
      ElMessage.success('恢复任务已取消')
      loadRestoreRecords()
      if (detailDialog.visible && detailDialog.data?.restore_id === restoreId) {
        detailDialog.visible = false
      }
    } else {
      ElMessage.error(response.data.message || '取消恢复任务失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消恢复任务失败:', error)
      ElMessage.error('取消恢复任务失败')
    }
  } finally {
    // 清除取消loading状态
    const record = restoreRecords.value.find(r => r.restore_id === restoreId)
    if (record) {
      record._cancelling = false
    }
    if (detailDialog.data?.restore_id === restoreId) {
      detailDialog.data._cancelling = false
    }
  }
}

// 工具函数
const getStatusText = (status) => {
  const statusMap = {
    'pending': '等待中',
    'running': '执行中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消'
  }
  return statusMap[status] || status
}

const getStatusTagType = (status) => {
  const typeMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'cancelled': ''
  }
  return typeMap[status] || ''
}

const getRestoreTypeText = (type) => {
  const typeMap = {
    'full': '完整恢复',
    'database_only': '仅数据库',
    'files_only': '仅文件',
    'partial': '部分恢复'
  }
  return typeMap[type] || type
}

const getRestoreTypeTagType = (type) => {
  const typeMap = {
    'full': 'primary',
    'database_only': 'success',
    'files_only': 'warning',
    'partial': 'info'
  }
  return typeMap[type] || ''
}

const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'exception'
  return undefined
}

const canCancel = (status) => {
  return ['pending', 'running'].includes(status)
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

const formatJSON = (jsonString) => {
  try {
    if (typeof jsonString === 'string') {
      return JSON.stringify(JSON.parse(jsonString), null, 2)
    }
    return JSON.stringify(jsonString, null, 2)
  } catch (error) {
    return jsonString
  }
}

// 生命周期
onMounted(() => {
  loadRestoreRecords()
})

onUnmounted(() => {
  stopProgressMonitoring()
})
</script>

<style scoped>
.restore-management {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.header h2 {
  margin: 0 0 8px 0;
  color: #303133;
}

.header .description {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.filters {
  margin-bottom: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 6px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.progress-container {
  width: 100%;
}

.status-message {
  font-size: 12px;
  margin-top: 4px;
  color: #909399;
}

.restore-detail .section {
  margin-bottom: 24px;
}

.restore-detail .section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 16px;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.restore-detail .info-item {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.restore-detail .info-item label {
  display: inline-block;
  width: 80px;
  color: #606266;
  font-weight: 500;
}

.restore-detail .info-item span {
  color: #303133;
}

.config-display {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  font-size: 13px;
  color: #606266;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.text-xs {
  font-size: 12px;
}

.text-gray-400 {
  color: #c0c4cc;
}

.text-gray-500 {
  color: #909399;
}

.text-gray-600 {
  color: #606266;
}

.mt-1 {
  margin-top: 4px;
}

.mt-2 {
  margin-top: 8px;
}
</style>