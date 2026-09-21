<template>
  <div class="evaluation-page space-y-5">
    <section class="panel overflow-hidden">
      <div class="border-b border-slate-200 p-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="panel-title">候选质量门禁</h2>
            <p class="muted mt-1">逐项展示发布前的必要条件和阻断原因。</p>
          </div>
          <span class="status-pill" :class="qualityGateStatus.className">{{ qualityGateStatus.status }}</span>
        </div>
      </div>

      <div class="p-5">
        <div class="divide-y divide-slate-200 border-t border-slate-200">
          <article v-for="item in gateItems" :key="item.key" class="flex items-start gap-3 py-4 first:pt-4">
            <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold" :class="item.iconClass">{{ item.icon }}</span>
            <div class="min-w-0 flex-1">
              <strong class="text-sm text-slate-900">{{ item.label }}</strong>
              <p class="mt-1 text-sm leading-6 text-slate-600">{{ item.description }}</p>
              <p v-if="item.detail" class="mt-1 text-xs leading-5 text-slate-500">{{ item.detail }}</p>
            </div>
            <span class="status-pill" :class="item.className">{{ item.status }}</span>
          </article>
        </div>

        <div class="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
          <strong>{{ gateNotice.title }}</strong>
          <p class="mt-1">{{ gateNotice.description }}</p>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <button class="btn btn-primary" :disabled="busy" @click="runQualityChecks">{{ busy ? '提交中...' : '运行可执行检查' }}</button>
          <button class="btn" :disabled="busy" @click="exportQualityEvidence">导出质量证据</button>
        </div>
        <p v-if="message" class="mt-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{{ message }}</p>
        <p v-if="error" class="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </div>
    </section>

    <section v-if="refreshPendingCount" class="panel overflow-hidden border-amber-200">
      <div class="flex flex-wrap items-start justify-between gap-4 border-b border-amber-200 bg-amber-50 p-5">
        <div>
          <h2 class="panel-title">评估集变更待重跑</h2>
          <p class="muted mt-1">评估集发布后，旧质量报告不能继续作为当前修订的证据。</p>
        </div>
        <span class="status-pill status-pill-amber">{{ refreshPendingCount }} 项待处理</span>
      </div>
      <div class="divide-y divide-slate-200 px-5">
        <div v-for="item in refreshItems" :key="item.event_id" class="flex flex-wrap items-center justify-between gap-3 py-3">
          <div>
            <strong class="text-sm text-slate-900">{{ refreshSetLabel(item.evaluation_set_id) }}</strong>
            <p class="mt-1 text-xs text-slate-500">修订 {{ item.revision_id }} · {{ refreshMissingLabel(item) }}</p>
          </div>
          <span class="text-xs text-amber-700">等待对应评估报告</span>
        </div>
      </div>
      <div class="border-t border-slate-200 p-5">
        <button class="btn btn-primary" :disabled="busy" @click="runQualityChecks">运行受影响评估</button>
      </div>
    </section>

    <section class="panel overflow-hidden">
      <div class="border-b border-slate-200 p-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="panel-title">最近评估结果</h2>
            <p class="muted mt-1">将机器指标翻译成可阅读的结论。</p>
          </div>
          <details v-if="latest || structuredLatest || answerLatest" class="relative text-sm">
            <summary class="cursor-pointer text-slate-600">查看原始报告</summary>
            <pre class="absolute right-5 z-10 mt-2 max-h-96 max-w-[min(720px,calc(100vw-40px))] overflow-auto rounded-md bg-slate-950 p-4 text-left text-xs leading-5 text-slate-100 shadow-lg">{{ formattedReports }}</pre>
          </details>
        </div>
      </div>

      <div class="p-5">
        <div class="rounded-md border p-4" :class="resultSummary.className">
          <h3 class="text-base font-semibold">{{ resultSummary.title }}</h3>
          <p class="mt-1 text-sm leading-6">{{ resultSummary.description }}</p>
        </div>

        <div class="mt-5 divide-y divide-slate-200 border-y border-slate-200">
          <div v-for="metric in resultMetrics" :key="metric.label" class="flex items-center justify-between gap-4 py-3">
            <span class="text-sm text-slate-600">{{ metric.label }}</span>
            <strong class="text-sm" :class="metric.className">{{ metric.value }}</strong>
          </div>
        </div>

        <section v-if="reportFailures.length" class="mt-5">
          <div class="mb-2 flex items-center justify-between">
            <h3 class="text-sm font-semibold">评估失败用例</h3>
            <span class="text-xs text-slate-500">{{ reportFailures.length }} 项</span>
          </div>
          <div class="space-y-3">
            <article v-for="item in reportFailures" :key="item.key" class="rounded-md border border-rose-200 bg-rose-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <strong class="text-sm text-rose-900">{{ item.source }} · {{ item.id }}</strong>
                <span class="text-xs text-rose-700">{{ item.checks }}</span>
              </div>
              <p class="mt-2 text-sm leading-6 text-slate-700">{{ item.query || item.error || '未提供失败详情。' }}</p>
              <details v-if="item.answer || item.error" class="mt-2">
                <summary class="cursor-pointer text-xs font-medium text-slate-600">查看原始响应</summary>
                <pre class="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded bg-white p-3 text-xs leading-5">{{ item.answer || item.error }}</pre>
              </details>
            </article>
          </div>
        </section>
        <div v-else class="mt-5 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">当前评估报告没有失败用例。</div>

        <div class="mt-5 flex flex-wrap gap-2 border-t border-slate-200 pt-4">
          <button class="btn" :disabled="busy" @click="runStructuredEvaluation">单独运行结构化评估</button>
          <button class="btn" :disabled="busy" @click="runAnswerEvaluation">单独运行回答盲测</button>
        </div>
      </div>
    </section>

    <section class="panel overflow-hidden">
      <div class="border-b border-slate-200 p-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="panel-title">质量运行比较</h2>
            <p class="muted mt-1">只比较已完成且完整性校验通过的运行，区分评估集、运行数据和实现变化。</p>
          </div>
          <button class="btn" type="button" :disabled="compareBusy" @click="loadQualityRuns">刷新运行列表</button>
        </div>
      </div>
      <div class="p-5">
        <div class="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          <label class="text-sm text-slate-600">基线运行
            <select v-model="baselineRunId" class="field mt-1 w-full">
              <option value="">请选择运行</option>
              <option v-for="run in qualityRuns" :key="`base-${run.verification_run_id}`" :value="run.verification_run_id">{{ runLabel(run) }}</option>
            </select>
          </label>
          <label class="text-sm text-slate-600">候选运行
            <select v-model="candidateRunId" class="field mt-1 w-full">
              <option value="">请选择运行</option>
              <option v-for="run in qualityRuns" :key="`candidate-${run.verification_run_id}`" :value="run.verification_run_id">{{ runLabel(run) }}</option>
            </select>
          </label>
          <button class="btn btn-primary self-end" type="button" :disabled="compareBusy || !baselineRunId || !candidateRunId" @click="compareRuns">比较</button>
        </div>
        <div v-if="comparison" class="mt-5 space-y-4">
          <div class="rounded-md border p-4" :class="comparison.summary?.evaluation_set_changed || comparison.summary?.runtime_changed ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'">
            <strong class="text-sm text-slate-900">{{ comparison.summary?.interpretation || '已完成比较。' }}</strong>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[640px] text-left text-sm">
              <thead class="bg-slate-50 text-xs text-slate-500"><tr><th class="px-3 py-3">评估类型</th><th class="px-3 py-3">评估集变化</th><th class="px-3 py-3">指标变化</th><th class="px-3 py-3">失败用例变化</th></tr></thead>
              <tbody>
                <tr v-for="row in comparisonRows" :key="row.kind" class="border-t border-slate-100">
                  <td class="px-3 py-3 font-medium text-slate-900">{{ row.label }}</td>
                  <td class="px-3 py-3">{{ row.changed ? '有变化' : '未变化' }}</td>
                  <td class="px-3 py-3">{{ row.metricSummary }}</td>
                  <td class="px-3 py-3">新增 {{ row.added }} · 减少 {{ row.removed }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <p v-else class="mt-4 text-sm text-slate-500">选择两个质量运行后查看比较结果。</p>
        <p v-if="compareError" class="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{{ compareError }}</p>
      </div>
    </section>

    <section class="panel overflow-hidden">
      <div class="border-b border-slate-200 p-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="panel-title">需要关注的失败项</h2>
            <p class="muted mt-1">失败项不会自动修改当前活动版本，请先判断是数据、评估证据、任务还是外部服务问题。</p>
          </div>
          <span class="status-pill" :class="gateFailures.length ? 'status-pill-red' : 'status-pill-green'">{{ gateFailures.length ? `${gateFailures.length} 项` : '无阻断' }}</span>
        </div>
      </div>
      <div v-if="gateFailures.length" class="divide-y divide-slate-200 px-5">
        <article v-for="item in gateFailures" :key="item.key" class="py-4">
          <div class="flex flex-wrap items-center gap-2">
            <strong class="text-sm text-slate-900">{{ item.title }}</strong>
            <span class="rounded bg-rose-100 px-2 py-0.5 text-xs text-rose-700">{{ item.category }}</span>
          </div>
          <p class="mt-1 text-sm leading-6 text-slate-600">{{ item.description }}</p>
          <p v-if="item.action" class="mt-1 text-xs leading-5 text-slate-500">建议：{{ item.action }}</p>
        </article>
      </div>
      <div v-else class="p-5 text-sm text-emerald-700">当前没有需要关注的门禁失败项。</div>
    </section>

    <EvaluationSetBrowser />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  compareAdminQualityRuns,
  listAdminQualityRuns,
  startAdminAnswerEvaluation,
  startAdminEvaluation,
} from '../admin-api'
import { errorMessage } from '../api'
import type {
  EvaluationFailureView,
  EvaluationReportView,
  EvaluationStatusView,
  JobResponse,
  QualityCheckView,
  QualityGateView,
  QualityReportCompareView,
  QualityRunSummary,
  QualityStatusView,
} from '../contracts'
import EvaluationSetBrowser from './EvaluationSetBrowser.vue'

