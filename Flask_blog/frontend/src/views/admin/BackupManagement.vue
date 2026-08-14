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
        <el-button type="primary" :loading="creating" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          创建备份
        </el-button>
        <el-button :loading="loading" @click="refreshBackups">
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
          <el-button size="small" :loading="loading" @click="refreshBackups">
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
              <span class="duration-text">{{ backup.status === 'pending' ? '状态' : '已运行' }}: {{ getRunningDuration(backup) }}</span>
            </div>
          </div>
          
          <div class="backup-progress">
            <el-progress 
              :percentage="getBackupProgress(backup)" 
              :status="getProgressStatus(backup)"
              :indeterminate="backup.status === 'running' && (!backup.progress || backup.progress === 0)"
              :duration="3"
            />
            <div class="progress-text">
              <span v-if="backup.status === 'completed'">✅ 备份完成</span>
              <span v-else-if="backup.status === 'failed'">❌ 备份失败</span>
              <span v-else-if="backup.status === 'cancelled'">🚫 已取消</span>
              <span v-else-if="backup.progress && backup.progress > 0">{{ backup.progress }}% - {{ getStatusLabel(backup.status) }}</span>
              <span v-else>{{ getStatusLabel(backup.status) }}...</span>
            </div>
          </div>

          <div class="backup-actions">
            <el-button 
              size="small" 
              title="查看详情"
              @click="showBackupDetail(backup)"
            >
              <el-icon><View /></el-icon>
            </el-button>
            <el-button 
              v-if="backup.status !== 'completed'"
              size="small" 
              type="danger"
              title="取消备份"
              @click="cancelBackup(backup)"
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

      <BackupRecordList
        :backups="backups"
        :loading="loading"
        :pagination="pagination"
        :can-download-backup="canDownloadBackup"
        :can-restore-backup="canRestoreBackup"
        @detail="showBackupDetail"
        @download="downloadBackup"
        @restore="showRestoreDialog"
        @delete="deleteBackup"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </el-card>

    <!-- 创建备份对话框 -->
    <CreateBackupDialog
      :visible="createDialog.visible"
      :creating="creating"
      @update:visible="createDialog.visible = $event"
      @submit="createBackup"
    />

    <!-- 备份详情对话框 -->
    <BackupDetailDialog
      :visible="detailDialog.visible"
      :backup="detailDialog.backup || undefined"
      @update:visible="detailDialog.visible = $event"
    />

    <!-- 恢复备份对话框 -->
    <el-dialog
      v-model="restoreDialogVisible"
      title="恢复备份"
      width="600px"
      :z-index="9999"
      :close-on-click-modal="false"
      append-to-body
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
              <el-select 
                v-model="restoreOptions.restore_type" 
                style="width: 100%"
                placeholder="请选择恢复类型"
                popper-append-to-body
                :teleported="false"
              >
                <el-option value="full" label="完整恢复（数据库 + 文件）">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>完整恢复（数据库 + 文件）</span>
                    <el-tag size="small" type="success">推荐</el-tag>
                  </div>
                </el-option>
                <el-option value="database_only" label="仅恢复数据库">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>仅恢复数据库</span>
                    <el-tag size="small" type="info">安全</el-tag>
                  </div>
                </el-option>
                <el-option value="files_only" label="仅恢复文件">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>仅恢复文件</span>
                    <el-tag size="small" type="warning">谨慎</el-tag>
                  </div>
                </el-option>
                <el-option value="partial" label="自定义恢复">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>自定义恢复</span>
                    <el-tag size="small" type="primary">高级</el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
            

            <div v-if="restoreOptions.restore_type === 'partial'">
              <el-form-item label="恢复内容">
                <el-checkbox v-model="restoreOptions.include_database">包含数据库</el-checkbox>
                <el-checkbox v-model="restoreOptions.include_files" style="margin-left: 16px;">包含文件</el-checkbox>
              </el-form-item>
            </div>

            <el-form-item v-if="restoreOptions.restore_type !== 'database_only'" label="目标路径">
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
            
            <el-form-item>
              <el-alert
                title="恢复说明"
                type="info"
                :closable="false"
                show-icon
              >
                <div style="font-size: 13px;">
                  恢复过程将同步执行，请耐心等待完成。大型备份恢复可能需要几分钟时间。
                </div>
              </el-alert>
            </el-form-item>
          </el-form>
        </div>

        <!-- 恢复进度监控 -->
        <div v-if="currentRestoreTask" class="restore-progress">
          <h4>{{ isTestMode ? '测试验证进度' : '恢复进度' }}</h4>
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
                <el-tag v-if="isTestMode" type="info" size="small">测试模式</el-tag>
              </div>
              <div v-if="currentRestoreTask.status_message" class="status-message">
                {{ currentRestoreTask.status_message }}
              </div>
            </div>
          </div>
          
          <!-- 测试模式结果显示 -->
          <div v-if="isTestMode && currentRestoreTask.status === 'completed' && testResults.length > 0" class="test-results">
            <h5>验证结果:</h5>
            <div class="test-result-list">
              <div
                v-for="(result, index) in testResults"
                :key="index"
                class="test-result-item"
                :class="{
                  'success': result.includes('✅'),
                  'warning': result.includes('⚠️'),
                  'error': result.includes('❌'),
                  'info': result.includes('🗄️') || result.includes('📁')
                }"
              >
                {{ result }}
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
            :loading="restoring"
            :disabled="restoreOptions.restore_type === 'partial' && !restoreOptions.include_database && !restoreOptions.include_files"
            @click="performRestore"
          >
            {{ restoring ? '恢复中，请稍候...' : '开始恢复' }}
          </el-button>

          <!-- 恢复进行中的按钮 -->
          <template v-if="currentRestoreTask">
            <el-button 
              v-if="canCancelRestore(currentRestoreTask.status)"
              type="warning"
              :loading="cancelling"
              @click="cancelCurrentRestore"
            >
              取消恢复
            </el-button>
            <el-button @click="goToRestoreManagement">
              查看详情
            </el-button>
            <el-button 
              :disabled="currentRestoreTask.status === 'running'"
              @click="closeRestoreDialog"
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
import { API } from '@/api'
import BackupDetailDialog from '@/components/backup/BackupDetailDialog.vue'
import BackupRecordList from '@/components/backup/BackupRecordList.vue'
import CreateBackupDialog from '@/components/backup/CreateBackupDialog.vue'
/** @typedef {import('../../types').BackupRecord} BackupRecord */
/** @typedef {import('../../types').RestoreRecord} RestoreRecord */
/** @typedef {{ message?: string, config?: unknown, response?: { status?: number, statusText?: string, data?: { message?: string } } }} ApiError */

