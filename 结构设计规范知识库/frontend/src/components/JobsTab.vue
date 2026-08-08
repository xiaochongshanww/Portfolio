<template>
  <div class="grid h-full min-h-[720px] grid-cols-[360px_minmax(0,1fr)] gap-5">
    <section class="panel flex flex-col">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">构建任务</h2>
        <p class="muted mt-1">统一入口运行导入、重建、审计、AI 校对候选和评估。</p>
      </div>

      <div class="space-y-4 overflow-auto p-4">
        <div class="grid grid-cols-2 gap-2">
          <button class="btn" :disabled="busy" @click="startJob('/admin/jobs/dry-run', jobRequest)">Dry Run</button>
          <button class="btn btn-primary" :disabled="busy" @click="startJob('/admin/jobs/rebuild', jobRequest)">重建知识库</button>
          <button class="btn" :disabled="busy" @click="startJob('/admin/jobs/audit')">规则审计</button>
          <button class="btn" :disabled="busy" @click="startJob('/admin/jobs/evaluate', { top_k: 5 })">运行评估</button>
        </div>

        <div class="space-y-2">
          <label class="block text-xs font-medium text-slate-500">数据源</label>
          <input v-model="jobRequest.source" class="field" />
          <label class="block text-xs font-medium text-slate-500">解析器</label>
          <select v-model="jobRequest.parser_backend" class="field">
            <option value="mineru">mineru</option>
            <option value="pymupdf">pymupdf</option>
          </select>
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="jobRequest.apply_corrections" type="checkbox" class="h-4 w-4 rounded border-slate-300">
            重建时应用已审批修正
          </label>
        </div>

        <div class="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div class="text-sm font-semibold">生成 AI 校对候选</div>
          <input v-model="reviewDoc" class="field" placeholder="文档名，例如 GB 50009-2012">
          <input v-model="reviewPages" class="field" placeholder="页码，例如 40-45">
          <button class="btn btn-primary w-full" :disabled="busy || !reviewDoc.trim()" @click="startReview">生成候选</button>
        </div>

        <p v-if="message" class="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{{ message }}</p>
        <p v-if="error" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </div>
    </section>

    <section class="panel grid min-h-0 grid-cols-[minmax(0,1fr)_420px] overflow-hidden">
      <div class="min-w-0 overflow-auto">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white p-4">
          <h2 class="panel-title">任务队列</h2>
          <button class="btn" @click="$emit('refresh')">刷新</button>
        </div>
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th class="px-4 py-3">类型</th>
              <th class="px-4 py-3">状态</th>
              <th class="px-4 py-3">步骤</th>
              <th class="px-4 py-3">开始时间</th>
              <th class="px-4 py-3">错误</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="job in jobs"
              :key="job.job_id"
              class="cursor-pointer border-t border-slate-100 hover:bg-blue-50/60"
              :class="selectedJob?.job_id === job.job_id ? 'bg-blue-50' : ''"
              @click="selectJob(job)"
            >
              <td class="px-4 py-3 font-medium">{{ job.type }}</td>
              <td class="px-4 py-3"><span :class="statusClass(job.status)">{{ job.status }}</span></td>
              <td class="px-4 py-3 text-slate-600">{{ job.step }}</td>
              <td class="px-4 py-3 text-slate-500">{{ job.started_at || job.created_at }}</td>
              <td class="max-w-[360px] truncate px-4 py-3 text-red-600">{{ job.error }}</td>
            </tr>
            <tr v-if="!jobs.length">
              <td colspan="5" class="px-4 py-10 text-center text-slate-500">暂无任务。</td>
            </tr>
          </tbody>
        </table>
      </div>

      <aside class="flex min-h-0 flex-col border-l border-slate-200 bg-slate-950 text-slate-100">
        <div class="border-b border-slate-800 p-4">
          <div class="text-sm font-semibold">{{ selectedJob?.job_id || '任务日志' }}</div>
          <div class="mt-1 text-xs text-slate-400">{{ selectedJob?.type || '选择左侧任务查看日志' }}</div>
        </div>
        <pre class="flex-1 overflow-auto whitespace-pre-wrap p-4 text-xs leading-5 text-slate-200">{{ logsText }}</pre>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { apiGet, apiPost } from '../api'

const props = defineProps<{ jobs: any[] }>()
const emit = defineEmits<{ refresh: [] }>()

const busy = ref(false)
const error = ref('')
const message = ref('')
const selectedJob = ref<any>(null)
const logs = ref<any[]>([])
const reviewDoc = ref('')
const reviewPages = ref('')
const jobRequest = ref({ source: 'data/raw', parser_backend: 'mineru', apply_corrections: true })

const logsText = computed(() => logs.value.length ? logs.value.map(formatLogEntry).join('\n') : selectedJob.value?.error || '暂无任务日志')

async function startJob(url: string, body?: Record<string, any>) {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const job = await apiPost(url, body)
    selectedJob.value = job
    message.value = `已提交任务 ${job.job_id}`
    emit('refresh')
    await loadLogs(job)
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function startReview() {
  await startJob('/admin/jobs/review', { doc: reviewDoc.value.trim(), pages: reviewPages.value.trim() })
}

async function selectJob(job: any) {
  selectedJob.value = job
  await loadLogs(job)
}

async function loadLogs(job: any) {
  if (!job?.job_id) return
  const result = await apiGet(`/admin/jobs/${job.job_id}/logs?limit=300`)
  logs.value = result.logs || []
}

function formatLogEntry(entry: any) {
  if (typeof entry === 'string') return entry
  if (!entry || typeof entry !== 'object') return String(entry)
  const time = entry.ts ? entry.ts.replace('T', ' ').replace(/\+\d\d:\d\d$/, '') : ''
  const level = String(entry.level || 'info').toUpperCase()
  const step = entry.step ? ` [${entry.step}]` : ''
  const request = entry.request_id ? ` [request:${entry.request_id}]` : ''
  const message = entry.message || entry.error || JSON.stringify(entry)
  const progress = entry.progress ? `\n${JSON.stringify(entry.progress, null, 2)}` : ''
  return `${time} ${level}${step}${request} ${message}${progress}`.trim()
}

function statusClass(status: string) {
  const base = 'rounded px-2 py-1 text-xs font-semibold'
  if (status === 'succeeded') return `${base} bg-emerald-100 text-emerald-700`
  if (status === 'failed') return `${base} bg-red-100 text-red-700`
  if (status === 'running') return `${base} bg-blue-100 text-blue-700`
  return `${base} bg-slate-100 text-slate-600`
}

watch(() => props.jobs, () => {
  if (!selectedJob.value && props.jobs.length) {
    selectedJob.value = props.jobs[0]
    return
  }
  const updated = props.jobs.find(job => job.job_id === selectedJob.value?.job_id)
  if (updated) selectedJob.value = updated
})
</script>
