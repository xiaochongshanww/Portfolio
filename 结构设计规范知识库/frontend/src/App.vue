<template>
  <div class="flex h-dvh flex-col overflow-hidden bg-slate-100 md:flex-row">
    <aside class="flex w-full shrink-0 flex-col border-b border-slate-800 bg-slate-950 text-slate-100 md:w-64 md:border-r md:border-b-0 md:border-slate-200">
      <div class="hidden border-b border-slate-800 px-5 py-4 md:block">
        <div class="text-base font-semibold">结构规范知识库</div>
        <div class="mt-1 text-xs text-slate-400">Build · Review · Evaluate</div>
      </div>
      <nav class="flex shrink-0 gap-1 overflow-x-auto px-2 py-2 md:flex-1 md:block md:space-y-1 md:overflow-visible md:px-3 md:py-4">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="flex w-auto shrink-0 items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm transition md:w-full"
          :class="activeTab === item.key ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'"
          @click="activeTab = item.key"
        >
          <span>{{ item.label }}</span>
          <span v-if="item.count !== undefined" class="rounded bg-white/10 px-2 py-0.5 text-xs">{{ item.count }}</span>
        </button>
      </nav>
      <div class="hidden border-t border-slate-800 p-3 md:block">
        <label class="mb-1 block text-xs text-slate-400">API Key</label>
        <form class="flex gap-2" @submit.prevent="persistApiKey">
          <input v-model="apiKey" class="field h-9 min-w-0 flex-1 bg-slate-900 text-slate-100" type="password" autocomplete="current-password">
          <button class="btn px-2" type="submit">验证</button>
        </form>
      </div>
    </aside>

    <main class="flex min-h-0 min-w-0 flex-1 flex-col">
      <header class="flex min-h-14 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-3 py-2 md:px-5">
        <div class="min-w-0">
          <h1 class="text-base font-semibold md:text-lg">结构设计规范知识库控制台</h1>
          <p class="text-xs text-slate-500">{{ statusLine }}</p>
        </div>
        <div class="flex items-center gap-2">
          <a class="text-sm text-blue-600" href="http://localhost:3000" target="_blank">Open WebUI</a>
          <button class="btn" :disabled="refreshing" @click="refreshAll()">
            {{ refreshing ? '刷新中' : '刷新' }}
          </button>
        </div>
      </header>

      <section class="min-h-0 flex-1 overflow-auto p-3 md:p-5">
        <div
          v-if="bootstrapState === 'checking'"
          class="flex min-h-64 items-center justify-center text-sm text-slate-500"
          aria-live="polite"
        >
          正在连接后端...
        </div>
        <div
          v-else-if="bootstrapState === 'unavailable'"
          class="mx-auto mt-10 max-w-xl border border-rose-200 bg-white p-6 shadow-sm"
          role="alert"
        >
          <h2 class="text-base font-semibold text-slate-900">后端暂时不可用</h2>
          <p class="mt-2 break-words text-sm text-slate-600">{{ bootstrapError }}</p>
          <button class="btn btn-primary mt-5" :disabled="refreshing" @click="refreshAll()">重新连接</button>
        </div>
        <template v-else-if="bootstrapState === 'ready'">
          <OverviewTab v-if="activeTab === 'overview'" :ready="ready" :documents="documents" :metrics="metrics" :quality="quality" />
          <JobsTab v-if="activeTab === 'jobs'" :jobs="jobs" @refresh="refreshJobs" />
          <VersionsTab v-if="activeTab === 'versions'" @refresh-jobs="refreshJobs" />
          <ReviewTab v-if="activeTab === 'review'" :candidate-docs="candidateDocs" @refresh="refreshCandidates" />
          <ManualStructuringTab v-if="activeTab === 'manual'" :documents="manualDocs" @refresh="refreshManualStructuring" />
          <EvaluationTab v-if="activeTab === 'evaluation'" :evaluation="evaluation" :jobs="jobs" @refresh="refreshJobs" />
          <ChatTab v-if="activeTab === 'chat'" />
        </template>
      </section>
    </main>

    <div v-if="authRequired" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
      <form
        class="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl"
        data-testid="auth-form"
        @submit.prevent="authenticate"
      >
        <h2 class="text-lg font-semibold">需要 API Key</h2>
        <p class="mt-2 text-sm text-slate-600">
          后端已拒绝当前访问凭据。请输入有效的 API Key 后继续。
        </p>
        <label class="mt-5 block text-sm font-medium text-slate-700" for="auth-api-key">API Key</label>
        <input
          id="auth-api-key"
          v-model="authCandidate"
          class="field mt-2 w-full"
          type="password"
          autocomplete="current-password"
          autofocus
        >
        <p v-if="authError" class="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{{ authError }}</p>
        <button class="btn btn-primary mt-5 w-full" type="submit" :disabled="authenticating">
          {{ authenticating ? '正在验证...' : '验证并进入' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ApiError,
  AUTH_REQUIRED_EVENT,
  adminGet,
  adminGetWithApiKey,
  apiGet,
  getApiKey,
  setApiKey,
} from './api'
import type {
  CandidateDocumentSummary,
  EvaluationStatusView,
  JobResponse,
  KnowledgeDocumentsView,
  ManualDocumentSummary,
  QualityStatusView,
  ReadinessResponse,
} from './contracts'
import OverviewTab from './components/OverviewTab.vue'
const JobsTab = defineAsyncComponent(() => import('./components/JobsTab.vue'))
const VersionsTab = defineAsyncComponent(() => import('./components/VersionsTab.vue'))
const ReviewTab = defineAsyncComponent(() => import('./components/ReviewTab.vue'))
const ManualStructuringTab = defineAsyncComponent(() => import('./components/ManualStructuringTab.vue'))
const EvaluationTab = defineAsyncComponent(() => import('./components/EvaluationTab.vue'))
const ChatTab = defineAsyncComponent(() => import('./components/ChatTab.vue'))

const activeTab = ref('overview')
const apiKey = ref(getApiKey())
const authCandidate = ref(apiKey.value)
const authRequired = ref(false)
const authError = ref('')
const authenticating = ref(false)
const bootstrapState = ref<'checking' | 'ready' | 'auth-required' | 'unavailable'>('checking')
const bootstrapError = ref('')
const refreshing = ref(false)
const ready = ref<ReadinessResponse | null>(null)
const metrics = ref<Record<string, unknown>>({})
const documents = ref<KnowledgeDocumentsView>({
  built: false,
  documents: [],
  document_count: 0,
  chunk_count: 0,
  image_count: 0,
  data_version_hash: '',
  built_at: '',
  parser_backend: '',
  missing_artifact_count: 0,
})
const candidateDocs = ref<CandidateDocumentSummary[]>([])
const manualDocs = ref<ManualDocumentSummary[]>([])
const jobs = ref<JobResponse[]>([])
const evaluation = ref<EvaluationStatusView>({})
const quality = ref<QualityStatusView>({})

const navItems = computed(() => [
  { key: 'overview', label: '概览' },
  { key: 'jobs', label: '构建任务', count: runningJobs.value || undefined },
  { key: 'versions', label: '版本管理' },
  { key: 'review', label: '校对工作台', count: pendingCount.value || undefined },
  { key: 'manual', label: '结构化队列', count: manualPendingCount.value || undefined },
  { key: 'evaluation', label: '评估' },
  { key: 'chat', label: '问答验证' },
])

const pendingCount = computed(() => candidateDocs.value.reduce((sum, item) => sum + Number(item.pending_count || 0), 0))
const manualPendingCount = computed(() => manualDocs.value.reduce(
  (sum, item) => sum + Number(item.pending_task_count ?? item.pending_count ?? 0),
  0,
))
const runningJobs = computed(() => jobs.value.filter(job => ['queued', 'running'].includes(job.status)).length)
const statusLine = computed(() => {
  if (bootstrapState.value === 'checking') return '正在连接后端'
  if (bootstrapState.value === 'auth-required') return '等待 API Key 验证'
  if (bootstrapState.value === 'unavailable') return '后端连接失败'
  const built = documents.value?.built ? 'built' : 'not built'
  const count = documents.value?.chunk_count ?? '-'
  const readyText = ready.value?.ready ? 'ready' : 'not ready'
  return `${readyText} · ${built} · ${count} chunks`
})

async function persistApiKey() {
  authCandidate.value = apiKey.value
  await authenticate()
}

function requireAuthentication(event?: Event) {
  if (!authRequired.value && !authenticating.value) {
    authCandidate.value = apiKey.value
  }
  const detail = event instanceof CustomEvent ? event.detail : null
  if (detail?.message) authError.value = String(detail.message)
  authRequired.value = true
  bootstrapState.value = 'auth-required'
  bootstrapError.value = ''
}

function connectionErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.message) {
    return `后端请求失败（HTTP ${error.status}）：${error.message}`
  }
  return '无法连接后端，请确认 API 服务正在运行。'
}