type UiStatus = { status: string; className: string; icon: string; iconClass: string }
type GateItem = UiStatus & { key: string; label: string; description: string; detail: string }
type GateFailure = { key: string; title: string; category: string; description: string; action: string }
type ReportFailure = EvaluationFailureView & { key: string; source: string; checks: string }

const props = defineProps<{ evaluation: EvaluationStatusView; quality?: QualityStatusView; jobs?: JobResponse[] }>()
const emit = defineEmits<{ refresh: []; busy: [value: boolean] }>()

const busy = ref(false)
const error = ref('')
const message = ref('')
const qualityRuns = ref<QualityRunSummary[]>([])
const baselineRunId = ref('')
const candidateRunId = ref('')
const comparison = ref<QualityReportCompareView | null>(null)
const compareBusy = ref(false)
const compareError = ref('')
const latest = computed(() => props.evaluation?.latest || null)
const structuredLatest = computed(() => props.evaluation?.structured_latest || null)
const answerLatest = computed(() => props.evaluation?.answer_latest || null)
const quality = computed(() => props.quality || {})
const qualityGate = computed<QualityGateView>(() => quality.value.quality_gate || {})
const checks = computed(() => Object.fromEntries((qualityGate.value.checks || []).map(item => [item.name || '', item])))
const check = (name: string) => checks.value[name] as QualityCheckView | undefined
const refreshItems = computed(() => (quality.value.evaluation_refresh?.items || []).filter(item => item.status === 'pending'))
const refreshPendingCount = computed(() => Number(quality.value.evaluation_refresh?.pending_count || refreshItems.value.length))
const comparisonRows = computed(() => Object.entries(comparison.value?.evaluation_sets || {}).map(([kind, item]) => {
  const labels: Record<string, string> = { regular: '常规检索', structured: '结构化检索', answer: '回答级验证' }
  const deltas = Object.values(item.metrics || {}).map(metric => metric.delta).filter(value => typeof value === 'number') as number[]
  return {
    kind,
    label: labels[kind] || kind,
    changed: Boolean(item.evaluation_set_changed),
    metricSummary: deltas.length ? deltas.map(value => `${value >= 0 ? '+' : ''}${Math.round(value * 100)} 个百分点`).join('、') : '无数值变化',
    added: item.failures?.added?.length || 0,
    removed: item.failures?.removed?.length || 0,
  }
}))

