<template>
  <div class="log-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">📋 日志管理中心</h1>
        <p class="page-description">查看系统运行日志，监控应用状态和用户行为</p>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" icon="Refresh" @click="refreshLogs">刷新</el-button>
        <el-button type="primary" icon="Download" @click="showExportDialog">导出</el-button>
        <el-button type="danger" icon="Delete" @click="showCleanupDialog">清理</el-button>
      </div>
    </div>

    <!-- 统计面板 -->
    <div class="stats-overview">
      <el-row :gutter="24">
        <el-col :span="6">
          <el-card class="stat-card total">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <h3>总日志数</h3>
                <div class="stat-number">{{ stats.total || 0 }}</div>
                <div class="stat-trend">全部记录</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card today">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><Calendar /></el-icon>
              </div>
              <div class="stat-info">
                <h3>今日日志</h3>
                <div class="stat-number">{{ stats.today || 0 }}</div>
                <div class="stat-trend">今天新增</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card errors">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="stat-info">
                <h3>错误数</h3>
                <div class="stat-number">{{ stats.errors || 0 }}</div>
                <div class="stat-trend">需要关注</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card warnings">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><InfoFilled /></el-icon>
              </div>
              <div class="stat-info">
                <h3>警告数</h3>
                <div class="stat-number">{{ stats.warnings || 0 }}</div>
                <div class="stat-trend">监控中</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 过滤控制条 -->
    <el-card class="filter-card">
      <div class="filter-controls">
        <div class="filter-row">
          <div class="filter-item">
            <label>关键词搜索</label>
            <el-input
              v-model="filters.keyword"
              placeholder="搜索日志内容..."
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
          
          <div class="filter-item">
            <label>日志级别</label>
            <el-select v-model="filters.level" placeholder="全部级别" clearable>
              <el-option label="全部" value="" />
              <el-option label="错误" value="ERROR" />
              <el-option label="警告" value="WARNING" />
              <el-option label="信息" value="INFO" />
              <el-option label="调试" value="DEBUG" />
            </el-select>
          </div>
          
          <div class="filter-item">
            <label>日志来源</label>
            <el-select v-model="filters.source" placeholder="全部来源" clearable filterable>
              <el-option label="全部" value="" />
              <el-option
                v-for="source in availableSources"
                :key="source"
                :label="source"
                :value="source"
              />
            </el-select>
          </div>
        </div>
        
        <div class="filter-row">
          <div class="filter-item time-range">
            <label>时间范围</label>
            <el-date-picker
              v-model="filters.timeRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
          </div>
          
          <div class="filter-item">
            <label>用户筛选</label>
            <el-select v-model="filters.userId" placeholder="全部用户" clearable filterable>
              <el-option label="全部" :value="''" />
              <el-option
                v-for="user in availableUsers"
                :key="user.id"
                :label="user.name"
                :value="user.id"
              />
            </el-select>
          </div>
          
          <div class="filter-actions">
            <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
            <el-button icon="RefreshLeft" @click="resetFilters">重置</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 日志表格 -->
    <el-card class="table-card">
      <template #header>
        <div class="table-header">
          <span>日志列表</span>
          <div class="table-actions">
            <el-switch
              v-model="autoRefresh"
              active-text="自动刷新"
              inactive-text="手动刷新"
              @change="toggleAutoRefresh"
            />
          </div>
        </div>
      </template>
      
      <el-table
        v-loading="loading"
        :data="logs"
        stripe
        style="width: 100%"
        :default-sort="{ prop: 'timestamp', order: 'descending' }"
        @row-click="showLogDetail"
      >
        <el-table-column prop="timestamp" label="时间" width="180" sortable>
          <template #default="{ row }">
            <el-tooltip :content="formatFullTime(row.timestamp)" placement="top">
              <span>{{ formatTime(row.timestamp) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        
        <el-table-column prop="level" label="级别" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="source" label="来源" width="120" sortable show-overflow-tooltip />
        
        <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-html="highlightKeyword(row.message)" />
          </template>
        </el-table-column>
        
        <el-table-column prop="user_name" label="用户" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.user_name">{{ row.user_name }}</span>
            <span v-else class="text-muted">系统</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="ip_address" label="IP地址" width="140" show-overflow-tooltip />
        
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              type="text"
              size="small"
              icon="View"
              @click.stop="showLogDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 日志详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="日志详情"
      width="80%"
      :before-close="handleDetailClose"
    >
      <div v-if="selectedLog" class="log-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="日志ID">
            {{ selectedLog.id }}
          </el-descriptions-item>
          <el-descriptions-item label="时间">
            {{ formatFullTime(selectedLog.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="级别">
            <el-tag :type="getLevelType(selectedLog.level)">
              {{ selectedLog.level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ selectedLog.source }}
          </el-descriptions-item>
          <el-descriptions-item label="用户">
            {{ selectedLog.user_name || '系统' }}
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">
            {{ selectedLog.ip_address || '-' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.request_id" label="请求ID">
            {{ selectedLog.request_id }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.endpoint" label="端点">
            {{ selectedLog.endpoint }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.method" label="HTTP方法">
            {{ selectedLog.method }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.status_code" label="状态码">
            {{ selectedLog.status_code }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.duration_ms" label="耗时">
            {{ selectedLog.duration_ms }}ms
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.user_agent" label="User-Agent" :span="2">
            {{ selectedLog.user_agent }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="log-message">
          <h4>详细消息</h4>
          <el-input
            type="textarea"
            :rows="4"
            :value="selectedLog.message"
            readonly
          />
        </div>
        
        <div v-if="selectedLog.extra_data" class="log-extra-data">
          <h4>额外数据</h4>
          <el-input
            type="textarea"
            :rows="8"
            :value="formatJSON(selectedLog.extra_data)"
            readonly
          />
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button 
            v-if="selectedLog && selectedLog.request_id"
            type="primary"
            @click="searchRelatedLogs"
          >
            查看相关日志
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 导出对话框 -->
    <el-dialog v-model="exportVisible" title="导出日志" width="500px">
      <el-form :model="exportForm" label-width="80px">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio label="json">JSON</el-radio>
            <el-radio label="csv">CSV</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="导出数量">
          <el-select v-model="exportForm.limit">
            <el-option label="100条" :value="100" />
            <el-option label="500条" :value="500" />
            <el-option label="1000条" :value="1000" />
            <el-option label="5000条" :value="5000" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="exportVisible = false">取消</el-button>
          <el-button type="primary" :loading="exporting" @click="handleExport">
            导出
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 清理对话框 -->
    <el-dialog v-model="cleanupVisible" title="清理日志" width="500px">
      <div class="cleanup-warning">
        <el-alert
          title="危险操作"
          description="此操作将永久删除指定天数之前的所有日志记录，请谨慎操作！"
          type="warning"
          show-icon
          :closable="false"
        />
      </div>
      
      <el-form :model="cleanupForm" label-width="80px" style="margin-top: 20px;">
        <el-form-item label="保留天数">
          <el-input-number
            v-model="cleanupForm.days"
            :min="1"
            :max="365"
            placeholder="请输入保留天数"
          />
          <div class="form-tip">将删除 {{ cleanupForm.days }} 天前的所有日志</div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cleanupVisible = false">取消</el-button>
          <el-button type="danger" :loading="cleaning" @click="handleCleanup">
            确认清理
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document, Calendar, Warning, InfoFilled, Search,
  Refresh, Download, Delete, View, RefreshLeft
} from '@element-plus/icons-vue'
import { API } from '@/api'

// 响应式数据
const loading = ref(false)
/** @type {import('vue').Ref<import('@/types').LogEntry[]>} */
const logs = ref([])
const stats = reactive({
  total: 0,
  today: 0,
  errors: 0,
  warnings: 0
})

// 过滤条件
const filters = reactive({
  keyword: '',
  level: '',
  source: '',
  userId: null,
  timeRange: []
})

// 分页
const pagination = reactive({
  page: 1,
  size: 50,
  total: 0
})

// 可用选项
/** @type {import('vue').Ref<string[]>} */
const availableSources = ref([])
/** @type {import('vue').Ref<Array<{ id: number, name: string }>>} */
const availableUsers = ref([])

// 对话框状态
const detailVisible = ref(false)
const exportVisible = ref(false)
const cleanupVisible = ref(false)
/** @type {import('vue').Ref<import('@/types').LogEntry | null>} */
const selectedLog = ref(null)

// 自动刷新
const autoRefresh = ref(false)
/** @type {ReturnType<typeof setInterval> | null} */
let refreshTimer = null

// 导出和清理表单
const exportForm = reactive({
  format: 'json',
  limit: 1000
})

const cleanupForm = reactive({
  days: 30
})

const exporting = ref(false)
const cleaning = ref(false)

// 加载日志列表（增加防抖与首轮重试）
let loadingLogsOnce = false
const loadLogs = async (retry=false) => {
  try {
    loading.value = true
    // 若无 token 且未重试，延迟再试
    const token = localStorage.getItem('access_token')
    if(!token){
      if(!retry){
        console.debug('[logs] no token yet, schedule retry')
        setTimeout(()=>loadLogs(true), 180)
      }
      return
    }
    if(loadingLogsOnce && !retry){
      // 避免并发重复
      return
    }
    loadingLogsOnce = true

    const params = {
      page: pagination.page,
      size: pagination.size,
      level: filters.level,
      source: filters.source,
      keyword: filters.keyword,
      user_id: filters.userId,
      start_time: null,
      end_time: null
    }
    
    // 添加时间范围
    if (filters.timeRange && filters.timeRange.length === 2) {
      params.start_time = filters.timeRange[0]
      params.end_time = filters.timeRange[1]
    }
    console.log("请求参数:", params)
  // 改为 POST 以使用新的 /admin/logs/query 端点，规避首个 GET 401 问题
  const response = await API.queryLogs(params)
    
    if (response.data.code === 0) {
      logs.value = response.data.data.logs
      pagination.total = response.data.data.total
    } else {
      ElMessage.error(response.data.message || '加载日志失败')
    }
  } catch (error) {
    console.error('加载日志失败:', error)
    // 自动一次重试（只在有token但仍失败时）
    if(!retry && localStorage.getItem('access_token')){
      console.debug('[logs] first attempt failed, retry in 200ms')
      setTimeout(()=>loadLogs(true), 200)
    } else {
      ElMessage.error('加载日志失败')
    }
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await API.getLogStats()
    
    if (response.data.code === 0) {
      Object.assign(stats, response.data.data)
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 加载可用选项
const loadOptions = async () => {
  try {
    // 加载日志来源
    const sourcesResponse = await API.getLogSources()
    if (sourcesResponse.data.code === 0) {
      // 过滤掉null和空值
      availableSources.value = (sourcesResponse.data.data || []).filter(/** @param {unknown} source */ (source) => source)
    }
    
    // 加载用户列表
    const usersResponse = await API.getLogUsers()
    if (usersResponse.data.code === 0) {
      // 过滤掉null和空值
      availableUsers.value = (usersResponse.data.data || []).filter(/** @param {{ id?: number }} user */ (user) => user && user.id)
    }
  } catch (error) {
    console.error('加载选项失败:', error)
  }
}

// 处理搜索
const handleSearch = () => {
  pagination.page = 1
  loadLogs()
}

// 重置过滤条件
const resetFilters = () => {
  Object.assign(filters, {
    keyword: '',
    level: '',
    source: '',
    userId: null,
    timeRange: []
  })
  handleSearch()
}

// 刷新日志
const refreshLogs = async () => {
  await Promise.all([loadLogs(), loadStats()])
  ElMessage.success('刷新成功')
}

// 分页处理
/** @param {number} page */
const handlePageChange = (page) => {
  pagination.page = page
  loadLogs()
}

/** @param {number} size */
const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  loadLogs()
}

// 显示日志详情
/** @param {import('@/types').LogEntry} row */
const showLogDetail = (row) => {
  selectedLog.value = row
  detailVisible.value = true
}

const handleDetailClose = () => {
  detailVisible.value = false
  selectedLog.value = null
}

// 搜索相关日志
const searchRelatedLogs = () => {
  if (selectedLog.value && selectedLog.value.request_id) {
    // 设置过滤条件为request_id并搜索
    resetFilters()
    // 这里应该添加按request_id搜索的逻辑
    handleDetailClose()
    ElMessage.info('功能开发中：搜索相关日志')
  }
}

// 自动刷新
/** @param {string | number | boolean} enabled */
const toggleAutoRefresh = (enabled) => {
  if (enabled) {
    refreshTimer = setInterval(() => {
      loadLogs()
    }, 30000) // 30秒刷新一次
    ElMessage.success('已开启自动刷新（30秒间隔）')
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    ElMessage.info('已关闭自动刷新')
  }
}

// 导出功能
const showExportDialog = () => {
  exportVisible.value = true
}

const handleExport = async () => {
  try {
    exporting.value = true
    
    const params = {
      format: exportForm.format,
      limit: exportForm.limit,
      level: filters.level,
      source: filters.source,
      keyword: filters.keyword,
      start_time: null,
      end_time: null
    }
    
    if (filters.timeRange && filters.timeRange.length === 2) {
      params.start_time = filters.timeRange[0]
      params.end_time = filters.timeRange[1]
    }
    
    const response = await API.exportLogs(params)
    
    if (response.data.code === 0) {
      // 创建下载链接
      const dataStr = JSON.stringify(response.data.data, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `logs_export_${new Date().toISOString().slice(0, 10)}.${exportForm.format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      ElMessage.success('导出成功')
      exportVisible.value = false
    } else {
      ElMessage.error(response.data.message || '导出失败')
    }
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 清理功能
const showCleanupDialog = () => {
  cleanupVisible.value = true
}

const handleCleanup = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${cleanupForm.days} 天前的所有日志吗？此操作不可恢复！`,
      '确认清理',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    cleaning.value = true
    
    const response = await API.cleanupLogs({
      days: cleanupForm.days
    })
    
    if (response.data.code === 0) {
      const deletedCount = response.data.data.deleted_count
      ElMessage.success(`清理完成，删除了 ${deletedCount} 条日志记录`)
      cleanupVisible.value = false
      await refreshLogs()
    } else {
      ElMessage.error(response.data.message || '清理失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清理失败:', error)
      ElMessage.error('清理失败')
    }
  } finally {
    cleaning.value = false
  }
}

// 工具函数
/** @param {string | number | Date | null | undefined} timestamp */
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

/** @param {string | number | Date | null | undefined} timestamp */
const formatFullTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

/** @param {unknown} data */
const formatJSON = (data) => {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

/** @param {string | undefined} level @returns {'danger' | 'warning' | 'info'} */
const getLevelType = (level) => {
  /** @type {Record<string, 'danger' | 'warning' | 'info'>} */
  const typeMap = {
    ERROR: 'danger',
    WARNING: 'warning',
    INFO: 'info',
    DEBUG: 'info'
  }
  return typeMap[level || ''] || 'info'
}

/** @param {string | undefined} text */
const highlightKeyword = (text) => {
  if (!filters.keyword || !text) return text
  const regex = new RegExp(`(${filters.keyword})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

// 生命周期
async function waitForToken(maxMs=2000){
  const start = Date.now()
  while(!localStorage.getItem('access_token') && Date.now()-start < maxMs){
    await new Promise(r=>setTimeout(r,100))
  }
  return !!localStorage.getItem('access_token')
}

onMounted(async () => {
  await waitForToken()
  // 首次加载使用 POST 查询端点，避免历史上首个 GET /admin/logs 可能出现的丢失 Authorization 现象
  await loadLogs()
  // 轻微延迟启动统计与选项，避免首批拥挤
  setTimeout(()=>{ loadStats() }, 50)
  setTimeout(()=>{ loadOptions() }, 80)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.log-management {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 统计面板 */
.stats-overview {
  margin-bottom: 24px;
}

.stat-card {
  height: 120px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0;
}

.stat-icon {
  font-size: 32px;
  margin-right: 16px;
  padding: 12px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-card.total .stat-icon {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
}

.stat-card.today .stat-icon {
  background: linear-gradient(135deg, #10b981, #047857);
  color: white;
}

.stat-card.errors .stat-icon {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.stat-card.warnings .stat-icon {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

.stat-info h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
}

.stat-number {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-trend {
  font-size: 12px;
  color: #9ca3af;
}

/* 过滤控制 */
.filter-card {
  margin-bottom: 24px;
}

.filter-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-item.time-range {
  min-width: 350px;
}

.filter-item label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.filter-item .el-input,
.filter-item .el-select {
  width: 200px;
}

.filter-item.time-range .el-date-editor {
  width: 100%;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

/* 表格 */
.table-card {
  margin-bottom: 24px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* 日志详情 */
.log-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.log-message,
.log-extra-data {
  margin-top: 20px;
}

.log-message h4,
.log-extra-data h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #1f2937;
}

/* 工具样式 */
.text-muted {
  color: #9ca3af;
}

.cleanup-warning {
  margin-bottom: 16px;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

/* 高亮关键词 */
:deep(mark) {
  background-color: #fef3c7;
  color: #92400e;
  padding: 1px 2px;
  border-radius: 2px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-item .el-input,
  .filter-item .el-select {
    width: 100%;
  }
  
  .filter-actions {
    margin-left: 0;
    justify-content: center;
  }
  
  .stats-overview :deep(.el-col) {
    margin-bottom: 12px;
  }
}
</style>