<template>
  <div class="grid min-h-[calc(100dvh-7rem)] gap-5 xl:h-full xl:min-h-[720px] xl:grid-cols-[320px_minmax(0,1fr)]">
    <section class="panel flex flex-col">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">构建任务</h2>
        <p class="muted mt-1">统一入口运行导入、重建、审计、AI 校对候选和评估。</p>
      </div>

      <div class="space-y-4 overflow-auto p-4">
        <div class="grid grid-cols-2 gap-2">
          <button class="btn" :disabled="busy" @click="startDryRun">Dry Run</button>
          <button class="btn btn-primary" :disabled="busy" @click="startRebuild">重建知识库</button>
          <button class="btn" :disabled="busy" @click="startAudit">规则审计</button>
          <button class="btn" :disabled="busy" @click="startEvaluation">运行评估</button>
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

    <section class="panel grid min-h-[760px] min-w-0 grid-rows-[minmax(420px,1fr)_320px] overflow-hidden 2xl:min-h-[680px] 2xl:grid-cols-[minmax(0,1fr)_420px] 2xl:grid-rows-1">
      <div class="min-w-0 overflow-auto">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white p-4">
          <h2 class="panel-title">任务队列</h2>
          <button class="btn" @click="$emit('refresh')">刷新</button>
        </div>
        <table class="w-full min-w-[760px] table-fixed text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th class="w-36 px-4 py-3">类型</th>
              <th class="w-28 px-4 py-3">状态</th>
              <th class="w-36 px-4 py-3">步骤</th>
              <th class="w-44 px-4 py-3">最近进度</th>
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
              <td class="break-all px-4 py-3 font-medium">{{ job.type }}</td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1">
                  <span :class="statusClass(job.status)">{{ statusLabel(job) }}</span>
                  <span v-if="job.diagnostics?.stalled" class="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">疑似卡滞</span>
                </div>
              </td>
              <td class="truncate px-4 py-3 text-slate-600" :title="job.step">{{ job.step }}</td>
              <td class="px-4 py-3 text-slate-500">
                <div>{{ formatDate(job.progress_at || job.started_at || job.created_at) }}</div>
                <div class="mt-1 text-xs">{{ formatAge(job.diagnostics?.progress_age_seconds) }}</div>
              </td>
              <td class="max-w-[360px] truncate px-4 py-3 text-red-600" :title="job.error || job.error_code">{{ job.error || errorCodeLabel(job.error_code) }}</td>
            </tr>
            <tr v-if="!jobs.length">
              <td colspan="5" class="px-4 py-10 text-center text-slate-500">暂无任务。</td>
            </tr>
          </tbody>
        </table>
      </div>

      <aside class="flex min-h-[320px] min-w-0 flex-col border-t border-slate-200 bg-slate-950 text-slate-100 2xl:min-h-0 2xl:border-t-0 2xl:border-l">
        <div class="border-b border-slate-800 p-4">
          <div class="flex items-center justify-between gap-2">
            <div class="min-w-0 truncate text-sm font-semibold">{{ selectedJob?.job_id || '任务日志' }}</div>
            <span v-if="selectedJob" :class="statusClass(selectedJob.status)">{{ statusLabel(selectedJob) }}</span>
          </div>
          <div class="mt-1 text-xs text-slate-400">{{ selectedJob ? `${selectedJob.type} · ${selectedJob.step}` : '选择左侧任务查看日志' }}</div>
          <div v-if="selectedJob?.diagnostics?.stalled" class="mt-3 rounded bg-amber-400/15 px-3 py-2 text-xs text-amber-200">
            {{ diagnosticLabel(selectedJob) }}。系统不会强制终止线程，请结合日志和进程状态处理。
          </div>
        </div>
        <pre class="flex-1 overflow-auto whitespace-pre-wrap p-4 text-xs leading-5 text-slate-200">{{ logsText }}</pre>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  getAdminJobLogs,
  startAdminAudit,
  startAdminDryRun,
  startAdminEvaluation,
  startAdminRebuild,
  startAdminReview,
} from '../admin-api'
import { errorMessage } from '../api'
import type { JobRequest, JobResponse } from '../contracts'

const props = defineProps<{ jobs: JobResponse[] }>()
const emit = defineEmits<{ refresh: [] }>()

const busy = ref(false)
const error = ref('')
const message = ref('')
const selectedJob = ref<JobResponse | null>(null)
const logs = ref<Record<string, unknown>[]>([])
const logsLoading = ref(false)
let logsRequestSerial = 0
const reviewDoc = ref('')
const reviewPages = ref('')
const jobRequest = ref<JobRequest>({
  source: 'data/raw',
  parser_backend: 'mineru',
  apply_corrections: true,
})

const logsText = computed(() => logs.value.length ? logs.value.map(formatLogEntry).join('\n') : selectedJob.value?.error || '暂无任务日志')