const setLabels: Record<string, string> = { regular: '常规检索评估', structured: '结构化专项评估', answer: '回答级盲测' }
function refreshSetLabel(id?: string) { return setLabels[id || ''] || id || '未知评估集' }
function refreshMissingLabel(item: { missing_report_types?: string[] }) {
  return (item.missing_report_types || []).map(refreshSetLabel).join('、') || '报告已更新'
}
function runLabel(run: QualityRunSummary) {
  return `${run.completed_at.replace('T', ' ').slice(0, 19)} · ${run.passed ? '通过' : '未通过'} · ${run.verification_run_id.slice(0, 8)}`
}

function reportAvailable(report?: EvaluationReportView | null, count?: number) {
  return Boolean(report || (typeof count === 'number' && count > 0))
}

function status(statusValue: string, className: string, icon: string, iconClass: string): UiStatus {
  return { status: statusValue, className, icon, iconClass }
}

function passedStatus(): UiStatus { return status('已通过', 'status-pill-green', '✓', 'bg-emerald-100 text-emerald-700') }
function failedStatus(): UiStatus { return status('未通过', 'status-pill-red', '!', 'bg-rose-100 text-rose-700') }
function pendingStatus(label = '待执行'): UiStatus { return status(label, 'status-pill-amber', '·', 'bg-amber-100 text-amber-700') }

