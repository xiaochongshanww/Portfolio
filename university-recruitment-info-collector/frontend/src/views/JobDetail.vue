<template>
  <el-dialog v-model="visible" :title="job?.school || '岗位详情'" width="700px" top="5vh" destroy-on-close>
    <template v-if="job">
      <div class="space-y-5">
        <!-- Header -->
        <div>
          <h3 class="text-lg font-semibold text-slate-900">{{ job.position }}</h3>
          <p class="text-sm text-slate-500 mt-1">{{ job.department || '未标注学院' }} · {{ job.location || '未标注地点' }}</p>
        </div>

        <!-- Key fields grid -->
        <div class="grid grid-cols-2 gap-4">
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-400">学校</p>
            <p class="mt-1 text-sm font-semibold text-slate-800">{{ job.school }}</p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-400">学历要求</p>
            <p class="mt-1 text-sm font-semibold text-slate-800">{{ job.education_requirement || '未提取' }} <span v-if="!job.education_requirement" class="text-amber-500 text-xs">（建议查看原文）</span></p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-400">岗位类型</p>
            <p class="mt-1 text-sm font-semibold text-slate-800">{{ job.job_type || '未提取' }} <span v-if="!job.job_type" class="text-amber-500 text-xs">（建议查看原文）</span></p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-400">截止日期</p>
            <p class="mt-1 text-sm font-semibold" :class="isExpired(job.deadline) ? 'text-red-600' : 'text-slate-800'">{{ job.deadline || '长期/未说明' }}</p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-400">学科方向</p>
            <p class="mt-1 text-sm font-semibold text-slate-800">{{ job.discipline || '未提取' }} <span v-if="!job.discipline" class="text-amber-500 text-xs">（建议查看原文）</span></p>
          </div>
          <div class="rounded-xl bg-slate-50 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-400">数据质量</p>
            <p class="mt-1 text-sm font-semibold text-slate-800">{{ qualityLabel(job.quality_status) }}（{{ job.quality_score ?? '—' }}分）</p>
          </div>
        </div>

        <!-- Coordinates -->
        <div v-if="job.longitude" class="rounded-xl bg-slate-50 p-3">
          <p class="text-xs uppercase tracking-wide text-slate-400">GPS 坐标</p>
          <p class="mt-1 text-sm text-slate-600">{{ job.latitude?.toFixed(4) }}, {{ job.longitude?.toFixed(4) }}</p>
        </div>

        <!-- Description -->
        <div v-if="job.description">
          <p class="text-xs uppercase tracking-wide text-slate-400 mb-2">公告内容摘要</p>
          <p class="text-sm leading-6 text-slate-600 bg-slate-50 rounded-xl p-3 max-h-40 overflow-y-auto">{{ job.description }}</p>
        </div>

        <!-- Source info -->
        <div class="text-xs text-slate-400 space-y-1">
          <p>来源: {{ job.source_name }} | 采集时间: {{ formatTime(job.collected_at) }}</p>
          <p v-if="job.published_at">发布时间: {{ job.published_at }}</p>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex gap-2">
        <el-button @click="toggleFav" :type="isFav ? 'warning' : 'default'">
          {{ isFav ? '★ 已收藏' : '☆ 收藏' }}
        </el-button>
        <el-button type="primary" @click="openLink">查看原文</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const API = axios.create({ baseURL: '/api', timeout: 5000 })
const props = defineProps({ modelValue: Boolean, job: Object })
const emit = defineEmits(['update:modelValue', 'fav-changed'])

const visible = ref(false)
const isFav = ref(false)

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v && props.job) checkFav()
})

watch(visible, (v) => { emit('update:modelValue', v) })

async function checkFav() {
  try {
    const res = await API.get(`/favorites/${props.job.id}`)
    isFav.value = res.data?.favorited || false
  } catch {}
}

async function toggleFav() {
  try {
    if (isFav.value) {
      await API.delete(`/favorites/${props.job.id}`)
      isFav.value = false
      ElMessage.success('已取消收藏')
    } else {
      await API.post(`/favorites/${props.job.id}`)
      isFav.value = true
      ElMessage.success('已收藏')
    }
    emit('fav-changed')
  } catch { ElMessage.error('操作失败') }
}

function openLink() {
  const url = (props.job?.source_url || '').toString().trim()
  if (url.startsWith('http')) window.open(url, '_blank', 'noopener,noreferrer')
  else ElMessage.warning('无效链接')
}

function isExpired(deadline) { return deadline && new Date(deadline) < new Date() }
function qualityLabel(status) {
  if (status === 'normal') return '质量正常'
  if (status === 'needs_review') return '待人工复核'
  if (status === 'hidden') return '低可信数据'
  return '未知'
}
function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}
</script>