async function startJob(task: () => Promise<JobResponse>) {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const job = await task()
    selectedJob.value = job
    message.value = `已提交任务 ${job.job_id}`
    emit('refresh')
    await loadLogs(job)
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function startDryRun() {
  await startJob(() => startAdminDryRun({ body: jobRequest.value }))
}

async function startRebuild() {
  await startJob(() => startAdminRebuild({ body: jobRequest.value }))
}

async function startAudit() {
  await startJob(() => startAdminAudit())
}

async function startEvaluation() {
  await startJob(() => startAdminEvaluation({
    body: { top_k: 5, evaluation_set: 'regular' },
  }))
}

async function startReview() {
  await startJob(() => startAdminReview({
    body: { doc: reviewDoc.value.trim(), pages: reviewPages.value.trim() },
  }))
}

async function selectJob(job: JobResponse) {
  selectedJob.value = job
  await loadLogs(job)
}

async function loadLogs(job: JobResponse) {
  const jobId = job?.job_id
  if (!jobId) return
  const requestSerial = ++logsRequestSerial
  logsLoading.value = true
  try {
    const result = await getAdminJobLogs({
      path: { job_id: jobId },
      query: { limit: 300 },
    })
    if (requestSerial === logsRequestSerial && selectedJob.value?.job_id === jobId) {
      logs.value = result.logs || []
    }
  } catch (err: unknown) {
    if (requestSerial === logsRequestSerial) {
      error.value = errorMessage(err)
    }
  } finally {
    if (requestSerial === logsRequestSerial) logsLoading.value = false
  }
}

function formatLogEntry(entry: Record<string, unknown>) {
  if (typeof entry === 'string') return entry
  if (!entry || typeof entry !== 'object') return String(entry)
  const time = typeof entry.ts === 'string'
    ? entry.ts.replace('T', ' ').replace(/\+\d\d:\d\d$/, '')
    : ''
  const level = String(entry.level || 'info').toUpperCase()
  const step = entry.step ? ` [${entry.step}]` : ''
  const request = entry.request_id ? ` [request:${entry.request_id}]` : ''
  const message = entry.message || entry.error || JSON.stringify(entry)
  const progress = entry.progress ? `\n${JSON.stringify(entry.progress, null, 2)}` : ''
  const recovery = entry.recovery ? `\n${JSON.stringify(entry.recovery, null, 2)}` : ''
  return `${time} ${level}${step}${request} ${message}${progress}${recovery}`.trim()
}

function statusLabel(job: JobResponse) {
  if (job?.error_code === 'PROCESS_RESTARTED') return '已中断'
  return ({
    queued: '排队中',
    running: '运行中',
    succeeded: '已成功',
    failed: '已失败',
  } as Record<string, string>)[job?.status] || job?.status || '-'
}

function errorCodeLabel(code?: string) {
  if (!code) return ''
  return ({
    PROCESS_RESTARTED: 'API 进程重启，任务已中断',
    JOB_RECORD_INVALID: '任务记录损坏',
    WORKFLOW_FAILED: '任务执行失败',
  } as Record<string, string>)[code] || code
}

function formatDate(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function formatAge(value: unknown) {
  const seconds = Number(value)
  if (!Number.isFinite(seconds)) return '暂无进度时间'
  if (seconds < 60) return `${Math.floor(seconds)} 秒前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

function diagnosticLabel(job: JobResponse) {
  const diagnostics = job?.diagnostics || {}
  if (diagnostics.reason === 'no_progress_and_heartbeat_stale') return '长时间无进展且执行器心跳已过期'
  if (diagnostics.reason === 'no_progress') return '执行器仍有心跳，但任务长时间没有推进步骤'
  if (diagnostics.reason === 'heartbeat_stale') return '执行器心跳已过期'
  return '任务状态需要核对'
}

function statusClass(status: string) {
  const base = 'whitespace-nowrap rounded px-2 py-1 text-xs font-semibold'
  if (status === 'succeeded') return `${base} bg-emerald-100 text-emerald-700`
  if (status === 'failed') return `${base} bg-red-100 text-red-700`
  if (status === 'running') return `${base} bg-blue-100 text-blue-700`
  return `${base} bg-slate-100 text-slate-600`
}

watch(() => props.jobs, async () => {
  if (!selectedJob.value && props.jobs.length) {
    selectedJob.value = props.jobs[0]
    await loadLogs(selectedJob.value)
    return
  }
  const updated = props.jobs.find(job => job.job_id === selectedJob.value?.job_id)
  if (updated) selectedJob.value = updated
}, { immediate: true })

let refreshTimer: number | undefined
onMounted(() => {
  refreshTimer = window.setInterval(() => {
    emit('refresh')
    if (selectedJob.value?.status === 'running' || selectedJob.value?.status === 'queued') {
      loadLogs(selectedJob.value)
    }
  }, 5000)
})
onBeforeUnmount(() => {
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer)
})
</script>