function reportGateStatus(
  name: string,
  report: EvaluationReportView | null,
  summary: { case_count?: number; failure_count?: number } | undefined,
  pendingLabel: string,
): UiStatus & { detail: string } {
  if (!reportAvailable(report, summary?.case_count)) {
    return { ...pendingStatus(pendingLabel), detail: check(`${name}_evaluation`)?.message || '尚未生成对应评估报告。' }
  }
  const evaluationCheck = check(`${name}_evaluation`)
  const freshnessCheck = check(`${name}_report_freshness`)
  if (evaluationCheck?.status === 'failed') {
    return { ...failedStatus(), detail: evaluationCheck.message || '评估结果未达到门禁要求。' }
  }
  if (freshnessCheck?.status === 'failed') {
    return { ...pendingStatus('待更新'), detail: freshnessCheck.message || '评估报告需要重新生成或更新。' }
  }
  if (summary?.failure_count) {
    return { ...failedStatus(), detail: `当前报告包含 ${summary.failure_count} 项失败用例。` }
  }
  return { ...passedStatus(), detail: evaluationCheck?.message || '评估结果满足当前门禁要求。' }
}

const gateItems = computed<GateItem[]>(() => {
  const candidate = quality.value.candidate_activation
  const runtimeChecks = ['manifest', 'knowledge_base', 'required_artifacts', 'active_db_pointer', 'runtime_collection']
  const runtimeFailure = runtimeChecks.map(name => check(name)).find(item => item?.status === 'failed')
  const runtimeStatus = candidate?.available === false || candidate?.passed === false
    ? failedStatus()
    : runtimeFailure
      ? failedStatus()
      : candidate?.available === true
        ? passedStatus()
        : pendingStatus('待检查')

  const regular = reportGateStatus('regular', latest.value, quality.value.regular_evaluation, '待执行')
  const structured = reportGateStatus('structured', structuredLatest.value, quality.value.structured_evaluation, '待执行')
  const answer = reportGateStatus('answer', answerLatest.value, quality.value.answer_evaluation, '待触发')
  return [
    {
      key: 'candidate-runtime',
      label: '候选运行时',
      description: '版本可独立加载，不影响当前活动版本。',
      detail: runtimeFailure?.message || (candidate?.passed === false ? '候选版本没有通过激活前检查。' : '候选版本运行环境和必需产物检查通过。'),
      ...runtimeStatus,
    },
    {
      key: 'regular-evaluation',
      label: '常规检索评估',
      description: `${quality.value.regular_evaluation?.case_count || latest.value?.case_count || 0} 条用例 · 来源、条文和关键词命中率达标。`,
      ...regular,
    },
    {
      key: 'structured-evaluation',
      label: '结构化检索评估',
      description: '需要复杂表任务完成并重新生成候选版本。',
      ...structured,
    },
    {
      key: 'answer-evaluation',
      label: '回答级验证',
      description: '需要在新活动版本上执行盲测和引用检查。',
      ...answer,
    },
  ]
})

