<template>
  <div class="grid h-[calc(100dvh-134px)] min-h-[680px] gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
    <section ref="jobControls" class="panel flex flex-col">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">构建任务</h2>
        <p class="muted mt-1">统一入口运行导入、重建、审计、AI 校对候选和评估。</p>
      </div>

      <div class="space-y-4 overflow-auto p-4">
        <div class="grid grid-cols-2 gap-2">
          <button class="btn" :disabled="busy" @click="analyzeChanges">分析变更</button>
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
          <label class="block text-xs font-medium text-slate-500">重建策略</label>
          <select v-model="jobRequest.mode" class="field">
            <option value="incremental">增量候选重建</option>
            <option value="full">强制全量重建</option>
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
          <button class="btn w-full" :disabled="busy || !reviewDoc.trim()" @click="startReview">生成候选</button>
        </div>

        <p v-if="message" class="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{{ message }}</p>
        <p v-if="error" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </div>
    </section>

    <section class="panel grid h-full min-h-0 min-w-0 grid-rows-[minmax(360px,1fr)_320px] overflow-hidden min-[1850px]:grid-cols-[minmax(0,1fr)_420px] min-[1850px]:grid-rows-1">
      <div class="flex min-h-0 min-w-0 flex-col overflow-hidden">
        <div class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white p-4">
          <div class="flex items-baseline gap-2">
            <h2 class="panel-title">任务队列</h2>
            <span class="muted">{{ filteredJobs.length }} / {{ jobs.length }} 条</span>
          </div>
          <div class="flex flex-wrap items-center justify-end gap-2">
            <label for="job-filter" class="sr-only">任务状态筛选</label>
            <select id="job-filter" v-model="jobFilter" class="field h-9 w-32">
              <option value="all">全部任务</option>
              <option value="running">运行中</option>
              <option value="queued">排队中</option>
              <option value="failed">已失败</option>
              <option value="succeeded">已成功</option>
            </select>
            <label for="job-page-size" class="sr-only">每页任务数</label>
            <select id="job-page-size" v-model.number="jobPageSize" class="field h-9 w-24">
              <option :value="10">每页 10 条</option>
              <option :value="20">每页 20 条</option>
              <option :value="50">每页 50 条</option>
            </select>
            <button class="btn" @click="$emit('refresh')">刷新任务</button>
          </div>
        </div>
        <div ref="queueViewport" data-testid="job-queue-scroll" class="min-h-0 min-w-0 flex-1 overflow-auto">
          <table class="w-full min-w-[600px] table-fixed text-left text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="w-32 px-4 py-3">类型</th>
                <th class="w-24 px-4 py-3">状态</th>
                <th class="w-28 px-4 py-3">步骤</th>
                <th class="w-40 px-4 py-3">最近更新</th>
                <th class="px-4 py-3">错误</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="job in paginatedJobs"
                :key="job.job_id"
                class="cursor-pointer border-t border-slate-100 outline-none hover:bg-blue-50/60 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500"
                :class="selectedJob?.job_id === job.job_id ? 'bg-blue-50' : ''"
                :aria-selected="selectedJob?.job_id === job.job_id"
                :tabindex="0"
                @click="selectJob(job)"
                @keydown.enter.prevent="selectJob(job)"
                @keydown.space.prevent="selectJob(job)"
              >
                <td class="max-w-0 truncate px-4 py-3 font-medium" :title="job.type">{{ formatJobType(job.type) }}</td>
                <td class="px-4 py-3">
                  <div class="flex flex-wrap gap-1">
                    <span :class="statusClass(job.status)">{{ statusLabel(job) }}</span>
                    <span v-if="job.resolution?.status" class="whitespace-nowrap rounded bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">{{ resolutionLabel(job) }}</span>
                    <span v-if="job.diagnostics?.stalled" class="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">疑似卡滞</span>
                  </div>
                </td>
                <td class="truncate px-4 py-3 text-slate-600" :title="job.step">{{ formatJobStep(job.step) }}</td>
                <td class="px-4 py-3 text-slate-500">
                  <div>{{ formatDate(job.progress_at || job.started_at || job.created_at) }}</div>
                  <div class="mt-1 text-xs">{{ formatAge(job.diagnostics?.progress_age_seconds) }}</div>
                </td>
                <td class="max-w-[360px] truncate px-4 py-3 text-red-600" :title="job.error || job.error_code">{{ job.error || errorCodeLabel(job.error_code) }}</td>
              </tr>
              <tr v-if="!filteredJobs.length">
                <td colspan="5" class="px-4 py-10 text-center text-slate-500">{{ jobs.length ? '暂无符合筛选条件的任务。' : '暂无任务。' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="filteredJobs.length" data-testid="job-pagination" class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white px-4 py-3">
          <span class="text-xs text-slate-500" aria-current="page">第 {{ jobPage }} / {{ totalJobPages }} 页，共 {{ filteredJobs.length }} 条</span>
          <div class="flex items-center gap-2">
            <button class="btn h-8 px-3 text-xs" :disabled="jobPage <= 1" @click="goToJobPage(jobPage - 1)">上一页</button>
            <button class="btn h-8 px-3 text-xs" :disabled="jobPage >= totalJobPages" @click="goToJobPage(jobPage + 1)">下一页</button>
          </div>
        </div>
      </div>

      <aside class="flex min-h-0 min-w-0 flex-col border-t border-slate-200 bg-slate-950 text-slate-100 min-[1850px]:border-t-0 min-[1850px]:border-l">
        <div class="border-b border-slate-800 p-4">
          <div class="flex items-center justify-between gap-2">
            <div class="min-w-0 truncate text-sm font-semibold">{{ selectedJob?.job_id || '任务日志' }}</div>
            <span v-if="selectedJob" :class="statusClass(selectedJob.status)">{{ statusLabel(selectedJob) }}</span>
          </div>
          <div class="mt-1 text-xs text-slate-400">{{ selectedJob ? `${formatJobType(selectedJob.type)} · ${formatJobStep(selectedJob.step)}` : '选择左侧任务查看日志' }}</div>
           <div v-if="selectedJob?.diagnostics?.stalled" class="mt-3 rounded bg-amber-400/15 px-3 py-2 text-xs text-amber-200">
             {{ diagnosticLabel(selectedJob) }}。系统不会强制终止线程，请结合日志和进程状态处理。
           </div>
          <div v-if="canRepublishCandidate" class="mt-3 rounded border border-slate-700 bg-slate-900 p-3">
            <p class="text-xs leading-5 text-slate-300">该候选已经完成解析，可重新执行候选门禁并发布，不会再次调用 MinerU。</p>
            <button class="btn mt-3 w-full border-blue-400/50 bg-blue-500 text-white hover:bg-blue-400" :disabled="busy" @click="republishCandidate">
              重试发布候选（复用已解析结果）
            </button>
          </div>
          <div v-if="canResolveJob" class="mt-3 rounded border border-amber-700/60 bg-amber-400/10 p-3">
            <p class="text-xs leading-5 text-amber-100">原始失败结果不可修改。记录处置后，质量门禁将不再把这条历史失败计为未解决。</p>
            <label for="job-resolution-status" class="mt-3 block text-xs font-medium text-slate-300">处置类型</label>
            <select id="job-resolution-status" v-model="resolutionStatus" class="field mt-1 w-full bg-slate-900 text-slate-100">
              <option value="acknowledged">已核对，不再阻断</option>
              <option value="superseded">已被成功任务替代</option>
            </select>
            <label for="job-resolution-note" class="mt-3 block text-xs font-medium text-slate-300">处置说明</label>
            <textarea id="job-resolution-note" v-model="resolutionNote" class="field mt-1 min-h-20 w-full bg-slate-900 text-slate-100" rows="3" placeholder="说明失败原因、核对结果和替代证据"></textarea>
            <template v-if="resolutionStatus === 'superseded'">
              <label for="job-related-id" class="mt-3 block text-xs font-medium text-slate-300">成功任务 ID</label>
              <input id="job-related-id" v-model="resolutionRelatedJobId" class="field mt-1 w-full bg-slate-900 text-slate-100" placeholder="关联 succeeded 任务的 ID">
            </template>
            <button class="btn mt-3 w-full border-amber-400/50 bg-amber-500 text-slate-950 hover:bg-amber-300" :disabled="busy || resolvingJob" @click="resolveSelectedJob">
              {{ resolvingJob ? '正在记录...' : '记录失败处置' }}
            </button>
          </div>
          <div v-else-if="selectedJob?.resolution?.status" class="mt-3 rounded border border-slate-700 bg-slate-900 p-3 text-xs text-slate-300">
            <div class="font-semibold text-emerald-300">{{ resolutionLabel(selectedJob) }}</div>
            <p class="mt-2 whitespace-pre-wrap leading-5">{{ selectedJob.resolution.note || '未填写处置说明' }}</p>
            <p class="mt-2 text-slate-500">{{ formatDate(String(selectedJob.resolution.resolved_at || '')) }} · {{ selectedJob.resolution.resolved_by || 'operator' }}</p>
          </div>
         </div>

        <div v-if="selectedJob" class="border-b border-slate-800 p-4">
          <div class="flex items-center justify-between gap-3">
            <span class="text-xs font-semibold uppercase tracking-wide text-slate-400">当前进度</span>
            <span v-if="progressPercent !== null" class="text-sm font-semibold text-blue-300">{{ progressPercent }}%</span>
          </div>
          <div v-if="progressPercent !== null" class="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
            <div class="h-full rounded-full bg-blue-400 transition-[width]" :style="{ width: `${progressPercent}%` }"></div>
          </div>
           <p class="mt-3 text-sm text-slate-100" aria-live="polite">{{ progressMessage }}</p>
          <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-400">
            <div v-if="progressValue('document')" class="rounded bg-slate-900 px-2 py-2">
              <span class="block text-slate-500">当前文档</span>
              <span class="mt-1 block break-all text-slate-200">{{ progressValue('document') }}</span>
            </div>
            <div v-if="progressValue('document_index') || progressValue('document_current') || progressValue('document_total')" class="rounded bg-slate-900 px-2 py-2">
              <span class="block text-slate-500">文档进度</span>
              <span class="mt-1 block text-slate-200">{{ progressValue('document_index') || progressValue('document_current') || '-' }} / {{ progressValue('document_total') || '-' }}</span>
            </div>
            <div v-if="progressValue('page_current') || progressValue('page_total')" class="rounded bg-slate-900 px-2 py-2">
              <span class="block text-slate-500">页面进度</span>
              <span class="mt-1 block text-slate-200">{{ progressValue('page_current') || '-' }} / {{ progressValue('page_total') || '-' }}</span>
            </div>
            <div v-if="progressValue('chunk_current') || progressValue('chunk_total')" class="rounded bg-slate-900 px-2 py-2">
              <span class="block text-slate-500">Chunk 进度</span>
              <span class="mt-1 block text-slate-200">{{ progressValue('chunk_current') || '-' }} / {{ progressValue('chunk_total') || '-' }}</span>
            </div>
          </div>
          <p v-if="progressValue('parser_output')" class="mt-3 break-words text-xs text-slate-500">
            {{ progressValue('parser_output') }}
          </p>
        </div>

        <div v-if="rebuildPlan" class="space-y-2 rounded-md border border-slate-200 bg-white p-3 text-sm">
          <div class="flex items-center justify-between gap-3">
            <span class="font-semibold">变更预检</span>
            <span :class="rebuildPlan.fallback_to_full ? 'text-amber-700' : 'text-emerald-700'">
              {{ rebuildPlan.fallback_to_full ? '将全量回退' : '可增量执行' }}
            </span>
          </div>
          <div class="grid grid-cols-4 gap-1 text-center text-xs">
            <div class="rounded bg-emerald-50 p-2"><strong>{{ planCount('reused') }}</strong><br>复用</div>
            <div class="rounded bg-blue-50 p-2"><strong>{{ planCount('added') }}</strong><br>新增</div>
            <div class="rounded bg-amber-50 p-2"><strong>{{ planCount('changed') }}</strong><br>变化</div>
            <div class="rounded bg-red-50 p-2"><strong>{{ planCount('removed') }}</strong><br>删除</div>
          </div>
          <p v-if="rebuildPlan.fallback_reasons.length" class="break-words text-xs text-amber-700">
            {{ rebuildPlan.fallback_reasons.join('、') }}
          </p>
        </div>
        <div v-if="logsLoading" class="border-b border-slate-800 px-4 py-2 text-xs text-slate-400" role="status">正在加载任务日志...</div>
        <pre class="min-h-0 flex-1 overflow-auto whitespace-pre-wrap p-4 text-xs leading-5 text-slate-200" :aria-busy="logsLoading">{{ logsText }}</pre>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  getAdminJobLogs,
  getAdminRebuildPlan,
  resolveAdminJob,
  startAdminAudit,
  startAdminEvaluation,
  startAdminRebuild,
  startAdminReview,
} from '../admin-api'
import { errorMessage } from '../api'
import type { JobRequest, JobResponse, RebuildPlanResponse } from '../contracts'
import { republishSourceCandidate } from '../source-api'

const props = defineProps<{ jobs: JobResponse[] }>()
const emit = defineEmits<{ refresh: [] }>()

const busy = ref(false)
const error = ref('')
const message = ref('')
const rebuildPlan = ref<RebuildPlanResponse | null>(null)
const selectedJob = ref<JobResponse | null>(null)
const logs = ref<Record<string, unknown>[]>([])
const logsLoading = ref(false)
let logsRequestSerial = 0
const jobFilter = ref('all')
const jobPage = ref(1)
const jobPageSize = ref(10)
const reviewDoc = ref('')
const reviewPages = ref('')
const resolutionStatus = ref<'acknowledged' | 'superseded'>('acknowledged')
const resolutionNote = ref('')
const resolutionRelatedJobId = ref('')
const resolvingJob = ref(false)
const jobRequest = ref<JobRequest>({
  source: 'data/raw',
  parser_backend: 'mineru',
  apply_corrections: true,
  mode: 'incremental',
})

const logsText = computed(() => logs.value.length ? logs.value.map(formatLogEntry).join('\n') : selectedJob.value?.error || '暂无任务日志')
const progressData = computed(() => selectedJob.value?.progress || {})
const progressMessage = computed(() => String(progressData.value.message || '暂无业务进度'))
const progressPercent = computed(() => {
  const value = Number(progressData.value.percent)
  if (!Number.isFinite(value)) return null
  return Math.max(0, Math.min(100, Math.round(value * 10) / 10))
})
const filteredJobs = computed(() => jobFilter.value === 'all'
  ? props.jobs
  : props.jobs.filter(job => job.status === jobFilter.value))
const totalJobPages = computed(() => Math.max(1, Math.ceil(filteredJobs.value.length / jobPageSize.value)))
const paginatedJobs = computed(() => {
  const start = (jobPage.value - 1) * jobPageSize.value
  return filteredJobs.value.slice(start, start + jobPageSize.value)
})

const jobTypeLabels: Record<string, string> = {
  source_rebuild: '知识库重建',
  source_republish: '候选版本发布',
  answer_evaluate: '问答评估',
  evaluate: '结构化评估',
  rebuild: '知识库重建（旧任务）',
}

const jobStepLabels: Record<string, string> = {
  queued: '排队中',
  started: '已开始',
  preflight: '预检',
  build_version: '构建版本',
  candidate_revalidate: '候选版本复核',
  candidate_gate: '候选门禁',
  activate_version: '激活版本',
  active: '已激活',
  finished: '已完成',
  failed: '失败',
}
const queueViewport = ref<HTMLElement | null>(null)
const canRepublishCandidate = computed(() => {
  const job = selectedJob.value
  return Boolean(
    job
    && job.type === 'source_rebuild'
    && job.status === 'failed'
    && typeof job.params?.source_catalog_revision === 'string'
    && job.params.source_catalog_revision,
  )
})
const canResolveJob = computed(() => Boolean(
  selectedJob.value?.status === 'failed' && !selectedJob.value?.resolution?.status,
))

function progressValue(key: string) {
  const value = progressData.value[key]
  return value === undefined || value === null || value === '' ? '' : String(value)
}

async function startJob(task: () => Promise<JobResponse>) {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const job = await task()
    selectedJob.value = job
    logs.value = []
    message.value = `已提交任务 ${job.job_id}`
    emit('refresh')
    await loadLogs(job)
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function analyzeChanges() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    rebuildPlan.value = await getAdminRebuildPlan({ body: jobRequest.value })
    message.value = rebuildPlan.value.fallback_to_full
      ? '预检完成：当前将安全回退为全量重建'
      : '预检完成：可执行增量候选重建'
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

function planCount(action: string) {
  return rebuildPlan.value?.counts?.[action] || 0
}

async function startRebuild() {
  const modeLabel = jobRequest.value.mode === 'full' ? '强制全量重建' : '增量候选重建'
  const parserLabel = jobRequest.value.parser_backend === 'mineru' ? 'MinerU' : 'PyMuPDF'
  const correctionLabel = jobRequest.value.apply_corrections ? '应用已审批修正' : '不应用已审批修正'
  if (!confirm(`将提交${modeLabel}任务，数据源为“${jobRequest.value.source}”，解析器为${parserLabel}，${correctionLabel}。继续吗？`)) return
  await startJob(() => startAdminRebuild({ body: jobRequest.value }))
}

async function republishCandidate() {
  const candidateJobId = selectedJob.value?.job_id
  if (!candidateJobId || !canRepublishCandidate.value) return
  if (!confirm('将重新执行候选门禁并发布该版本，不会重新解析 PDF。继续吗？')) return
  await startJob(async () => {
    const result = await republishSourceCandidate(candidateJobId)
    return result.job as unknown as JobResponse
  })
}

async function resolveSelectedJob() {
  const job = selectedJob.value
  if (!job || !canResolveJob.value) return
  const note = resolutionNote.value.trim()
  const relatedJobId = resolutionRelatedJobId.value.trim()
  if (!note) {
    error.value = '请填写失败任务处置说明。'
    return
  }
  if (resolutionStatus.value === 'superseded' && !relatedJobId) {
    error.value = '“已被成功任务替代”必须填写成功任务 ID。'
    return
  }
  if (!confirm('将保留原始失败结果，并记录这条失败任务的处置说明。继续吗？')) return
  resolvingJob.value = true
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const resolved = await resolveAdminJob({
      path: { job_id: job.job_id },
      body: {
        status: resolutionStatus.value,
        note,
        related_job_id: relatedJobId,
      },
    })
    selectedJob.value = resolved
    resolutionNote.value = ''
    resolutionRelatedJobId.value = ''
    message.value = `任务 ${job.job_id} 已记录为${resolutionLabel(resolved)}`
    emit('refresh')
    await loadLogs(resolved)
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    resolvingJob.value = false
    busy.value = false
  }
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
  logs.value = []
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
  const time = formatDateTime(entry.ts)
  const level = String(entry.level || 'info').toUpperCase()
  const step = entry.step ? ` [${formatJobStep(String(entry.step))}]` : ''
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

function resolutionLabel(job: JobResponse) {
  return ({
    acknowledged: '已处置',
    superseded: '已替代',
  } as Record<string, string>)[String(job?.resolution?.status || '')] || '已处置'
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
  return formatDateTime(value) || '-'
}

function formatDateTime(value: unknown) {
  const raw = String(value || '')
  if (!raw) return ''
  // JavaScript Date accepts milliseconds, while the backend may emit microseconds.
  const normalized = raw.replace(/\.(\d{3})\d+(?=(?:Z|[+-]\d\d:?\d\d)?$)/, '.$1')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime())
    ? raw.replace('T', ' ').replace(/\+\d\d:\d\d$/, '')
    : date.toLocaleString('zh-CN', { hour12: false })
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

function formatJobType(type?: string) {
  if (!type) return '-'
  return jobTypeLabels[type] || type.replaceAll('_', ' ')
}

function formatJobStep(step?: string) {
  if (!step) return '-'
  return jobStepLabels[step] || step.replaceAll('_', ' ')
}

function goToJobPage(page: number) {
  jobPage.value = Math.max(1, Math.min(page, totalJobPages.value))
  void nextTick(() => {
    if (queueViewport.value && typeof queueViewport.value.scrollTo === 'function') {
      queueViewport.value.scrollTo({ top: 0, behavior: 'smooth' })
    }
  })
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
  jobPage.value = Math.min(jobPage.value, totalJobPages.value)
}, { immediate: true })

watch([jobFilter, jobPageSize], () => {
  goToJobPage(1)
  if (selectedJob.value && filteredJobs.value.some(job => job.job_id === selectedJob.value?.job_id)) return
  const nextJob = filteredJobs.value[0]
  selectedJob.value = nextJob || null
  logs.value = []
  if (nextJob) void loadLogs(nextJob)
})

let refreshTimer: number | undefined
const jobControls = ref<HTMLElement | null>(null)
function handlePageAction(event: Event) {
  const detail = (event as CustomEvent<{ key?: string }>).detail
  if (detail?.key !== 'jobs') return
  jobControls.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
onMounted(() => {
  window.addEventListener('admin-page-action', handlePageAction)
  refreshTimer = window.setInterval(() => {
    emit('refresh')
    if (selectedJob.value?.status === 'running' || selectedJob.value?.status === 'queued') {
      loadLogs(selectedJob.value)
    }
  }, 5000)
})
onBeforeUnmount(() => {
  window.removeEventListener('admin-page-action', handlePageAction)
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer)
})
</script>
