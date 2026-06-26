<template>
  <div class="space-y-6">
    <section class="glass-panel-strong p-6 sm:p-8">
      <div class="grid gap-8 lg:grid-cols-[1.5fr_1fr] lg:items-end">
        <div>
          <p class="section-kicker">Live Recruiting Board</p>
          <h2 class="hero-title mt-3 text-slate-950">广州高校岗位总览</h2>
          <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
            将各高校招聘公告清洗为统一岗位数据，同时附带质量状态，便于快速筛选哪些岗位可以直接投递，哪些需要回原文复核。
          </p>
        </div>

        <div class="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">总岗位</p>
            <p class="mt-3 text-3xl font-semibold text-slate-950">{{ pagination.total }}</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">当前页正常</p>
            <p class="mt-3 text-3xl font-semibold text-emerald-700">{{ normalCount }}</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">需人工复核</p>
            <p class="mt-3 text-3xl font-semibold text-amber-600">{{ reviewCount }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="glass-panel p-4 sm:p-5">
      <div class="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto] xl:items-center">
        <el-input v-model="search" placeholder="搜索学校、岗位、学院或地点" clearable class="xl:min-w-[20rem]" />
        <el-select v-model="filterSchool" clearable placeholder="所有学校" class="xl:w-44" @change="fetchJobs(0)">
          <el-option v-for="s in schoolOptions" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="filterLocation" clearable placeholder="所有地点" class="xl:w-44" @change="fetchJobs(0)">
          <el-option v-for="l in locationOptions" :key="l" :label="l" :value="l" />
        </el-select>
        <el-checkbox v-model="showExpired" @change="fetchJobs(0)">包含已过期</el-checkbox>
        <el-checkbox v-model="showLowQuality" @change="fetchJobs(0)">包含低质量数据</el-checkbox>
        <div class="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-500">
          当前展示 {{ filteredJobs.length }} / {{ allJobsCount }}
        </div>
        <div class="flex items-center gap-3 xl:justify-end">
          <span class="text-xs text-slate-400">更新于 {{ lastUpdated || '—' }}</span>
          <el-button type="primary" @click="fetchJobs(0)" :loading="loading">刷新数据</el-button>
        </div>
      </div>
    </section>

    <section class="glass-panel-strong overflow-hidden p-3 sm:p-4">
      <el-table
        :data="filteredJobs"
        border
        stripe
        style="width: 100%"
        v-loading="loading"
        empty-text="暂无岗位数据"
        :header-cell-style="{ background: 'rgba(248,250,252,0.84)', color: '#334155', fontWeight: 700 }"
      >
        <el-table-column prop="school" label="学校" min-width="170" show-overflow-tooltip />
        <el-table-column label="岗位信息" min-width="260">
          <template #default="{ row }">
            <div class="space-y-1">
              <div class="font-semibold text-slate-900">{{ row.position }}</div>
              <div class="text-xs text-slate-500">{{ row.department || '未标注学院/部门' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="条件" min-width="170">
          <template #default="{ row }">
            <div class="flex flex-wrap gap-1.5">
              <el-tag v-if="row.education_requirement" size="small" type="info" effect="plain">{{ row.education_requirement }}</el-tag>
              <el-tag v-if="row.job_type" size="small" type="success" effect="plain">{{ row.job_type }}</el-tag>
              <span v-if="!row.education_requirement && !row.job_type" class="text-slate-300">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="地点" width="110" />
        <el-table-column label="质量" width="150">
          <template #default="{ row }">
            <div class="space-y-1">
              <el-tag :type="qualityTagType(row.quality_status)" size="small" effect="plain">
                {{ qualityLabel(row.quality_status) }}
              </el-tag>
              <div class="text-xs text-slate-400">分数 {{ row.quality_score ?? '—' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="130">
          <template #default="{ row }">
            <div v-if="isExpired(row.deadline)" class="space-y-1">
              <el-tag type="danger" size="small">已过期</el-tag>
              <div class="text-xs text-slate-400">{{ row.deadline || '未说明' }}</div>
            </div>
            <span v-else class="text-slate-600">{{ row.deadline || '长期/未说明' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openLink(row.source_url)">查看原文</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <div class="flex justify-center" v-if="pagination.total > pagination.limit">
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
const allJobs = ref([])
const search = ref('')
const showExpired = ref(false)
const showLowQuality = ref(false)
const loading = ref(false)
const lastUpdated = ref('')
const pagination = ref({ ...DEFAULT_PAGINATION })
const currentPage = ref(1)
const filterSchool = ref('')
const filterLocation = ref('')
const schoolOptions = ref([])
const locationOptions = ref([])

function parseJobListResponse(data) {
  return {
    jobs: Array.isArray(data?.jobs) ? data.jobs : [],
    pagination: data?.pagination || { ...DEFAULT_PAGINATION },
  }
}

const allJobsCount = computed(() => allJobs.value.length)

const filteredJobs = computed(() => {
  const arr = Array.isArray(jobs.value) ? jobs.value : []
  if (!search.value) return arr
  const q = search.value.toLowerCase()
  return arr.filter(j =>
    j.school?.toLowerCase().includes(q)
    || j.position?.toLowerCase().includes(q)
    || j.department?.toLowerCase().includes(q)
    || j.location?.toLowerCase().includes(q)
  )
})

const normalCount = computed(() => jobs.value.filter(j => j.quality_status === 'normal').length)
const reviewCount = computed(() => jobs.value.filter(j => j.quality_status === 'needs_review').length)

function isExpired(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

function qualityTagType(status) {
  if (status === 'normal') return 'success'
  if (status === 'needs_review') return 'warning'
  if (status === 'hidden') return 'danger'
  return 'info'
}

function qualityLabel(status) {
  if (status === 'normal') return '质量正常'
  if (status === 'needs_review') return '待复核'
  if (status === 'hidden') return '已隐藏'
  return '未知'
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
    const filters = {}
    if (filterSchool.value) filters.school = filterSchool.value
    if (filterLocation.value) filters.location = filterLocation.value
    const res = await listJobs(showExpired.value, pagination.value.limit, offset, showLowQuality.value, filters)
    const parsed = parseJobListResponse(res.data)
    jobs.value = parsed.jobs
    pagination.value = parsed.pagination
    currentPage.value = Math.floor(offset / Math.max(1, pagination.value.limit)) + 1
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN')

    // Build filter options from full dataset
    if (page === 0 && !filterSchool.value && !filterLocation.value) {
      const fullRes = await listJobs(showExpired.value, 1000, 0, showLowQuality.value)
      const fullParsed = parseJobListResponse(fullRes.data)
      allJobs.value = fullParsed.jobs
      schoolOptions.value = [...new Set(fullParsed.jobs.map(j => j.school).filter(Boolean))].sort()
      locationOptions.value = [...new Set(fullParsed.jobs.map(j => j.location).filter(Boolean))].sort()
    }
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