// 路由
const router = useRouter()

// 响应式数据
const loading = ref(false)
const creating = ref(false)
/** @type {import('vue').Ref<Record<string, number>>} */
const stats = ref({})
/** @type {import('vue').Ref<BackupRecord[]>} */
const backups = ref([])

// 实时监控相关
/** @type {import('vue').Ref<ReturnType<typeof setInterval> | null>} */
const pollingInterval = ref(null)
const pollingEnabled = ref(true)
const POLLING_INTERVAL = 3000 // 3秒轮询间隔

// 防止并发更新的锁
const isUpdatingBackups = ref(false)

// 计算属性：运行中的备份
const runningBackups = computed(() => {
  return backups.value.filter(backup => {
    // 只显示真正运行中或等待中的任务
    if (!['pending', 'running'].includes(backup.status || '')) {
      return false
    }
    
    // 如果是运行中状态但有完成时间，说明状态不同步，排除
    if (backup.status === 'running' && backup.completed_at) {
      return false
    }
    
    // 排除已取消的任务
    if (backup.status === 'cancelled') {
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

// 备份详情对话框
const detailDialog = reactive({
  visible: false,
  /** @type {BackupRecord | null} */
  backup: null
})

// 获取备份统计
const getBackupStats = async () => {
  try {
    console.log('🔄 开始获取备份统计...')
    const response = await API.getBackupStatistics()
    console.log('✅ 统计数据响应:', response)
    stats.value = response.data?.data || response.data || {}
    console.log('📊 设置统计数据:', stats.value)
  } catch (error) {
    const err = /** @type {ApiError} */ (error)
    console.error('❌ 获取备份统计失败:', error)
    console.error('❌ 错误详情:', {
      status: err.response?.status,
      statusText: err.response?.statusText,
      data: err.response?.data,
      message: err.message
    })
    
    // 设置默认统计数据，避免页面显示异常
    stats.value = {
      total_backups: 0,
      completed_backups: 0,
      total_storage_size: 0,
      success_rate: 0
    }
    
    // 只在非首次加载时显示错误消息
    if (Object.keys(stats.value).length > 4) {
      ElMessage.error('获取备份统计失败: ' + (err.response?.data?.message || err.message || '网络错误'))
    }
    
    throw error // 重新抛出错误供上层处理
  }
}

// 获取备份列表
const getBackupList = async () => {
  try {
    console.log('🔄 开始获取备份列表...')
    loading.value = true
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      ...filters
    }
    console.log('🔄 请求参数:', params)
    
      const response = await API.getBackupRecords(params)
    console.log('✅ 备份列表响应:', response)
    
    // 处理不同的响应结构
    const data = response.data?.data || response.data || {}
    console.log('📋 解析的数据:', data)
    backups.value = data.records || []
    pagination.total = data.total || 0
    pagination.pages = data.pages || 1
    console.log('📋 设置备份列表:', backups.value.length, '条记录')
  } catch (error) {
    const err = /** @type {ApiError} */ (error)
    console.error('❌ 获取备份列表失败:', error)
    console.error('❌ 错误详情:', {
      status: err.response?.status,
      statusText: err.response?.statusText,
      data: err.response?.data,
      message: err.message,
      config: err.config
    })
    
    // 设置默认值，避免页面显示异常
    backups.value = []
    pagination.total = 0
    pagination.pages = 1
    
    // 只在非首次加载时显示错误消息
    if (backups.value.length > 0) {
      ElMessage.error('获取备份列表失败: ' + (err.response?.data?.message || err.message || '网络错误'))
    }
    
    throw error // 重新抛出错误供上层处理
  } finally {
    loading.value = false
    console.log('🔄 备份列表请求完成，loading设为false')
  }
}

// 刷新数据
const refreshBackups = async () => {
  // 防止并发更新
  if (isUpdatingBackups.value) {
    console.log('🔒 备份数据正在更新中，跳过此次刷新请求')
    return
  }
  
  isUpdatingBackups.value = true
  
  // 减少超时时间，避免阻塞页面加载
  const refreshTimeout = setTimeout(() => {
    if (loading.value) {
      loading.value = false
      console.error('❌ 请求超时，停止加载状态')
      // 页面初始化时不显示超时错误，避免干扰用户
      if (backups.value.length === 0) {
        ElMessage.error('数据加载超时，请点击刷新按钮重试')
      }
    }
  }, 15000) // 15秒超时，原来是30秒太长

  try {
    console.log('🔄 开始刷新所有数据...')
    // 同时请求统计和列表数据，但不让任一失败影响整体
    const results = await Promise.allSettled([
      getBackupStats(),
      getBackupList()
    ])
    
    // 检查结果
    const [statsResult, listResult] = results
    if (statsResult.status === 'rejected') {
      console.error('❌ 统计数据获取失败:', statsResult.reason)
    }
    if (listResult.status === 'rejected') {
      console.error('❌ 备份列表获取失败:', listResult.reason)
    }
    
    // 只要有一个成功就认为刷新成功
    if (statsResult.status === 'fulfilled' || listResult.status === 'fulfilled') {
      console.log('✅ 数据刷新完成')
    } else {
      console.error('❌ 所有数据请求都失败')
      throw new Error('所有数据请求都失败')
    }
  } catch (error) {
    console.error('❌ 刷新数据失败:', error)
    loading.value = false // 确保loading状态被清除
    // 只在已有数据的情况下显示错误（非首次加载）
    if (backups.value.length > 0 || Object.keys(stats.value).length > 0) {
      ElMessage.error('数据刷新失败，请检查网络连接')
    }
    throw error // 重新抛出错误，让调用方处理
  } finally {
    isUpdatingBackups.value = false
    clearTimeout(refreshTimeout)
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  createDialog.visible = true
}

// 创建备份
/** @param {Record<string, unknown>} createForm */
const createBackup = async (createForm) => {
  try {
    creating.value = true
    console.log('创建备份数据:', createForm)
    
    const response = await API.createBackup(createForm)
    console.log('创建备份响应:', response)
    
    ElMessage.success('备份创建成功！正在后台执行备份任务...')
    createDialog.visible = false
    
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
    const err = /** @type {ApiError} */ (error)
    ElMessage.error('创建备份失败: ' + (err.response?.data?.message || err.message || '网络错误'))
  } finally {
    creating.value = false
  }
}

// 开始轮询监控
const startPolling = () => {
  if (pollingInterval.value) return // 避免重复启动
  
  pollingInterval.value = setInterval(async () => {
    if (!pollingEnabled.value) return
    
    // 如果正在更新数据，跳过此次轮询
    if (isUpdatingBackups.value) {
      console.log('🔒 备份数据更新中，跳过轮询')
      return
    }
    
    try {
      // 设置更新锁，防止与手动刷新冲突
      isUpdatingBackups.value = true
      
      // 静默刷新，不显示加载状态
      const params = {
        page: pagination.page,
        per_page: pagination.per_page,
        ...filters
      }
      
    const response = await API.getBackupRecords(params)
      const data = response.data?.data || response.data || {}
      /** @type {BackupRecord[]} */
      const newBackups = data.records || []
      
      // 检查是否有状态变化
      const hasRunningBackups = newBackups.some((backup) => 
        ['pending', 'running'].includes(backup.status || '')
      )
      
      // 更新数据
      backups.value = newBackups
      pagination.total = data.total || 0
      
      // 同时更新统计信息
      const statsResponse = await API.getBackupStatistics()
      stats.value = statsResponse.data?.data || statsResponse.data || {}
      
      // 如果没有运行中的备份，等待一段时间后停止轮询
      // 防止快速完成的任务无法显示
      if (!hasRunningBackups) {
        setTimeout(() => {
          // 再次检查是否有新的运行中任务
          const stillNoRunning = backups.value.filter(backup => 
            ['pending', 'running'].includes(backup.status || '')
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
    } finally {
      // 确保释放更新锁
      isUpdatingBackups.value = false
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
/** @param {BackupRecord} backup */
const cancelBackup = async (backup) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消备份任务 "${backup.backup_id}" 吗？\n\n取消后该备份任务将停止执行，已生成的部分数据将被清理。`,
      '取消备份任务',
      {
        confirmButtonText: '确定取消',
        cancelButtonText: '继续备份',
        type: 'warning'
      }
    )
    
    console.log('🚫 用户确认取消备份:', backup.backup_id)
    
    const response = await API.cancelBackup(backup.backup_id)
    
    if (response.data?.code === 0) {
      ElMessage.success(`备份任务 "${backup.backup_id}" 已取消`)
      
      // 立即刷新备份列表
      await refreshBackups()
      
      console.log('✅ 备份取消成功，列表已刷新')
    } else {
      throw new Error(response.data?.message || '取消失败')
    }
    
  } catch (error) {
    if (error !== 'cancel') {
      const err = /** @type {ApiError} */ (error)
      console.error('❌ 取消备份失败:', error)
      ElMessage.error('取消备份失败: ' + (err.response?.data?.message || err.message))
    }
  }
}

// 判断备份是否可以下载
/** @param {BackupRecord} backup */
const canDownloadBackup = (backup) => {
  // 完成状态的备份肯定可以下载
  if (backup.status === 'completed') return true
  
  // 对于取消状态的备份，只有在有任何文件相关信息时才显示下载按钮
  // 包括文件路径、文件大小或校验和，任何一个存在都表明可能有备份文件
  if (backup.status === 'cancelled' && 
      (backup.file_path || 
       (backup.file_size && backup.file_size > 0) || 
       backup.checksum)) {
    return true
  }
  
  // 其他状态不能下载
  return false
}

// 判断备份是否可以用于恢复
/** @param {BackupRecord} backup */
const canRestoreBackup = (backup) => {
  // 完成状态的备份肯定可以恢复
  if (backup.status === 'completed') return true
  
  // 取消状态的备份也应该允许尝试恢复
  // 因为可能在备份完成后但在更新数据库前被取消
  // 恢复时后端会验证文件是否真实存在
  if (backup.status === 'cancelled') {
    return true
  }
  
  // 失败或其他状态不能恢复
  return false
}

// 获取备份进度百分比
/** @param {BackupRecord} backup */
const getBackupProgress = (backup) => {
  if (backup.status === 'completed') return 100
  if (backup.status === 'failed' || backup.status === 'cancelled') return 0
  return backup.progress || 0
}

// 获取进度条状态
/** @param {BackupRecord | string | undefined} backupOrStatus */
const getProgressStatus = (backupOrStatus) => {
  // 兼容两种参数：对象或字符串
  const status = typeof backupOrStatus === 'string' ? backupOrStatus : backupOrStatus?.status
  
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'warning'
  return ''
}

// 计算运行时长
/** @param {BackupRecord} backup */
const getRunningDuration = (backup) => {
  // 如果任务还在pending状态，显示等待时间
  if (backup.status === 'pending') {
    if (!backup.created_at) return '等待中'
    
    const created = new Date(backup.created_at)
    const now = new Date()
    const waitTime = Math.floor((now.getTime() - created.getTime()) / 1000)
    
    if (waitTime < 60) {
      return `等待中 (${waitTime}秒)`
    } else if (waitTime < 3600) {
      const minutes = Math.floor(waitTime / 60)
      return `等待中 (${minutes}分钟)`
    } else {
      const hours = Math.floor(waitTime / 3600)
      const minutes = Math.floor((waitTime % 3600) / 60)
      return `等待中 (${hours}小时${minutes}分钟)`
    }
  }
  
  // 对于running状态，使用started_at或created_at
  const startTime = backup.started_at || backup.created_at
  if (!startTime) return '0秒'
  
  // 处理时区：假设后端返回的时间是上海时区的时间字符串
  // 如果时间字符串没有时区信息，我们需要正确解析
  let start
  try {
    if (startTime.includes('+') || startTime.endsWith('Z')) {
      // 有时区信息的ISO字符串
      start = new Date(startTime)
    } else {
      // 无时区信息，假设为上海时间 (UTC+8)
      // 将上海时间转换为本地时间进行比较
      const shangaiTime = new Date(startTime + '+08:00')
      start = shangaiTime
    }
  } catch (e) {
    // 备用解析方式
    start = new Date(startTime)
  }
  
  const now = new Date()
  const duration = Math.floor((now.getTime() - start.getTime()) / 1000)
  
  // 如果计算出负数时间，说明时区处理有问题，显示警告
  if (duration < 0) {
    return '时间异常'
  }
  
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
/** @param {BackupRecord} backup */
const showBackupDetail = (backup) => {
  detailDialog.backup = backup
  detailDialog.visible = true
}

// 下载备份
/** @param {BackupRecord} backup */
const downloadBackup = async (backup) => {
  try {
    ElMessage.info('开始下载备份文件...')
    await API.downloadBackup(backup.backup_id)
  } catch (error) {
    const err = /** @type {ApiError} */ (error)
    ElMessage.error('下载备份失败: ' + (err.message || '网络错误'))
  }
}

// 恢复选项
/** @type {import('vue').Ref<{ restore_type: string, target_path: string, include_database: boolean, include_files: boolean, test_mode: boolean }>} */
const restoreOptions = ref({
  restore_type: 'full', // full, database_only, files_only, partial
  target_path: '',
  include_database: true,
  include_files: true,
  test_mode: false
})


// 恢复对话框显示状态
const restoreDialogVisible = ref(false)
/** @type {import('vue').Ref<BackupRecord | null>} */
const currentRestoreBackup = ref(null)
const restoring = ref(false)

// 恢复进度监控
/** @type {import('vue').Ref<RestoreRecord | null>} */
const currentRestoreTask = ref(null)
const cancelling = ref(false)
/** @type {ReturnType<typeof setTimeout> | null} */
let restoreProgressTimer = null

// 测试结果
/** @type {import('vue').Ref<string[]>} */
const testResults = ref([])

// 计算属性：是否为测试模式
const isTestMode = computed(() => {
  return restoreOptions.value.test_mode
})

// 显示恢复对话框
/** @param {BackupRecord} backup */
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
    
    /** @type {{ restore_type: string, target_path?: string, options: { include_database: boolean, include_files: boolean, test_mode: boolean } }} */
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
    
    const response = await API.restoreBackup(currentRestoreBackup.value.backup_id, options)
    
    console.log('恢复任务响应:', response.data) // 添加调试日志
    
    // 处理测试模式结果
    if (restoreOptions.value.test_mode && response.data?.data?.test_results) {
      testResults.value = response.data.data.test_results
      ElMessage.success('测试验证完成！请查看验证结果')
      // 测试模式不关闭对话框，让用户查看结果
    } else {
      // 异步恢复任务已启动，关闭对话框并跳转到恢复管理页面
      ElMessage.success('恢复任务已启动，正在后台执行...')
      restoreDialogVisible.value = false
      
      // 跳转到恢复任务管理页面
      if (response.data?.data?.restore_id) {
        await navigateToRestoreManagement(response.data.data.restore_id)
      } else {
        console.error('响应中缺少restore_id:', response.data)
        ElMessage.warning('恢复任务已启动，但无法自动跳转，请手动前往恢复管理页面查看')
      }
    }
    
    // 刷新备份列表
    await refreshBackups()
    
  } catch (error) {
    console.error('恢复失败:', error)
    const err = /** @type {ApiError} */ (error)
    ElMessage.error(`恢复失败: ${err.response?.data?.message || err.message || '网络错误'}`)
  } finally {
    restoring.value = false
  }
}

// 跳转到恢复任务管理页面
/** @param {string} restoreId */
const navigateToRestoreManagement = async (restoreId) => {
  try {
    // 使用Vue Router进行页面跳转
    await router.push({
      path: '/admin/restore-management',
      query: { 
        highlight: restoreId  // 传递要高亮显示的恢复任务ID
      }
    })
  } catch (error) {
    console.error('导航到恢复管理页面失败:', error)
    ElMessage.warning('无法跳转到恢复管理页面，请手动前往查看')
  }
}

// 开始恢复进度监控
/** @param {string} restoreId */
const startRestoreProgressMonitoring = (restoreId) => {
  if (restoreProgressTimer) {
    clearInterval(restoreProgressTimer)
  }
  
  restoreProgressTimer = setInterval(async () => {
    try {
      const response = await API.getRestoreProgress(restoreId)
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
    
    await API.cancelRestore(currentRestoreTask.value.restore_id)
    ElMessage.success('恢复任务已取消')
    
    // 停止进度监控
    stopRestoreProgressMonitoring()
    currentRestoreTask.value = null
    
  } catch (error) {
    if (error !== 'cancel') {
      const err = /** @type {ApiError} */ (error)
      console.error('取消恢复任务失败:', error)
      ElMessage.error(`取消恢复任务失败: ${err.response?.data?.message || err.message}`)
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

/** @param {string | undefined} status */
const canCancelRestore = (status) => {
  return ['pending', 'running'].includes(status || '')
}

// 删除备份
/** @param {BackupRecord} backup */
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
    
    await API.deleteBackup(backup.backup_id)
    ElMessage.success('备份删除成功')
    await refreshBackups()
  } catch (error) {
    if (error !== 'cancel') {
      const err = /** @type {ApiError} */ (error)
      ElMessage.error('删除备份失败: ' + (err.message || '网络错误'))
    }
  }
}

// 分页处理
/** @param {number | string} val */
const handleSizeChange = (val) => {
  pagination.per_page = Number(val)
  pagination.page = 1
  getBackupList()
}

/** @param {number | string} val */
const handleCurrentChange = (val) => {
  pagination.page = Number(val)
  getBackupList()
}

// 工具函数
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

// 统一使用 getStatusText 函数
const getStatusLabel = getStatusText

// 监听过滤条件变化
watch([() => filters.backup_type, () => filters.status], () => {
  pagination.page = 1
  getBackupList()
})

// 组件挂载和卸载
onMounted(async () => {
  console.log('🔄 BackupManagement 组件挂载')
  console.log('🔄 当前用户信息:', {
    token: localStorage.getItem('access_token') ? '存在' : '不存在',
    role: localStorage.getItem('role')
  })

  try {
    // 检查用户store
    const { useUserStore } = await import('@/stores/user.js');
    const userStore = useUserStore();
    
    console.log('🔄 用户store状态:', {
      isAuthenticated: userStore.isAuthenticated,
      user: userStore.user
    })
    
    // 确保用户已认证
    if (!userStore.isAuthenticated) {
      console.log('🔄 用户未认证，初始化认证状态...')
      await userStore.initAuth()
      console.log('🔄 认证状态初始化完成:', userStore.isAuthenticated)
    }

    console.log('🔄 开始刷新备份数据...')
    // 立即开始数据加载，不等待，并提供用户反馈
    console.time('initial-data-load')
    refreshBackups()
      .then(() => {
        console.timeEnd('initial-data-load')
        console.log('✅ 页面初始化数据加载成功')
        // 如果数据加载成功，给用户视觉反馈
        if (backups.value.length > 0 || Object.keys(stats.value).length > 0) {
          // 轻微的成功反馈，不干扰用户
          console.log('📊 页面数据加载完成:', {
            backups: backups.value.length,
            stats: Object.keys(stats.value).length
          })
        }
      })
      .catch(error => {
        console.timeEnd('initial-data-load')
        console.error('🔄 初始数据加载失败:', error)
        ElMessage.error('初始数据加载失败，请点击刷新按钮重试')
      })
    
    // 如果有运行中的备份，自动开始轮询
    setTimeout(() => {
      if (runningBackups.value.length > 0) {
        startPolling()
        ElMessage.info({
          message: `检测到 ${runningBackups.value.length} 个运行中的备份任务，已开启实时监控`,
          duration: 3000
        })
      }
    }, 1000)
    
  } catch (error) {
    console.error('🔄 组件初始化失败:', error)
    ElMessage.error('页面初始化失败，请刷新页面重试')
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

// 测试结果显示样式
.test-results {
  margin-top: 24px;
  
  h4 {
    margin: 0 0 16px 0;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    display: flex;
    align-items: center;
    
    .el-icon {
      margin-right: 8px;
      color: #67c23a;
    }
  }
  
  .test-result-list {
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    background: #fafafa;
    
    .test-result-item {
      padding: 12px 16px;
      border-bottom: 1px solid #e4e7ed;
      font-family: monospace;
      font-size: 13px;
      line-height: 1.6;
      transition: all 0.3s ease;
      
      &:last-child {
        border-bottom: none;
      }
      
      &:hover {
        background: rgba(64, 158, 255, 0.05);
      }
      
      &.success {
        background: #f0f9ff;
        color: #155724;
        border-left: 4px solid #28a745;
        
        &:hover {
          background: #e3f2fd;
        }
      }
      
      &.warning {
        background: #fffbf0;
        color: #856404;
        border-left: 4px solid #ffc107;
        
        &:hover {
          background: #fff8e1;
        }
      }
      
      &.error {
        background: #fef5f5;
        color: #721c24;
        border-left: 4px solid #dc3545;
        
        &:hover {
          background: #fce4ec;
        }
      }
      
      &.info {
        background: #f8f9fa;
        color: #0c5460;
        border-left: 4px solid #17a2b8;
        
        &:hover {
          background: #e9ecef;
        }
      }
      
      // 添加图标样式
      &::before {
        content: '';
        display: inline-block;
        width: 4px;
        height: 4px;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
      }
      
      &.success::before {
        background: #28a745;
      }
      
      &.warning::before {
        background: #ffc107;
      }
      
      &.error::before {
        background: #dc3545;
      }
      
      &.info::before {
        background: #17a2b8;
      }
    }
  }
}
</style>