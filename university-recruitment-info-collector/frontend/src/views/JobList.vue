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

    <section class="glass-panel-strong p-4 sm:p-5" v-loading="loading">
      <div v-if="filteredJobs.length === 0" class="py-12 text-center">
        <p class="text-lg font-semibold text-slate-400">暂无岗位数据</p>
        <p class="mt-2 text-sm text-slate-300">试试清除筛选条件，或等待数据采集完成后刷新</p>
      </div>

      <div v-else class="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="job in filteredJobs"
          :key="job.id"
          class="job-card cursor-pointer rounded-xl border border-slate-200 bg-white p-4 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
          @click="openDetail(job)"
        >
          <div class="flex items-start justify-between gap-2">
            <span class="truncate rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{{ job.school }}</span>
            <el-button text :type="isFav(job.id) ? 'warning' : 'default'" size="small" @click.stop="toggleFav(job)" :title="isFav(job.id) ? '取消收藏' : '收藏'">
              {{ isFav(job.id) ? '★' : '☆' }}
            </el-button>
          </div>

          <h3 class="mt-3 font-semibold text-slate-900 line-clamp-2">{{ job.position }}</h3>
          <p v-if="job.department" class="mt-0.5 text-xs text-slate-400 truncate">{{ job.department }}</p>

          <div class="mt-3 flex flex-wrap gap-1.5">
            <el-tag v-if="job.education_requirement" size="small" type="info" effect="plain">{{ job.education_requirement }}</el-tag>
            <el-tag v-if="job.job_type" size="small" type="success" effect="plain">{{ job.job_type }}</el-tag>
            <el-tag v-if="job.quality_status" :type="qualityTagType(job.quality_status)" size="small" effect="plain">{{ qualityLabel(job.quality_status) }}</el-tag>
          </div>

          <div class="mt-4 flex items-center justify-between text-xs text-slate-400">
            <span>{{ job.location || '未标注地点' }}</span>
            <span :class="{ 'text-red-500': isExpired(job.deadline) }">{{ job.deadline || '长期' }}</span>
          </div>

          <div class="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
            <el-button text size="small" type="primary" @click.stop="openLink(job.source_url)">查看原文</el-button>
            <el-tag v-if="job.quality_score != null" size="small" effect="plain" type="default">质量 {{ job.quality_score }}</el-tag>
          </div>
        </article>
      </div>
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

    <JobDetail v-model="detailVisible" :job="detailJob" @fav-changed="fetchFavs" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listJobs } from '../api/index.js'
import JobDetail from './JobDetail.vue'
import axios from 'axios'

const FAV_API = axios.create({ baseURL: '/api', timeout: 5000 })

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

const detailVisible = ref(false)
const detailJob = ref(null)

function openDetail(row) {
  detailJob.value = row
  detailVisible.value = true
}

const favoriteIds = ref(new Set())

async function fetchFavs() {
  try {
    const res = await FAV_API.get('/favorites')
    favoriteIds.value = new Set((res.data || []).map(f => f.job_id))
  } catch {}
}

function isFav(jobId) { return favoriteIds.value.has(jobId) }

async function toggleFav(job) {
  try {
    if (isFav(job.id)) {
      await FAV_API.delete(`/favorites/${job.id}`)
      favoriteIds.value.delete(job.id)
      ElMessage.success('已取消收藏')
    } else {
      await FAV_API.post(`/favorites/${job.id}`)
      favoriteIds.value.add(job.id)
      ElMessage.success('已收藏')
    }
  } catch { ElMessage.error('操作失败') }
}

onMounted(() => { fetchJobs(0); fetchFavs() })
</script>
