<template>
  <div class="backup-management">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <el-icon class="title-icon"><FolderOpened /></el-icon>
          站点备份管理
        </h1>
        <p class="page-description">管理数据库和文件的备份与恢复</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" :loading="creating">
          <el-icon><Plus /></el-icon>
          创建备份
        </el-button>
        <el-button @click="refreshBackups" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon total">
            <el-icon size="24"><FolderOpened /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total_backups || 0 }}</div>
            <div class="stat-label">总备份数</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon success">
            <el-icon size="24"><SuccessFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.completed_backups || 0 }}</div>
            <div class="stat-label">成功备份</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon storage">
            <el-icon size="24"><Coin /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatFileSize(stats.total_storage_size) }}</div>
            <div class="stat-label">存储使用</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon rate">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ Math.round(stats.success_rate || 0) }}%</div>
            <div class="stat-label">成功率</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 运行中的备份任务 -->
    <el-card v-if="runningBackups.length > 0" class="running-backups-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon class="running-icon"><Loading /></el-icon>
            进行中的备份任务
          </span>
          <el-button size="small" @click="refreshBackups" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>

      <div class="running-backup-list">
        <div v-for="backup in runningBackups" :key="backup.id" class="running-backup-item">
          <div class="backup-info">
            <div class="backup-title">
              <el-tag :type="getBackupTypeTagType(backup.backup_type)" size="small">
                {{ getBackupTypeLabel(backup.backup_type) }}
              </el-tag>
              <span class="backup-id">{{ backup.backup_id }}</span>
            </div>
            <div class="backup-meta">
              <span class="time-text">开始时间: {{ formatDateTime(backup.started_at || backup.created_at) }}</span>
              <span class="duration-text">已运行: {{ getRunningDuration(backup.started_at || backup.created_at) }}</span>
            </div>
          </div>
          
          <div class="backup-progress">
            <el-progress 
              :percentage="backup.status === 'completed' ? 100 : (backup.progress || 0)" 
              :status="backup.status === 'failed' ? 'exception' : (backup.status === 'completed' ? 'success' : '')"
              :indeterminate="backup.status === 'running' && !backup.progress"
              :duration="3"
            />
            <div class="progress-text">
              <span v-if="backup.status === 'completed'">已完成</span>
              <span v-else-if="backup.progress">{{ backup.progress }}%</span>
              <span v-else>{{ getStatusLabel(backup.status) }}...</span>
            </div>
          </div>

          <div class="backup-actions">
            <el-button 
              size="small" 
              @click="showBackupDetail(backup)"
              title="查看详情"
            >
              <el-icon><View /></el-icon>
            </el-button>
            <el-button 
              v-if="backup.status !== 'completed'"
              size="small" 
              type="danger"
              @click="cancelBackup(backup)"
              title="取消备份"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 备份列表 -->
    <el-card class="backup-list-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">备份记录</span>
          <div class="filter-controls">
            <el-select v-model="filters.backup_type" placeholder="备份类型" clearable size="small">
              <el-option label="全量备份" value="full" />
              <el-option label="增量备份" value="incremental" />
              <el-option label="快照备份" value="snapshot" />
            </el-select>
            <el-select v-model="filters.status" placeholder="状态" clearable size="small">
              <el-option label="已完成" value="completed" />
              <el-option label="进行中" value="running" />
              <el-option label="失败" value="failed" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table 
        :data="backups" 
        :loading="loading" 
        stripe
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
                @click="showBackupDetail(row)"
                title="查看详情"
              >
                <el-icon><View /></el-icon>
              </el-button>
              
              <el-button 
                v-if="row.status === 'completed'"
                size="small" 
                type="success"
                @click="downloadBackup(row)"
                title="下载备份"
              >
                <el-icon><Download /></el-icon>
              </el-button>

              <el-button 
                v-if="row.status === 'completed'"
                size="small" 
                type="warning"
                @click="showRestoreDialog(row)"
                title="恢复备份"
              >
                <el-icon><RefreshLeft /></el-icon>
              </el-button>

              <el-button 
                size="small" 
                type="danger"
                @click="deleteBackup(row)"
                title="删除备份"
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
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.per_page"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建备份对话框 -->
    <el-dialog 
      v-model="createDialog.visible" 
      title="创建新备份"
      width="600px"
      :z-index="9999"
      append-to-body
      @close="resetCreateForm"
    >
      <el-form 
        :model="createForm" 
        :rules="createRules" 
        label-width="120px"
      >
        <el-form-item label="备份类型" prop="backup_type">
          <el-select v-model="createForm.backup_type" placeholder="请选择备份类型">
            <el-option label="全量备份" value="full">
              <div class="option-detail">
                <div>全量备份</div>
                <div class="option-desc">完整备份所有数据和文件</div>
              </div>
            </el-option>
            <el-option label="增量备份" value="incremental">
              <div class="option-detail">
                <div>增量备份</div>
                <div class="option-desc">仅备份自上次备份后的更改</div>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="备份内容">
          <div class="backup-options">
            <el-checkbox v-model="createForm.include_database">
              <div class="option-detail">
                <div>数据库</div>
                <div class="option-desc">包含所有数据库表和数据</div>
              </div>
            </el-checkbox>
            <el-checkbox v-model="createForm.include_files">
              <div class="option-detail">
                <div>文件系统</div>
                <div class="option-desc">包含上传的文件和静态资源</div>
              </div>
            </el-checkbox>
          </div>
        </el-form-item>

        <el-form-item label="备份描述">
          <el-input 
            v-model="createForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入备份描述信息（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="createBackup" :loading="creating">
          {{ creating ? '创建中...' : '创建备份' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 备份详情对话框 -->
    <el-dialog 
      v-model="detailDialog.visible" 
      title="备份详情"
      width="800px"
      :z-index="9999"
      append-to-body
    >
      <div v-if="detailDialog.backup" class="backup-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="备份ID">
            {{ detailDialog.backup.backup_id }}
          </el-descriptions-item>
          <el-descriptions-item label="备份类型">
            <el-tag :type="getBackupTypeTagType(detailDialog.backup.backup_type)">
              {{ getBackupTypeLabel(detailDialog.backup.backup_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(detailDialog.backup.status)">
              {{ getStatusLabel(detailDialog.backup.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ detailDialog.backup.file_size ? formatFileSize(detailDialog.backup.file_size) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="压缩大小">
            {{ detailDialog.backup.compressed_size ? formatFileSize(detailDialog.backup.compressed_size) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="压缩比">
            {{ detailDialog.backup.compression_ratio ? (detailDialog.backup.compression_ratio * 100).toFixed(1) + '%' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="文件数量">
            {{ detailDialog.backup.files_count || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="数据库数量">
            {{ detailDialog.backup.databases_count || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="是否加密">
            <el-tag :type="detailDialog.backup.encryption_enabled ? 'success' : 'info'">
              {{ detailDialog.backup.encryption_enabled ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="校验和">
            <code v-if="detailDialog.backup.checksum" class="checksum">
              {{ detailDialog.backup.checksum }}
            </code>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(detailDialog.backup.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ detailDialog.backup.started_at ? formatDateTime(detailDialog.backup.started_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ detailDialog.backup.completed_at ? formatDateTime(detailDialog.backup.completed_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ detailDialog.backup.duration !== null ? detailDialog.backup.duration + 's' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="存储位置" :span="2">
            <div v-if="detailDialog.backup.storage_providers" class="storage-providers">
              <el-tag 
                v-for="(info, provider) in detailDialog.backup.storage_providers" 
                :key="provider"
                :type="info.status === 'success' ? 'success' : 'danger'"
                size="small"
                class="provider-tag"
              >
                {{ provider.toUpperCase() }}: {{ info.status }}
              </el-tag>
            </div>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailDialog.backup.extra_data?.description" label="描述" :span="2">
            {{ detailDialog.backup.extra_data.description }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detailDialog.backup.error_message" label="错误信息" :span="2">
            <el-alert type="error" :title="detailDialog.backup.error_message" :closable="false" />
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 恢复备份对话框 -->
    <el-dialog
      v-model="restoreDialogVisible"
      title="恢复备份"
      width="600px"
      :close-on-click-modal="false"
    >
      <div v-if="currentRestoreBackup">
        <div class="restore-warning">
          <el-alert
            title="重要提醒"
            type="warning"
            :closable="false"
            show-icon
          >
            <template #default>
              <div>恢复操作将会影响当前系统数据，请确认您了解以下风险：</div>
              <ul class="risk-list">
                <li>数据库恢复可能会覆盖现有数据</li>
                <li>文件恢复可能会替换当前文件</li>
                <li>恢复过程无法撤销，请提前做好当前数据备份</li>
              </ul>
            </template>
          </el-alert>
        </div>

        <div class="backup-info">
          <h4>备份信息</h4>
          <el-descriptions :column="2" size="small">
            <el-descriptions-item label="备份ID">{{ currentRestoreBackup.backup_id }}</el-descriptions-item>
            <el-descriptions-item label="备份类型">{{ currentRestoreBackup.backup_type }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(currentRestoreBackup.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="文件大小">{{ formatFileSize(currentRestoreBackup.file_size) }}</el-descriptions-item>
            <el-descriptions-item label="数据库数量">{{ currentRestoreBackup.databases_count }}</el-descriptions-item>
            <el-descriptions-item label="文件数量">{{ currentRestoreBackup.files_count }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="restore-options">
          <h4>恢复选项</h4>
          <el-form :model="restoreOptions" label-width="120px">
            <el-form-item label="恢复类型">
              <el-select v-model="restoreOptions.restore_type" style="width: 100%">
                <el-option value="full" label="完整恢复（数据库 + 文件）">
                  <span>完整恢复（数据库 + 文件）</span>
                  <span style="color: #8492a6; font-size: 12px; margin-left: 8px;">推荐</span>
                </el-option>
                <el-option value="database_only" label="仅恢复数据库">
                  <span>仅恢复数据库</span>
                  <span style="color: #8492a6; font-size: 12px; margin-left: 8px;">安全</span>
                </el-option>
                <el-option value="files_only" label="仅恢复文件">
                  <span>仅恢复文件</span>
                  <span style="color: #8492a6; font-size: 12px; margin-left: 8px;">谨慎</span>
                </el-option>
                <el-option value="partial" label="自定义恢复" />
              </el-select>
            </el-form-item>

            <div v-if="restoreOptions.restore_type === 'partial'">
              <el-form-item label="恢复内容">
                <el-checkbox v-model="restoreOptions.include_database">包含数据库</el-checkbox>
                <el-checkbox v-model="restoreOptions.include_files" style="margin-left: 16px;">包含文件</el-checkbox>
              </el-form-item>
            </div>

            <el-form-item label="目标路径" v-if="restoreOptions.restore_type !== 'database_only'">
              <el-input
                v-model="restoreOptions.target_path"
                placeholder="留空则恢复到原位置（高风险）"
              />
              <div style="color: #909399; font-size: 12px; margin-top: 4px;">
                建议指定一个安全的目录进行恢复，然后手动迁移所需文件
              </div>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="restoreOptions.test_mode">
                测试模式（仅验证，不实际执行恢复）
              </el-checkbox>
            </el-form-item>
          </el-form>
        </div>

        <!-- 恢复进度监控 -->
        <div v-if="currentRestoreTask" class="restore-progress">
          <h4>恢复进度</h4>
          <div class="progress-container">
            <el-progress 
              :percentage="currentRestoreTask.progress || 0"
              :status="getProgressStatus(currentRestoreTask.status)"
              :stroke-width="12"
              text-inside
            />
            <div class="progress-info">
              <div class="status-info">
                <el-tag 
                  :type="getStatusTagType(currentRestoreTask.status)"
                  size="small"
                >
                  {{ getStatusText(currentRestoreTask.status) }}
                </el-tag>
                <span class="task-id">ID: {{ currentRestoreTask.restore_id }}</span>
              </div>
              <div v-if="currentRestoreTask.status_message" class="status-message">
                {{ currentRestoreTask.status_message }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button 
            v-if="!currentRestoreTask"
            @click="restoreDialogVisible = false"
          >
            取消
          </el-button>
          <el-button
            v-if="!currentRestoreTask"
            type="danger"
            @click="performRestore"
            :loading="restoring"
            :disabled="restoreOptions.restore_type === 'partial' && !restoreOptions.include_database && !restoreOptions.include_files"
          >
            {{ restoring ? '启动恢复中...' : '确认恢复' }}
          </el-button>

          <!-- 恢复进行中的按钮 -->
          <template v-if="currentRestoreTask">
            <el-button 
              v-if="canCancelRestore(currentRestoreTask.status)"
              type="warning"
              @click="cancelCurrentRestore"
              :loading="cancelling"
            >
              取消恢复
            </el-button>
            <el-button @click="goToRestoreManagement">
              查看详情
            </el-button>
            <el-button 
              @click="closeRestoreDialog"
              :disabled="currentRestoreTask.status === 'running'"
            >
              {{ currentRestoreTask.status === 'running' ? '恢复中...' : '关闭' }}
            </el-button>
          </template>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Refresh, FolderOpened, SuccessFilled, Coin, TrendCharts,
  View, Download, RefreshLeft, Delete, Loading, Close
} from '@element-plus/icons-vue'
import backupApi from '@/api/backup'

// 路由
const router = useRouter()

// 响应式数据
const loading = ref(false)
const creating = ref(false)
const stats = ref({})
const backups = ref([])

// 实时监控相关
const pollingInterval = ref(null)
const pollingEnabled = ref(true)
const POLLING_INTERVAL = 3000 // 3秒轮询间隔

// 计算属性：运行中的备份
const runningBackups = computed(() => {
  return backups.value.filter(backup => {
    // 只显示真正运行中或等待中的任务
    if (!['pending', 'running'].includes(backup.status)) {
      return false
    }
    
    // 如果是运行中状态但有完成时间，说明状态不同步，排除
    if (backup.status === 'running' && backup.completed_at) {
      return false
    }
    
    return true
  })
})

// 分页数据
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0,
  pages: 1
})

// 过滤条件
const filters = reactive({
  backup_type: '',
  status: ''
})

// 创建备份对话框
const createDialog = reactive({
  visible: false
})

const createForm = reactive({
  backup_type: 'full',
  include_database: true,
  include_files: true,
  description: ''
})

const createRules = {
  backup_type: [
    { required: true, message: '请选择备份类型', trigger: 'change' }
  ]
}

// 备份详情对话框
const detailDialog = reactive({
  visible: false,
  backup: null
})

// 获取备份统计
const getBackupStats = async () => {
  try {
    const response = await backupApi.getStatistics()
    console.log('统计数据响应:', response)
    stats.value = response.data?.data || response.data || {}
  } catch (error) {
    console.error('获取备份统计失败:', error)
    ElMessage.error('获取备份统计失败: ' + (error.message || '网络错误'))
    stats.value = {} // 提供默认值
  }
}

// 获取备份列表
const getBackupList = async () => {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      ...filters
    }
    
    const response = await backupApi.getBackupRecords(params)
    console.log('备份列表响应:', response)
    
    // 处理不同的响应结构
    const data = response.data?.data || response.data || {}
    backups.value = data.records || []
    pagination.total = data.total || 0
    pagination.pages = data.pages || 1
  } catch (error) {
    console.error('获取备份列表失败:', error)
    ElMessage.error('获取备份列表失败: ' + (error.message || '网络错误'))
    backups.value = [] // 提供默认值
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshBackups = async () => {
  try {
    await Promise.all([
      getBackupStats(),
      getBackupList()
    ])
  } catch (error) {
    console.error('刷新数据失败:', error)
    // 不显示错误消息，因为单个函数已经处理了错误
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  createDialog.visible = true
}

// 重置创建表单
const resetCreateForm = () => {
  Object.assign(createForm, {
    backup_type: 'full',
    include_database: true,
    include_files: true,
    description: ''
  })
}

// 创建备份
const createBackup = async () => {
  try {
    creating.value = true
    console.log('创建备份数据:', createForm)
    
    const response = await backupApi.createBackup(createForm)
    console.log('创建备份响应:', response)
    
    ElMessage.success('备份创建成功！正在后台执行备份任务...')
    createDialog.visible = false
    resetCreateForm()
    
    // 立即刷新以显示新创建的备份
    await refreshBackups()
    
    // 立即启动轮询监控，无论是否检测到运行中任务
    // 因为任务可能正在初始化或快速执行
    startPolling()
    
    // 显示实时监控提示
    ElMessage.info({
      message: '备份任务已开始，正在监控进度...',
      duration: 5000,
      showClose: true
    })
  } catch (error) {
    console.error('创建备份失败:', error)
    ElMessage.error('创建备份失败: ' + (error.response?.data?.message || error.message || '网络错误'))
  } finally {
    creating.value = false
  }
}

// 开始轮询监控
const startPolling = () => {
  if (pollingInterval.value) return // 避免重复启动
  
  pollingInterval.value = setInterval(async () => {
    if (!pollingEnabled.value) return
    
    try {
      // 静默刷新，不显示加载状态
      const params = {
        page: pagination.page,
        per_page: pagination.per_page,
        ...filters
      }
      
      const response = await backupApi.getBackupRecords(params)
      const data = response.data?.data || response.data || {}
      const newBackups = data.records || []
      
      // 检查是否有状态变化
      const hasRunningBackups = newBackups.some(backup => 
        ['pending', 'running'].includes(backup.status)
      )
      
      // 更新数据
      backups.value = newBackups
      pagination.total = data.total || 0
      
      // 同时更新统计信息
      const statsResponse = await backupApi.getStatistics()
      stats.value = statsResponse.data?.data || statsResponse.data || {}
      
      // 如果没有运行中的备份，等待一段时间后停止轮询
      // 防止快速完成的任务无法显示
      if (!hasRunningBackups) {
        setTimeout(() => {
          // 再次检查是否有新的运行中任务
          const stillNoRunning = backups.value.filter(backup => 
            ['pending', 'running'].includes(backup.status)
          ).length === 0
          
          if (stillNoRunning) {
            stopPolling()
            ElMessage.success('所有备份任务已完成！')
          }
        }, 5000) // 等待5秒
      }
    } catch (error) {
      console.error('轮询更新失败:', error)
      // 网络错误时继续轮询，但降低频率
      if (pollingInterval.value) {
        clearInterval(pollingInterval.value)
        pollingInterval.value = setTimeout(() => {
          if (pollingEnabled.value) startPolling()
        }, 10000) // 10秒后重试
      }
    }
  }, POLLING_INTERVAL)
}

// 停止轮询监控
const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

// 取消备份
const cancelBackup = async (backup) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消备份 ${backup.backup_id} 吗？`,
      '取消备份',
      {
        confirmButtonText: '确定取消',
        cancelButtonText: '继续备份',
        type: 'warning'
      }
    )
    
    // TODO: 实现取消备份的API
    ElMessage.info('取消备份功能正在开发中...')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消备份失败: ' + error.message)
    }
  }
}

// 计算运行时长
const getRunningDuration = (startTime) => {
  if (!startTime) return '0秒'
  
  const start = new Date(startTime)
  const now = new Date()
  const duration = Math.floor((now - start) / 1000)
  
  if (duration < 60) {
    return `${duration}秒`
  } else if (duration < 3600) {
    const minutes = Math.floor(duration / 60)
    const seconds = duration % 60
    return `${minutes}分${seconds}秒`
  } else {
    const hours = Math.floor(duration / 3600)
    const minutes = Math.floor((duration % 3600) / 60)
    return `${hours}时${minutes}分`
  }
}

// 显示备份详情
const showBackupDetail = (backup) => {
  detailDialog.backup = backup
  detailDialog.visible = true
}

// 下载备份
const downloadBackup = async (backup) => {
  try {
    ElMessage.info('开始下载备份文件...')
    await backupApi.downloadBackup(backup.backup_id)
  } catch (error) {
    ElMessage.error('下载备份失败: ' + error.message)
  }
}

// 恢复选项
const restoreOptions = ref({
  restore_type: 'full', // full, database_only, files_only, partial
  target_path: '',
  include_database: true,
  include_files: true,
  test_mode: false
})

// 恢复对话框显示状态
const restoreDialogVisible = ref(false)
const currentRestoreBackup = ref(null)
const restoring = ref(false)

// 恢复进度监控
const currentRestoreTask = ref(null)
const cancelling = ref(false)
let restoreProgressTimer = null

// 显示恢复对话框
const showRestoreDialog = (backup) => {
  currentRestoreBackup.value = backup
  restoreOptions.value = {
    restore_type: 'full',
    target_path: '',
    include_database: true,
    include_files: true,
    test_mode: false
  }
  restoreDialogVisible.value = true
}

// 执行恢复
const performRestore = async () => {
  if (!currentRestoreBackup.value) return
  
  try {
    restoring.value = true
    
    const options = {
      restore_type: restoreOptions.value.restore_type,
      options: {
        include_database: restoreOptions.value.include_database,
        include_files: restoreOptions.value.include_files,
        test_mode: restoreOptions.value.test_mode
      }
    }
    
    if (restoreOptions.value.target_path) {
      options.target_path = restoreOptions.value.target_path
    }
    
    const response = await backupApi.restoreBackup(currentRestoreBackup.value.backup_id, options)
    
    // 获取恢复任务ID并开始监控进度
    if (response.data?.data?.restore_id) {
      currentRestoreTask.value = {
        restore_id: response.data.data.restore_id,
        status: 'pending',
        progress: 0,
        status_message: '恢复任务已创建'
      }
      startRestoreProgressMonitoring(response.data.data.restore_id)
    }
    
    ElMessage.success('恢复任务已启动，正在监控进度...')
    
    // 刷新备份列表
    await refreshBackups()
    
  } catch (error) {
    console.error('恢复失败:', error)
    ElMessage.error(`恢复失败: ${error.response?.data?.message || error.message}`)
  } finally {
    restoring.value = false
  }
}

// 开始恢复进度监控
const startRestoreProgressMonitoring = (restoreId) => {
  if (restoreProgressTimer) {
    clearInterval(restoreProgressTimer)
  }
  
  restoreProgressTimer = setInterval(async () => {
    try {
      const response = await backupApi.getRestoreProgress(restoreId)
      if (response.data.code === 0) {
        currentRestoreTask.value = response.data.data
        
        // 如果任务已完成或失败，停止监控
        if (['completed', 'failed', 'cancelled'].includes(response.data.data.status)) {
          stopRestoreProgressMonitoring()
          
          if (response.data.data.status === 'completed') {
            ElMessage.success('恢复任务已完成！')
          } else if (response.data.data.status === 'failed') {
            ElMessage.error(`恢复任务失败: ${response.data.data.status_message || '未知错误'}`)
          } else if (response.data.data.status === 'cancelled') {
            ElMessage.warning('恢复任务已取消')
          }
          
          // 刷新备份列表
          await refreshBackups()
        }
      }
    } catch (error) {
      console.error('获取恢复进度失败:', error)
      stopRestoreProgressMonitoring()
    }
  }, 2000) // 每2秒更新一次
}

// 停止恢复进度监控
const stopRestoreProgressMonitoring = () => {
  if (restoreProgressTimer) {
    clearInterval(restoreProgressTimer)
    restoreProgressTimer = null
  }
}

// 取消当前恢复任务
const cancelCurrentRestore = async () => {
  if (!currentRestoreTask.value) return
  
  try {
    await ElMessageBox.confirm(
      '确定要取消当前恢复任务吗？正在进行的恢复操作将被中止。',
      '确认取消',
      {
        confirmButtonText: '确定取消',
        cancelButtonText: '继续恢复',
        type: 'warning'
      }
    )
    
    cancelling.value = true
    
    await backupApi.cancelRestore(currentRestoreTask.value.restore_id)
    ElMessage.success('恢复任务已取消')
    
    // 停止进度监控
    stopRestoreProgressMonitoring()
    currentRestoreTask.value = null
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消恢复任务失败:', error)
      ElMessage.error(`取消恢复任务失败: ${error.response?.data?.message || error.message}`)
    }
  } finally {
    cancelling.value = false
  }
}

// 跳转到恢复管理页面
const goToRestoreManagement = () => {
  router.push('/admin/restore')
}

// 关闭恢复对话框
const closeRestoreDialog = () => {
  if (currentRestoreTask.value?.status !== 'running') {
    restoreDialogVisible.value = false
    stopRestoreProgressMonitoring()
    currentRestoreTask.value = null
  }
}

// 恢复状态相关工具函数
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

const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'exception'
  return undefined
}

const canCancelRestore = (status) => {
  return ['pending', 'running'].includes(status)
}

// 删除备份
const deleteBackup = async (backup) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除备份 ${backup.backup_id} 吗？此操作不可恢复！`,
      '删除备份',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await backupApi.deleteBackup(backup.backup_id)
    ElMessage.success('备份删除成功')
    await refreshBackups()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除备份失败: ' + error.message)
    }
  }
}

// 分页处理
const handleSizeChange = (val) => {
  pagination.per_page = val
  pagination.page = 1
  getBackupList()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  getBackupList()
}

// 工具函数
const formatFileSize = (bytes) => {
  if (!bytes || bytes === '0' || bytes === 0) return '0 B'
  const size = parseInt(bytes) || 0
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

const getBackupTypeLabel = (type) => {
  const labels = {
    full: '全量',
    incremental: '增量',
    snapshot: '快照'
  }
  return labels[type] || type
}

const getBackupTypeTagType = (type) => {
  const types = {
    full: 'primary',
    incremental: 'success',
    snapshot: 'warning'
  }
  return types[type] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return labels[status] || status
}

const getStatusTagType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 监听过滤条件变化
watch([() => filters.backup_type, () => filters.status], () => {
  pagination.page = 1
  getBackupList()
})

// 组件挂载和卸载
onMounted(async () => {
  await refreshBackups()
  
  // 如果有运行中的备份，自动开始轮询
  if (runningBackups.value.length > 0) {
    startPolling()
    ElMessage.info({
      message: `检测到 ${runningBackups.value.length} 个运行中的备份任务，已开启实时监控`,
      duration: 3000
    })
  }
})

// 页面隐藏时停止轮询，显示时恢复
const handleVisibilityChange = () => {
  if (document.hidden) {
    pollingEnabled.value = false
  } else {
    pollingEnabled.value = true
    // 页面重新显示时，如果有运行中的任务，重新开始轮询
    if (runningBackups.value.length > 0 && !pollingInterval.value) {
      startPolling()
    }
  }
}

// 监听页面可见性变化
document.addEventListener('visibilitychange', handleVisibilityChange)

onUnmounted(() => {
  stopPolling()
  stopRestoreProgressMonitoring() // 清理恢复进度监控
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style lang="scss" scoped>
.backup-management {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;

    .header-left {
      .page-title {
        display: flex;
        align-items: center;
        margin: 0 0 8px 0;
        font-size: 28px;
        font-weight: 600;
        color: #1a202c;

        .title-icon {
          margin-right: 12px;
          color: #3182ce;
        }
      }

      .page-description {
        margin: 0;
        color: #718096;
        font-size: 16px;
      }
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }
  }

  .stats-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 24px;

    .stat-card {
      border: none;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

      .stat-content {
        display: flex;
        align-items: center;

        .stat-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 16px;

          &.total {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
          }

          &.success {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
          }

          &.storage {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
          }

          &.rate {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
          }
        }

        .stat-info {
          .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 4px;
          }

          .stat-label {
            font-size: 14px;
            color: #718096;
          }
        }
      }
    }
  }

  .running-backups-card {
    margin-bottom: 24px;
    border: none;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;

    :deep(.el-card__header) {
      background: rgba(255, 255, 255, 0.1);
      border-bottom: 1px solid rgba(255, 255, 255, 0.2);

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .card-title {
          display: flex;
          align-items: center;
          font-size: 18px;
          font-weight: 600;
          color: white;

          .running-icon {
            margin-right: 8px;
            animation: spin 1s linear infinite;
          }
        }
      }
    }

    :deep(.el-card__body) {
      padding: 16px;
    }

    .running-backup-list {
      display: flex;
      flex-direction: column;
      gap: 16px;

      .running-backup-item {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 16px;
        backdrop-filter: blur(10px);
        
        display: grid;
        grid-template-columns: 1fr auto auto;
        gap: 16px;
        align-items: center;

        .backup-info {
          .backup-title {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;

            .backup-id {
              font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
              font-size: 13px;
              color: rgba(255, 255, 255, 0.9);
            }
          }

          .backup-meta {
            display: flex;
            flex-direction: column;
            gap: 4px;

            .time-text, .duration-text {
              font-size: 12px;
              color: rgba(255, 255, 255, 0.8);
            }
          }
        }

        .backup-progress {
          min-width: 200px;

          .progress-text {
            margin-top: 4px;
            text-align: center;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.9);
          }
        }

        .backup-actions {
          display: flex;
          gap: 4px;
        }
      }
    }
  }

  .backup-list-card {
    border: none;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .card-title {
        font-size: 18px;
        font-weight: 600;
        color: #1a202c;
      }

      .filter-controls {
        display: flex;
        gap: 12px;
      }
    }

    .backup-table {
      .backup-id {
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        color: #4a5568;
      }

      .time-text {
        font-size: 13px;
        color: #4a5568;
      }

      .description {
        color: #4a5568;
      }

      .text-muted {
        color: #a0aec0;
      }

      .action-buttons {
        display: flex;
        gap: 4px;
      }
    }

    .pagination-wrapper {
      display: flex;
      justify-content: center;
      margin-top: 20px;
    }
  }

  .backup-options {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .option-detail {
      .option-desc {
        font-size: 12px;
        color: #718096;
        margin-top: 2px;
      }
    }
  }

  .backup-detail {
    .checksum {
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 12px;
      background: #f7fafc;
      padding: 4px 8px;
      border-radius: 4px;
      border: 1px solid #e2e8f0;
      word-break: break-all;
    }

    .storage-providers {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .provider-tag {
        font-size: 12px;
      }
    }
  }

  .option-detail {
    .option-desc {
      font-size: 12px;
      color: #718096;
      margin-top: 2px;
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .backup-management {
    padding: 16px;

    .stats-cards {
      grid-template-columns: 1fr;
    }

    .page-header {
      flex-direction: column;
      gap: 16px;

      .header-actions {
        align-self: stretch;
      }
    }

    .running-backups-card {
      .running-backup-item {
        grid-template-columns: 1fr;
        gap: 12px;

        .backup-progress {
          min-width: auto;
        }
      }
    }
  }
}

// 恢复对话框样式
.restore-warning {
  margin-bottom: 24px;
  
  .risk-list {
    margin: 8px 0 0 0;
    padding-left: 16px;
    
    li {
      margin-bottom: 4px;
      font-size: 13px;
      color: #E6A23C;
    }
  }
}

.backup-info, .restore-options {
  margin-bottom: 24px;
  
  h4 {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }
}

.backup-info {
  .el-descriptions {
    :deep(.el-descriptions__label) {
      font-weight: 500;
    }
  }
}

.restore-options {
  :deep(.el-form-item__label) {
    font-weight: 500;
  }
  
  :deep(.el-select .el-select-dropdown__item) {
    padding: 8px 20px;
  }
}

// 恢复进度监控样式
.restore-progress {
  margin-bottom: 24px;
  
  h4 {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }
  
  .progress-container {
    .progress-info {
      margin-top: 12px;
      
      .status-info {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
        
        .task-id {
          font-size: 12px;
          color: #909399;
          font-family: monospace;
        }
      }
      
      .status-message {
        font-size: 13px;
        color: #606266;
        background: #f5f7fa;
        padding: 8px 12px;
        border-radius: 4px;
        border-left: 3px solid #409eff;
      }
    }
  }
}
</style>