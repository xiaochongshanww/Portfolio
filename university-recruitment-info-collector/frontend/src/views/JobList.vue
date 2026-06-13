<template>
  <div>
    <div class="mb-6">
      <h2 class="text-2xl font-semibold text-gray-800">招聘岗位列表</h2>
      <p class="text-sm text-gray-400 mt-1">共 {{ pagination.total }} 条岗位，实时同步自各高校招聘网站</p>
    </div>

    <div class="flex flex-wrap items-center gap-3 mb-4">
      <el-input v-model="search" placeholder="搜索学校或岗位..." clearable class="!w-72" />
      <el-checkbox v-model="showExpired" @change="fetchJobs(0)">显示已过期</el-checkbox>
      <el-checkbox v-model="showLowQuality" @change="fetchJobs(0)">显示低质量数据</el-checkbox>
      <el-button type="primary" @click="fetchJobs(0)" :loading="loading">
        🔄 刷新
      </el-button>
      <span class="text-xs text-gray-400 ml-auto">更新于 {{ lastUpdated || '—' }}</span>
    </div>

    <div class="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
      <el-table :data="filteredJobs" border stripe style="width: 100%" v-loading="loading"
        empty-text="暂无岗位数据"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: 600 }">
        <el-table-column prop="school" label="学校" min-width="160" show-overflow-tooltip />
        <el-table-column prop="position" label="岗位" min-width="220" show-overflow-tooltip />
        <el-table-column prop="department" label="学院/部门" min-width="140" show-overflow-tooltip />
        <el-table-column prop="location" label="地点" width="90" />
        <el-table-column prop="education_requirement" label="学历要求" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.education_requirement" size="small" type="info" effect="plain">{{ row.education_requirement }}</el-tag>
            <span v-else class="text-gray-300">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="job_type" label="岗位类型" width="120" show-overflow-tooltip />
        <el-table-column label="质量" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.quality_status === 'normal'" size="small" type="success">正常</el-tag>
            <el-tag v-else-if="row.quality_status === 'needs_review'" size="small" type="warning">待审查</el-tag>
            <el-tag v-else-if="row.quality_status === 'hidden'" size="small" type="danger">隐藏</el-tag>
            <span v-else class="text-gray-300">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="120">
          <template #default="{ row }">
            <el-tag v-if="isExpired(row.deadline)" type="danger" size="small">已过期</el-tag>
            <span v-else class="text-gray-600">{{ row.deadline || '未说明' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openLink(row.source_url)">查看原文</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pagination -->
    <div class="flex justify-center mt-4" v-if="pagination.total > pagination.limit">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="pagination.total"
        :page-size="pagination.limit"
        :current-page="currentPage"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listJobs } from '../api/index.js'

const DEFAULT_PAGINATION = { total: 0, limit: 100, offset: 0, has_more: false }

const jobs = ref([])
const search = ref('')
const showExpired = ref(false)
const showLowQuality = ref(false)
const loading = ref(false)
const lastUpdated = ref('')
const pagination = ref({ ...DEFAULT_PAGINATION })
const currentPage = ref(1)

function parseJobListResponse(data) {
  return {
    jobs: Array.isArray(data?.jobs) ? data.jobs : [],
    pagination: data?.pagination || { ...DEFAULT_PAGINATION },
  }
}

const filteredJobs = computed(() => {
  const arr = Array.isArray(jobs.value) ? jobs.value : []
  if (!search.value) return arr
  const q = search.value.toLowerCase()
  return arr.filter(j => j.school?.toLowerCase().includes(q) || j.position?.toLowerCase().includes(q))
})

function isExpired(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

function openLink(url) {
  const value = String(url || '').trim()
  if (!value.startsWith('http://') && !value.startsWith('https://')) {
    ElMessage.warning('不支持打开非 HTTP/HTTPS 链接')
    return
  }
  window.open(value, '_blank', 'noopener,noreferrer')
}

async function fetchJobs(page = 0) {
  loading.value = true
  const offset = page * pagination.value.limit
  try {
    const res = await listJobs(showExpired.value, pagination.value.limit, offset, showLowQuality.value)
    const parsed = parseJobListResponse(res.data)
    jobs.value = parsed.jobs
    pagination.value = parsed.pagination
    currentPage.value = Math.floor(offset / Math.max(1, pagination.value.limit)) + 1
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN')
  } catch (e) {
    ElMessage.error('加载岗位列表失败，请稍后重试')
    jobs.value = []
    pagination.value = { ...DEFAULT_PAGINATION }
  } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  fetchJobs(page - 1)
}

onMounted(() => fetchJobs(0))
</script>
