<template>
  <div class="space-y-6">
    <section class="glass-panel-strong p-6 sm:p-8">
      <div class="grid gap-8 xl:grid-cols-[1.2fr_0.8fr] xl:items-end">
        <div>
          <p class="section-kicker">Favorites</p>
          <h2 class="hero-title mt-3 text-slate-950">我的收藏</h2>
          <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
            收藏的岗位会保存在服务器上，方便后续查看和对比。
          </p>
        </div>
        <div class="text-right">
          <el-button @click="fetchFavorites" :loading="loading">刷新</el-button>
        </div>
      </div>
    </section>

    <section class="glass-panel-strong overflow-hidden p-3 sm:p-4">
      <el-table :data="favorites" border stripe style="width: 100%" v-loading="loading" empty-text="还没有收藏任何岗位">
        <el-table-column prop="school" label="学校" min-width="160" show-overflow-tooltip />
        <el-table-column prop="position" label="岗位" min-width="240" show-overflow-tooltip />
        <el-table-column prop="location" label="地点" width="120" />
        <el-table-column label="收藏时间" width="170">
          <template #default="{ row }">{{ formatTime(row.saved_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link @click="removeFavorite(row.job_id)">取消收藏</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const API = axios.create({ baseURL: '/api', timeout: 10000 })
const favorites = ref([])
const loading = ref(false)

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchFavorites() {
  loading.value = true
  try {
    const res = await API.get('/favorites')
    favorites.value = res.data || []
  } catch {
    ElMessage.error('加载收藏列表失败')
  } finally {
    loading.value = false
  }
}

async function removeFavorite(jobId) {
  try {
    await API.delete(`/favorites/${jobId}`)
    ElMessage.success('已取消收藏')
    await fetchFavorites()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => fetchFavorites())
</script>
