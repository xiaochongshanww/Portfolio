<template>
  <div>
    <!-- Page Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-semibold text-gray-800">招聘岗位列表</h2>
      <p class="text-sm text-gray-400 mt-1">共 {{ jobs.length }} 条岗位，实时同步自各高校招聘网站</p>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <el-input
        v-model="search"
        placeholder="搜索学校或岗位..."
        clearable
        class="!w-72"
        @input="handleSearch"
      />
      <el-checkbox v-model="showExpired" @change="fetchJobs">显示已过期</el-checkbox>
      <el-button type="primary" @click="fetchJobs" :loading="loading">
        <span class="flex items-center gap-1">🔄 刷新</span>
      </el-button>
      <span class="text-xs text-gray-400 ml-auto">
        更新于 {{ lastUpdated || '—' }}
      </span>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
      <el-table
        :data="filteredJobs"
        border
        stripe
        style="width: 100%"
        v-loading="loading"
        empty-text="暂无岗位数据"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: 600 }"
      >
        <el-table-column prop="school" label="学校" min-width="160" show-overflow-tooltip />
        <el-table-column prop="position" label="岗位" min-width="220" show-overflow-tooltip />
        <el-table-column prop="department" label="学院/部门" min-width="140" show-overflow-tooltip />
        <el-table-column prop="location" label="地点" width="90" />
        <el-table-column prop="education_requirement" label="学历要求" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.education_requirement" size="small" type="info" effect="plain">
              {{ row.education_requirement }}
            </el-tag>
            <span v-else class="text-gray-300">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="job_type" label="岗位类型" width="120" show-overflow-tooltip />
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { listJobs } from '../api/index.js'

const jobs = ref([])
const search = ref('')
const showExpired = ref(false)
const loading = ref(false)
const lastUpdated = ref('')

const filteredJobs = computed(() => {
  if (!search.value) return jobs.value
  const q = search.value.toLowerCase()
  return jobs.value.filter(
    (j) => j.school?.toLowerCase().includes(q) || j.position?.toLowerCase().includes(q)
  )
})

function isExpired(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

function openLink(url) {
  window.open(url, '_blank')
}

async function fetchJobs() {
  loading.value = true
  try {
    const res = await listJobs(showExpired.value)
    jobs.value = res.data
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN')
  } catch (e) {
    console.error('Failed to fetch jobs:', e)
    jobs.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  // computed handles filtering
}

onMounted(fetchJobs)
</script>
