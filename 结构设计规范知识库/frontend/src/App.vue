<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="app-brand">
        <div class="app-brand-mark">结</div>
        <div class="min-w-0">
          <div class="app-brand-title">结构规范知识库</div>
          <div class="app-brand-subtitle">Build · Review · Evaluate</div>
        </div>
      </div>

      <div class="sidebar-current">
        <span>当前工作区</span>
        <strong>{{ pageMeta.title }}</strong>
      </div>

      <nav class="app-nav" aria-label="管理后台导航">
        <div class="nav-section-label">生产流程</div>
        <button
          v-for="item in workflowNavItems"
          :key="item.key"
          class="nav-item"
          :class="activeTab === item.key ? 'nav-item-active' : ''"
          :aria-current="activeTab === item.key ? 'page' : undefined"
          type="button"
          @click="activeTab = item.key"
        >
          <span>{{ item.label }}</span>
          <span v-if="item.count" class="nav-count">{{ item.count }}</span>
        </button>

        <div class="nav-section-label nav-section-label-spaced">治理与验证</div>
        <button
          v-for="item in governanceNavItems"
          :key="item.key"
          class="nav-item"
          :class="activeTab === item.key ? 'nav-item-active' : ''"
          :aria-current="activeTab === item.key ? 'page' : undefined"
          type="button"
          @click="activeTab = item.key"
        >
          <span>{{ item.label }}</span>
          <span v-if="item.count" class="nav-count">{{ item.count }}</span>
        </button>
      </nav>

      <div class="sidebar-api-key">
        <label for="sidebar-api-key">API Key</label>
        <form class="sidebar-api-form" @submit.prevent="persistApiKey">
          <input id="sidebar-api-key" v-model="apiKey" type="password" autocomplete="current-password" placeholder="输入后验证">
          <button class="btn btn-sidebar" type="submit">验证</button>
        </form>
        <p>仅保存在当前浏览器 localStorage。</p>
      </div>
    </aside>

    <main class="app-main">
      <header class="app-header">
        <div class="app-header-copy">
          <div class="app-breadcrumb">管理后台 <span>/</span> {{ pageMeta.section }}</div>
          <h1>{{ pageMeta.title }}</h1>
          <p>{{ pageMeta.subtitle }}</p>
          <span class="app-header-status">{{ statusLine }}</span>
        </div>
        <div class="app-header-actions">
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">打开 Open WebUI</a>
          <button class="btn" type="button" :disabled="refreshing" @click="refreshCurrentPage()">
            {{ refreshing ? '刷新中' : '刷新' }}
          </button>
          <button
            v-if="bootstrapState === 'ready' && pageMeta.action"
            class="btn"
            :class="pageMeta.actionPrimary ? 'btn-primary' : ''"
            type="button"
            :disabled="refreshing || pageActionBusy"
            @click="handlePageAction"
          >
            {{ pageMeta.action }}
          </button>
        </div>
      </header>

      <section class="app-content">
        <div v-if="bootstrapState === 'checking'" class="app-state-panel" aria-live="polite">
          <div class="loading-dot" aria-hidden="true"></div>
          <strong>正在连接后端</strong>
          <span>正在读取知识库运行状态和工作流数据</span>
        </div>
        <div v-else-if="bootstrapState === 'unavailable'" class="app-state-panel app-state-error" role="alert">
          <strong>后端暂时不可用</strong>
          <span>{{ bootstrapError }}</span>
          <button class="btn btn-primary" type="button" :disabled="refreshing" @click="refreshAll()">重新连接</button>
        </div>
        <template v-else-if="bootstrapState === 'ready'">
          <OverviewTab v-if="activeTab === 'overview'" :ready="ready" :documents="documents" :metrics="metrics" :quality="quality" @navigate="activeTab = $event" />
          <JobsTab v-if="activeTab === 'jobs'" :jobs="jobs" @refresh="refreshJobs" />
          <VersionsTab v-if="activeTab === 'versions'" @refresh-jobs="refreshJobs" />
          <SourcesTab v-if="activeTab === 'sources'" @refresh-jobs="refreshJobs" />
          <ReviewTab v-if="activeTab === 'review'" :candidate-docs="candidateDocs" @refresh="refreshCandidates" />
          <ManualStructuringTab v-if="activeTab === 'manual'" :documents="manualDocs" :active-data-version="documents.data_version_hash" @refresh="refreshManualStructuring" />
          <EvaluationTab v-if="activeTab === 'evaluation'" :evaluation="evaluation" :quality="quality" :jobs="jobs" @busy="pageActionBusy = $event" @refresh="refreshEvaluationData" />
          <EvaluationSetsTab v-if="activeTab === 'evaluationSets'" @navigate="activeTab = $event" />
          <ChatTab v-if="activeTab === 'chat'" />
        </template>
      </section>
    </main>

    <div v-if="authRequired" class="auth-overlay">
      <form class="auth-dialog" data-testid="auth-form" @submit.prevent="authenticate">
        <div class="auth-dialog-kicker">访问控制</div>
        <h2>需要 API Key</h2>
        <p>后端已拒绝当前访问凭据。请输入有效的 API Key 后继续。</p>
        <label for="auth-api-key">API Key</label>
        <input id="auth-api-key" v-model="authCandidate" class="field" type="password" autocomplete="current-password" autofocus>
        <p v-if="authError" class="auth-error" role="alert">{{ authError }}</p>
        <button class="btn btn-primary auth-submit" type="submit" :disabled="authenticating">
          {{ authenticating ? '正在验证...' : '验证并进入' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  getAdminEvaluationStatus,
  getAdminQualityStatus,
  getAdminStatus,
  listAdminJobs,
  listCorrectionCandidateDocuments,
  listManualStructuringDocuments,
} from './admin-api'
import {
  ApiError,
  AUTH_REQUIRED_EVENT,
  apiGet,
  authorizationHeaders,
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
const SourcesTab = defineAsyncComponent(() => import('./components/SourcesTab.vue'))
const ReviewTab = defineAsyncComponent(() => import('./components/ReviewTab.vue'))
const ManualStructuringTab = defineAsyncComponent(() => import('./components/ManualStructuringTab.vue'))
const EvaluationTab = defineAsyncComponent(() => import('./components/EvaluationTab.vue'))
const EvaluationSetsTab = defineAsyncComponent(() => import('./components/EvaluationSetsTab.vue'))
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
const pageActionBusy = ref(false)
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

const pendingCount = computed(() => candidateDocs.value.reduce((sum, item) => sum + Number(item.pending_count || 0), 0))
const manualPendingCount = computed(() => manualDocs.value.reduce(
  (sum, item) => sum + Number(item.pending_task_count ?? item.pending_count ?? 0),
  0,
))
const runningJobs = computed(() => jobs.value.filter(job => ['queued', 'running'].includes(job.status)).length)

const workflowNavItems = computed(() => [
  { key: 'overview', label: '工作流驾驶舱', count: undefined },
  { key: 'sources', label: '规范来源目录', count: undefined },
  { key: 'jobs', label: '构建任务队列', count: runningJobs.value || undefined },
  { key: 'review', label: '内容校对工作台', count: pendingCount.value || undefined },
  { key: 'manual', label: '复杂表结构化', count: manualPendingCount.value || undefined },
])

const governanceNavItems = computed(() => [
  { key: 'versions', label: '版本管理', count: undefined },
  { key: 'evaluation', label: '质量验证', count: undefined },
  { key: 'evaluationSets', label: '评估集管理', count: undefined },
  { key: 'chat', label: '问答验证', count: undefined },
])

const pageMeta = computed(() => {
  const meta: Record<string, { section: string, title: string, subtitle: string, action: string, actionPrimary?: boolean }> = {
    overview: { section: '生产流程', title: '知识生产工作流', subtitle: '从规范来源到可验证知识包，查看当前阶段、阻塞项和下一步动作。', action: '' },
    sources: { section: '生产流程', title: '规范来源目录', subtitle: '登记来源、审核使用边界，并管理不可变资产版本。', action: '上传 PDF', actionPrimary: true },
    jobs: { section: '生产流程', title: '构建任务队列', subtitle: '提交候选构建，跟踪每个阶段的进度、日志和失败原因。', action: '' },
    review: { section: '生产流程', title: '内容校对工作台', subtitle: '对照原 PDF、解析文本和 AI 证据，完成逐项人工审核。', action: '刷新候选' },
    manual: { section: '生产流程', title: '复杂表结构化队列', subtitle: '保留原页面、行列关系和结构化草稿，完成复杂表人工确认。', action: '扫描复杂表' },
    versions: { section: '治理与验证', title: '版本管理', subtitle: '查看活动版本、候选产物和受保护的版本清理策略。', action: '刷新版本' },
    evaluation: { section: '治理与验证', title: '质量验证中心', subtitle: '把检索、结构化和回答级结果转成可阅读的发布结论。', action: '运行可执行检查', actionPrimary: true },
    evaluationSets: { section: '治理与验证', title: '评估集管理', subtitle: '管理评估用例、版本记录和发布版本，并与质量验证保持清晰分工。', action: '' },
    chat: { section: '治理与验证', title: '问答验证工作区', subtitle: '用真实问题检查检索依据、引用截图和答案渲染效果。', action: '新建验证会话' },
  }
  return meta[activeTab.value] || meta.overview
})

const statusLine = computed(() => {
  if (bootstrapState.value === 'checking') return '正在连接后端'
  if (bootstrapState.value === 'auth-required') return '等待 API Key 验证'
  if (bootstrapState.value === 'unavailable') return '后端连接失败'
  const built = documents.value?.built ? '知识库已构建' : '知识库未构建'
  const count = documents.value?.chunk_count ?? '-'
  const readyText = ready.value?.ready ? '服务已就绪' : '服务未就绪'
  return `${readyText} · ${built} · ${count} 个 Chunk`
})

async function persistApiKey() {
  authCandidate.value = apiKey.value
  await authenticate()
}

function requireAuthentication(event?: Event) {
  if (!authRequired.value && !authenticating.value) authCandidate.value = apiKey.value
  const detail = event instanceof CustomEvent ? event.detail : null
  if (detail?.message) authError.value = String(detail.message)
  authRequired.value = true
  bootstrapState.value = 'auth-required'
  bootstrapError.value = ''
}

function connectionErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.message) return `后端请求失败（HTTP ${error.status}）：${error.message}`
  return '无法连接后端，请确认 API 服务正在运行。'
}

