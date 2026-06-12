<template>
  <div>
    <h3>招聘岗位列表</h3>
    <div style="margin-bottom: 16px; display: flex; gap: 12px; align-items: center;">
      <el-input
        v-model="search"
        placeholder="搜索学校或岗位..."
        clearable
        style="width: 300px;"
        @input="handleSearch"
      />
      <el-checkbox v-model="showExpired" @change="fetchJobs">显示已过期</el-checkbox>
      <el-button type="primary" @click="fetchJobs" :loading="loading">刷新</el-button>
    </div>

    <el-table :data="filteredJobs" border stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="school" label="学校" width="180" />
      <el-table-column prop="position" label="岗位" width="240" />
      <el-table-column prop="department" label="学院/部门" width="160" />
      <el-table-column prop="location" label="地点" width="100" />
      <el-table-column prop="education_requirement" label="学历要求" width="110" />
      <el-table-column prop="job_type" label="岗位类型" width="120" />
      <el-table-column prop="deadline" label="截止日期" width="120">
        <template #default="{ row }">
          <el-tag v-if="isExpired(row.deadline)" type="danger" size="small">已过期</el-tag>
          <span v-else>{{ row.deadline || '未说明' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openLink(row.source_url)">原文</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && filteredJobs.length === 0" description="暂无岗位数据" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { listJobs } from '../api/index.js'

const jobs = ref([])
const search = ref('')
const showExpired = ref(false)
const loading = ref(false)

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