const qualityGateStatus = computed<UiStatus>(() => {
  if (qualityGate.value.passed === true) return passedStatus()
  if (gateItems.value.some(item => ['待执行', '待触发', '待更新', '待检查'].includes(item.status))) return pendingStatus('部分待执行')
  return failedStatus()
})

const gateNotice = computed(() => {
  if (qualityGate.value.passed === true) {
    return { title: '候选质量门禁已通过。', description: '当前候选版本满足已配置的发布检查，可以进入版本发布流程。' }
  }
  return {
    title: '当前活动版本仍可继续使用，但候选版本尚未满足全部发布条件。',
    description: '常规检索结果通过不代表结构化表和回答级质量已经通过；请根据下方阻断项处理后重新验证。',
  }
})

function metric(value: number | undefined | null, fallback: number | undefined | null, report: EvaluationReportView | null, summary: { case_count?: number } | undefined) {
  const actual = typeof value === 'number' ? value : fallback
  if (typeof actual !== 'number' || !reportAvailable(report, summary?.case_count)) return { value: '待执行', className: 'text-amber-700' }
  return { value: `${Math.round(actual * 100)}%`, className: actual >= 0.95 ? 'text-emerald-700' : actual >= 0.85 ? 'text-amber-700' : 'text-rose-700' }
}

const resultMetrics = computed(() => [
  { label: '来源命中率', ...metric(latest.value?.source_hit_rate, latest.value?.authority_hit_rate || quality.value.regular_evaluation?.authority_hit_rate, latest.value, quality.value.regular_evaluation) },
  { label: '条文命中率', ...metric(latest.value?.clause_hit_rate, null, latest.value, quality.value.regular_evaluation) },
  { label: '关键词命中率', ...metric(latest.value?.keyword_hit_rate, null, latest.value, quality.value.regular_evaluation) },
  { label: '结构化表命中率', ...metric(structuredLatest.value?.structured_table_hit_rate, quality.value.structured_evaluation?.structured_table_hit_rate, structuredLatest.value, quality.value.structured_evaluation) },
  { label: '回答级通过率', ...metric(answerLatest.value?.pass_rate, quality.value.answer_evaluation?.pass_rate, answerLatest.value, quality.value.answer_evaluation) },
])

const resultSummary = computed(() => {
  if (qualityGate.value.passed === true) return { title: '候选版本可以进入发布流程', description: '候选运行时和各项质量评估均已通过当前门禁。', className: 'border-emerald-200 bg-emerald-50 text-emerald-800' }
  if (!qualityGate.value.checks?.length) return { title: '质量门禁尚未形成结论', description: '请先运行可执行检查，生成与当前数据版本对应的质量证据。', className: 'border-amber-200 bg-amber-50 text-amber-800' }
  return { title: '当前活动版本可继续使用', description: '当前候选版本未满足全部发布条件，处理阻断项并重新验证后才能进入发布流程。', className: 'border-amber-200 bg-amber-50 text-amber-800' }
})

function failureSource(report: EvaluationReportView | null, source: string): ReportFailure[] {
  return (report?.failures || []).map((item, index) => ({
    ...item,
    key: `${source}-${item.id}-${index}`,
    source,
    checks: (item.failed_checks || []).join('、') || '未通过',
  }))
}

const reportFailures = computed(() => [
  ...failureSource(latest.value, '常规检索'),
  ...failureSource(structuredLatest.value, '结构化检索'),
  ...failureSource(answerLatest.value, '回答级验证'),
])