async function probeApiAccess() {
  try {
    await adminGet('/admin/status')
    authRequired.value = false
    authError.value = ''
    bootstrapError.value = ''
    bootstrapState.value = 'ready'
    return true
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      requireAuthentication()
    } else {
      authRequired.value = false
      bootstrapState.value = 'unavailable'
      bootstrapError.value = connectionErrorMessage(error)
    }
    return false
  }
}

async function authenticate() {
  const candidate = authCandidate.value.trim()
  if (!candidate) {
    authError.value = '请输入 API Key。'
    return
  }

  authenticating.value = true
  authError.value = ''
  try {
    await adminGetWithApiKey('/admin/status', candidate)
    setApiKey(candidate)
    apiKey.value = candidate
    authRequired.value = false
    bootstrapState.value = 'ready'
    await refreshAll({ skipAccessProbe: true })
  } catch (error) {
    apiKey.value = getApiKey()
    authRequired.value = true
    bootstrapState.value = 'auth-required'
    authError.value = error instanceof Error ? error.message : '认证失败，请检查 API Key。'
  } finally {
    authenticating.value = false
  }
}

async function refreshAll(options: { skipAccessProbe?: boolean } = {}) {
  if (refreshing.value) return
  refreshing.value = true
  try {
    if (!options.skipAccessProbe && !await probeApiAccess()) return
    await Promise.allSettled([refreshStatus(), refreshCandidates(), refreshManualStructuring(), refreshJobs(), refreshEvaluation(), refreshQuality()])
  } finally {
    refreshing.value = false
  }
}

async function refreshStatus() {
  const readyResponse = await fetch('/ready')
  ready.value = await readyResponse.json()
  metrics.value = await apiGet<Record<string, unknown>>('/metrics')
  documents.value = await apiGet<KnowledgeDocumentsView>('/knowledge/documents')
}

async function refreshCandidates() {
  const result = await adminGet('/admin/corrections/candidates')
  candidateDocs.value = result.documents || []
}

async function refreshManualStructuring() {
  const result = await adminGet('/admin/manual-structuring')
  manualDocs.value = result.documents || []
}

async function refreshJobs() {
  const result = await adminGet('/admin/jobs')
  jobs.value = result.jobs || []
}

async function refreshEvaluation() {
  evaluation.value = await adminGet('/admin/evaluation/status')
}

async function refreshQuality() {
  quality.value = await adminGet('/admin/quality/status')
}

watch(activeTab, () => refreshAll())
onMounted(() => {
  window.addEventListener(AUTH_REQUIRED_EVENT, requireAuthentication)
  refreshAll()
})
onBeforeUnmount(() => window.removeEventListener(AUTH_REQUIRED_EVENT, requireAuthentication))
</script>