async function probeApiAccess() {
  try {
    await getAdminStatus()
    authRequired.value = false
    authError.value = ''
    bootstrapError.value = ''
    bootstrapState.value = 'ready'
    return true
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) requireAuthentication()
    else {
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
    await getAdminStatus({ headers: authorizationHeaders(candidate) })
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

async function refreshCurrentPage() {
  await refreshAll()
  if (activeTab.value === 'evaluationSets') {
    window.dispatchEvent(new CustomEvent('admin-page-action', { detail: { key: 'evaluationSets' } }))
  }
}

async function refreshStatus() {
  const readyResponse = await fetch('/ready')
  ready.value = await readyResponse.json()
  metrics.value = await apiGet<Record<string, unknown>>('/metrics')
  documents.value = await apiGet<KnowledgeDocumentsView>('/knowledge/documents')
}

async function refreshCandidates() {
  const result = await listCorrectionCandidateDocuments()
  candidateDocs.value = result.documents || []
}

async function refreshManualStructuring() {
  const result = await listManualStructuringDocuments()
  manualDocs.value = result.documents || []
}

async function refreshJobs() {
  const result = await listAdminJobs()
  jobs.value = result.jobs || []
}

async function refreshEvaluation() {
  evaluation.value = await getAdminEvaluationStatus()
}

async function refreshQuality() {
  quality.value = await getAdminQualityStatus()
}

async function refreshEvaluationData() {
  await Promise.allSettled([refreshJobs(), refreshEvaluation(), refreshQuality()])
}

async function handlePageAction() {
  if (pageActionBusy.value) return
  pageActionBusy.value = true
  try {
    if (activeTab.value === 'overview') {
      activeTab.value = manualPendingCount.value ? 'manual' : 'sources'
    } else if (activeTab.value === 'review') {
      await refreshCandidates()
    } else if (activeTab.value === 'jobs') {
      window.dispatchEvent(new CustomEvent('admin-page-action', { detail: { key: 'jobs' } }))
    } else if (activeTab.value === 'versions') {
      window.dispatchEvent(new CustomEvent('admin-page-action', { detail: { key: 'versions' } }))
    } else {
      window.dispatchEvent(new CustomEvent('admin-page-action', { detail: { key: activeTab.value } }))
    }
  } finally {
    pageActionBusy.value = false
  }
}

watch(activeTab, () => refreshAll())
onMounted(() => {
  window.addEventListener(AUTH_REQUIRED_EVENT, requireAuthentication)
  refreshAll()
})
onBeforeUnmount(() => window.removeEventListener(AUTH_REQUIRED_EVENT, requireAuthentication))
</script>