const gateFailureLabels: Record<string, { title: string; category: string; action: string }> = {
  evaluation_report_integrity: { title: '评估报告完整性', category: '质量证据', action: '检查最新质量运行指针和报告文件。' },
  runtime_config_consistency: { title: '评估运行配置指纹不一致', category: '质量证据', action: '按当前运行配置重新执行完整质量验证。' },
  regular_evaluation: { title: '常规检索评估未通过', category: '检索质量', action: '查看常规评估失败用例并修正检索或数据问题。' },
  structured_evaluation: { title: '结构化检索评估未通过', category: '结构化质量', action: '完成复杂表结构化后重新构建并执行评估。' },
  answer_evaluation: { title: '回答级验证未通过', category: '外部服务或回答质量', action: '检查模型服务、引用和截图可访问性后重新执行。' },
  regular_report_freshness: { title: '常规评估证据已过期', category: '质量证据', action: '重新运行常规检索评估。' },
  structured_report_freshness: { title: '结构化评估证据已过期', category: '质量证据', action: '重新运行结构化专项评估。' },
  answer_report_freshness: { title: '回答评估证据已过期', category: '质量证据', action: '重新运行回答级盲测。' },
  unresolved_jobs: { title: '存在未解决失败任务', category: '任务状态', action: '在构建任务队列查看失败日志并处理。' },
  stale_jobs: { title: '存在卡住的活动任务', category: '任务状态', action: '检查活动任务进程和日志。' },
}

const gateFailures = computed<GateFailure[]>(() => {
  const failedNames = new Set(qualityGate.value.failed_checks || [])
  return (qualityGate.value.checks || [])
    .filter(item => item.status === 'failed' || failedNames.has(item.name || ''))
    .map(item => {
      const name = item.name || 'unknown'
      const info = gateFailureLabels[name] || { title: name, category: '质量门禁', action: '查看检查详情并重新验证。' }
      return { key: name, title: info.title, category: info.category, description: item.message || '该检查未通过。', action: info.action }
    })
})

const formattedReports = computed(() => JSON.stringify({
  quality_gate: qualityGate.value,
  regular_evaluation: latest.value,
  structured_evaluation: structuredLatest.value,
  answer_evaluation: answerLatest.value,
}, null, 2))

async function submitEvaluationTasks(tasks: Array<Promise<JobResponse>>, label: string) {
  busy.value = true
  emit('busy', true)
  error.value = ''
  try {
    const results = await Promise.allSettled(tasks)
    const succeeded = results.filter(item => item.status === 'fulfilled').length
    if (!succeeded) throw new Error(`${label}提交失败。`)
    message.value = `已提交 ${succeeded} 项${label}，任务完成后请刷新质量门禁。`
    await loadQualityRuns()
    emit('refresh')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
    emit('busy', false)
  }
}

async function loadQualityRuns() {
  try {
    const response = await listAdminQualityRuns({ query: { limit: 50 } })
    qualityRuns.value = response.runs || []
  } catch {
    qualityRuns.value = []
  }
}

async function compareRuns() {
  if (!baselineRunId.value || !candidateRunId.value) return
  compareBusy.value = true
  compareError.value = ''
  comparison.value = null
  try {
    const response = await compareAdminQualityRuns({ query: { baseline_run_id: baselineRunId.value, candidate_run_id: candidateRunId.value } })
    comparison.value = response.comparison as QualityReportCompareView
  } catch (cause) {
    compareError.value = errorMessage(cause)
  } finally {
    compareBusy.value = false
  }
}

function runQualityChecks() {
  return submitEvaluationTasks([
    startAdminEvaluation({ body: { top_k: 5, evaluation_set: 'regular' } }),
    startAdminEvaluation({ body: { top_k: 5, evaluation_set: 'structured' } }),
    startAdminAnswerEvaluation({ body: { evaluation_set: 'answer' } }),
  ], '质量检查')
}

function runStructuredEvaluation() {
  return submitEvaluationTasks([
    startAdminEvaluation({ body: { top_k: 5, evaluation_set: 'structured' } }),
  ], '结构化专项评估')
}

function runAnswerEvaluation() {
  return submitEvaluationTasks([
    startAdminAnswerEvaluation({ body: { evaluation_set: 'answer' } }),
  ], '回答级盲测')
}

function exportQualityEvidence() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-')
  const blob = new Blob([formattedReports.value], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `quality-evidence-${stamp}.json`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
  message.value = '已导出当前质量门禁和评估报告摘要。'
}

function handlePageAction(event: Event) {
  const detail = (event as CustomEvent<{ key?: string }>).detail
  if (detail?.key === 'evaluation') void runQualityChecks()
}

onMounted(() => {
  window.addEventListener('admin-page-action', handlePageAction)
  void loadQualityRuns()
})
onBeforeUnmount(() => window.removeEventListener('admin-page-action', handlePageAction))
</script>
