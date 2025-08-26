<template>
  <div class="simple-log-management">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <h2>日志管理 (简化版)</h2>
          <el-button type="primary" @click="refreshLogs">刷新</el-button>
        </div>
      </template>

      <!-- 统计信息 -->
      <div class="stats-section" v-if="stats">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="总日志数" :value="stats.total" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="今日日志" :value="stats.today" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="错误数量" :value="stats.errors" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="警告数量" :value="stats.warnings" />
          </el-col>
        </el-row>
      </div>

      <!-- 过滤器 -->
      <div class="filter-section">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-select v-model="filters.level" placeholder="选择级别" clearable>
              <el-option label="ERROR" value="ERROR" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="INFO" value="INFO" />
              <el-option label="DEBUG" value="DEBUG" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select v-model="filters.source" placeholder="选择来源" clearable>
              <el-option v-for="source in sources" :key="source" :label="source" :value="source" />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-input v-model="filters.keyword" placeholder="搜索关键词" clearable />
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="applyFilters">搜索</el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 日志表格 -->
      <el-table 
        :data="logs" 
        style="width: 100%" 
        v-loading="loading"
        :default-sort="{ prop: 'timestamp', order: 'descending' }"
      >
        <el-table-column prop="timestamp" label="时间" width="180" sortable>
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="level" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="source" label="来源" width="120" />
        
        <el-table-column prop="message" label="消息" min-width="300">
          <template #default="{ row }">
            <span class="message-text" :title="row.message">
              {{ row.message }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="user_name" label="用户" width="120" />
        
        <el-table-column prop="ip_address" label="IP地址" width="140" />
      </el-table>

      <!-- 分页 -->
      <div class="pagination-section">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[20, 50, 100]"
          :total="pagination.total"
          layout="sizes, prev, pager, next, jumper, total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 响应式数据
const loading = ref(false)
const logs = ref([])
const stats = ref(null)
const sources = ref([])

const filters = reactive({
  level: '',
  source: '',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  size: 50,
  total: 0
})

// 获取token
const getToken = () => {
  return localStorage.getItem('access_token') || ''
}

// API请求配置
const apiRequest = (url, options = {}) => {
  const token = getToken()
  return axios({
    url: `/api/v1/simple${url}`,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })
}

// 获取日志列表
const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      level: filters.level,
      source: filters.source,
      keyword: filters.keyword
    }
    
    const response = await apiRequest('/logs/list', { 
      method: 'GET',
      params 
    })
    
    if (response.data.status === 'success') {
      logs.value = response.data.data.logs
      pagination.total = response.data.data.total
    } else {
      throw new Error(response.data.error || '加载失败')
    }
  } catch (error) {
    console.error('加载日志失败:', error)
    ElMessage.error('加载日志失败: ' + (error.response?.data?.error || error.message))
  } finally {
    loading.value = false
  }
}

// 获取统计信息
const loadStats = async () => {
  try {
    const response = await apiRequest('/logs/stats', { method: 'GET' })
    if (response.data.status === 'success') {
      stats.value = response.data.data
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 获取日志来源列表
const loadSources = async () => {
  try {
    const response = await apiRequest('/logs/sources', { method: 'GET' })
    if (response.data.status === 'success') {
      sources.value = response.data.data
    }
  } catch (error) {
    console.error('加载日志来源失败:', error)
  }
}

// 应用过滤器
const applyFilters = () => {
  pagination.page = 1
  loadLogs()
}

// 刷新所有数据
const refreshLogs = async () => {
  await Promise.all([
    loadLogs(),
    loadStats(),
    loadSources()
  ])
}

// 分页处理
const handleSizeChange = (val) => {
  pagination.size = val
  pagination.page = 1
  loadLogs()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  loadLogs()
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 获取级别对应的标签类型
const getLevelType = (level) => {
  const types = {
    'ERROR': 'danger',
    'WARNING': 'warning',
    'INFO': 'info',
    'DEBUG': 'success'
  }
  return types[level] || 'info'
}

// 初始化
onMounted(() => {
  refreshLogs()
})
</script>

<style scoped>
.simple-log-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-section {
  margin-bottom: 20px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.pagination-section {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.message-text {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table .el-table__row) {
  cursor: pointer;
}

:deep(.el-table .el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>