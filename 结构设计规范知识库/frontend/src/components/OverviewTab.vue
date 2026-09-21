<template>
  <div class="space-y-5 cockpit-page">
    <section class="panel cockpit-hero">
      <div class="cockpit-hero-copy">
        <div class="section-kicker">下一步操作 · {{ currentStageOwner }}</div>
        <h2>{{ nextActionTitle }}</h2>
        <p>{{ currentStageDescription }}</p>
        <div class="cockpit-hero-meta">{{ currentStageMeta }}</div>
      </div>
      <button class="btn btn-primary" type="button" @click="emit('navigate', currentStageKey)">
        {{ currentStageAction }}
      </button>
    </section>

    <section class="workflow-strip" aria-label="知识库生产流程">
      <button
        v-for="stage in stages"
        :key="stage.key"
        class="workflow-stage"
        :class="stageClass(stage)"
        type="button"
        @click="emit('navigate', stageTarget(stage))"
      >
        <span class="workflow-stage-index">{{ stage.index }}</span>
        <span class="workflow-stage-content">
          <strong>{{ stage.label }}</strong>
          <small>{{ stage.status }}</small>
        </span>
        <span v-if="stage.key !== 'versions'" class="workflow-stage-arrow" aria-hidden="true">›</span>
      </button>
    </section>

    <section class="cockpit-metrics">
      <div class="metric-block">
        <span>当前活动版本</span>
        <strong class="font-mono">{{ shortHash(documents.data_version_hash) }}</strong>
        <small>{{ documents.built_at ? formatDate(documents.built_at) : '尚未记录构建时间' }}</small>
      </div>
      <div class="metric-block">
        <span>来源规范</span>
        <strong>{{ documents.document_count || 0 }} 份</strong>
        <small>当前知识库中的文档数量</small>
      </div>
      <div class="metric-block metric-block-attention">
        <span>人工待处理</span>
        <strong>{{ pendingHumanWork }}</strong>
        <small>{{ pendingHumanLabel }}</small>
      </div>
      <div class="metric-block">
        <span>构建产物状态</span>
        <strong>{{ documents.built ? '已就绪' : '未构建' }}</strong>
        <small>{{ ready?.ready ? '服务检查通过' : '服务检查未通过' }}</small>
      </div>
    </section>

    <div class="cockpit-main-grid">
      <section class="panel current-stage-panel">
        <div class="panel-heading-row">
          <div>
            <div class="section-kicker">CURRENT STAGE</div>
            <h2>当前阶段：{{ currentStageLabel }}</h2>
          </div>
          <span class="status-pill" :class="currentStageStatusClass">{{ currentStageStatus }}</span>
        </div>
        <p class="stage-description">{{ currentStageDescription }}</p>
        <div class="stage-progress-row">
          <div class="stage-progress-track"><span :style="{ width: `${stageProgress}%` }"></span></div>
          <strong>{{ completedStageCount }} / {{ stages.length }} 阶段</strong>
        </div>
        <ol class="stage-checklist">
          <li v-for="item in checklist" :key="item.label" :class="item.state">
            <span class="checklist-icon" aria-hidden="true">{{ item.state === 'done' ? '✓' : item.state === 'current' ? '●' : '○' }}</span>
            <span>{{ item.label }}</span>
          </li>
        </ol>
        <div class="stage-actions">
          <button class="btn" type="button" @click="emit('navigate', stageTargetForKey(currentStageKey))">查看输入与产物</button>
        </div>
      </section>

      <section class="panel timeline-panel">
        <div class="panel-heading-row">
          <div>
            <div class="section-kicker">WORKFLOW CONTEXT</div>
            <h2>流程时间线</h2>
          </div>
          <span class="muted">{{ formatDate(documents.built_at) }}</span>
        </div>
        <ol class="timeline-list">
          <li v-for="item in timeline" :key="item.label" :class="item.state">
            <span class="timeline-node" aria-hidden="true"></span>
            <div><strong>{{ item.label }}</strong><p>{{ item.description }}</p></div>
          </li>
        </ol>
      </section>

      <section class="panel version-context-panel">
        <div class="section-kicker">VERSION CONTEXT</div>
        <h2>版本关系</h2>
        <div class="version-block version-block-active">
          <span>当前活动版本</span>
          <strong class="font-mono">{{ shortHash(documents.data_version_hash) }}</strong>
          <small>{{ documents.built ? '可供检索使用' : '等待首次构建' }}</small>
        </div>
        <div class="version-connector" aria-hidden="true">↓</div>
        <div class="version-block version-block-next">
          <span>下一次发布方向</span>
          <strong>{{ nextReleaseLabel }}</strong>
          <small>{{ nextReleaseDescription }}</small>
        </div>
      </section>
    </div>

    <div class="cockpit-bottom-grid">
      <section class="panel todo-panel">
        <div class="panel-heading-row">
          <div>
            <div class="section-kicker">NEXT ACTIONS</div>
            <h2>待办清单</h2>
          </div>
          <span class="status-pill" :class="pendingHumanWork ? 'status-pill-amber' : 'status-pill-green'">{{ pendingHumanWork ? `${pendingHumanWork} 项` : '已清空' }}</span>
        </div>
        <ul class="todo-list">
          <li :class="manualPending ? 'todo-current' : 'todo-done'"><span>{{ manualPending ? '●' : '✓' }}</span><div><strong>完成复杂表结构化</strong><small>{{ manualPending ? `${manualPending} 项等待人工确认` : '当前没有待处理复杂表' }}</small></div><button v-if="manualPending" class="btn" type="button" @click="emit('navigate', 'manual')">进入队列</button></li>
          <li :class="qualityNeedsAttention ? 'todo-current' : 'todo-done'"><span>{{ qualityNeedsAttention ? '●' : '✓' }}</span><div><strong>通过质量门禁</strong><small>{{ qualityGatePassed ? '当前门禁没有阻断项' : qualityGateRecorded ? '需要处理阻断项并重新验证' : '尚未运行质量评估' }}</small></div><button v-if="qualityNeedsAttention" class="btn" type="button" @click="emit('navigate', 'evaluation')">查看门禁</button></li>
          <li class="todo-neutral"><span>○</span><div><strong>发布候选版本</strong><small>{{ qualityNeedsAttention ? '等待质量门禁完成' : '可在构建任务中提交候选版本' }}</small></div><button class="btn" type="button" @click="emit('navigate', 'jobs')">查看任务</button></li>
        </ul>
      </section>

      <section class="panel quality-preview-panel">
        <div class="panel-heading-row">
          <div>
            <div class="section-kicker">QUALITY GATE</div>
            <h2>质量门禁预览</h2>
          </div>
          <span class="status-pill" :class="qualityGatePassed ? 'status-pill-green' : qualityGateRecorded ? 'status-pill-red' : 'status-pill-amber'">{{ qualityGatePassed ? '已通过' : qualityGateRecorded ? '待处理' : '待验证' }}</span>
        </div>
        <div class="quality-check-list">
          <div v-for="check in qualityChecks" :key="check.label" class="quality-check"><span :class="check.ok ? 'check-ok' : 'check-warn'">{{ check.ok ? '✓' : '!' }}</span><span>{{ check.label }}</span><strong>{{ check.value }}</strong></div>
        </div>
        <button class="btn" type="button" @click="emit('navigate', 'evaluation')">打开质量验证</button>
      </section>
    </div>

    <section class="panel provider-panel">
      <div class="panel-heading-row">
        <div>
          <div class="section-kicker">MODEL CAPABILITY</div>
          <h2>模型供应商状态</h2>
        </div>
        <button class="btn" data-testid="provider-probe-button" type="button" :disabled="probingProviders" title="发起一次最小 Embedding 与聊天调用" @click="runProviderProbe">
          {{ probingProviders ? '检测中' : '检测' }}
        </button>
      </div>
      <div v-if="providerProbeError" class="alert-error" role="alert">{{ providerProbeError }}</div>
      <div v-else-if="providerProbe" class="provider-list">
        <div v-for="item in providerProbe.providers" :key="`${item.provider}:${item.capability}`" class="provider-item">
          <div><strong>{{ providerName(item.provider, item.capability) }}</strong><span>{{ item.model }}</span></div>
          <div class="provider-result"><span :class="providerStatusClass(item.status)">{{ providerStatusLabel(item.status) }}</span><small>{{ item.latency_ms }} ms<span v-if="item.http_status"> · HTTP {{ item.http_status }}</span></small></div>
        </div>
      </div>
      <p v-else class="empty-inline">尚未检测。检测会发起一次最小供应商调用。</p>
    </section>

    <details class="panel diagnostics-panel">
      <summary>查看运行诊断</summary>
      <div class="diagnostics-grid">
        <div><span>Ready 状态</span><strong>{{ ready?.status || 'unknown' }}</strong></div>
        <div><span>Chunk 数</span><strong>{{ documents.chunk_count || 0 }}</strong></div>
        <div><span>图片数</span><strong>{{ documents.image_count || 0 }}</strong></div>
        <div><span>未解决失败任务</span><strong>{{ quality.unresolved_failed_job_count ?? quality.recent_failed_job_count ?? 0 }}</strong></div>
      </div>
      <div v-if="ready?.reasons?.length" class="alert-error">{{ ready.reasons.join('、') }}</div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { probeModelProviders } from '../admin-api'
import { errorMessage } from '../api'
import type { KnowledgeDocumentsView, ProviderProbesResponse, QualityStatusView, ReadinessResponse } from '../contracts'

const props = defineProps<{
  ready: ReadinessResponse | null
  documents: KnowledgeDocumentsView
  metrics: Record<string, unknown>
  quality: QualityStatusView
}>()
const emit = defineEmits<{ navigate: [tab: string] }>()

const probingProviders = ref(false)
const providerProbe = ref<ProviderProbesResponse | null>(null)
const providerProbeError = ref('')

const manualPending = computed(() => Number(props.quality.pending_task_count || 0))
const qualityGateRecorded = computed(() => Boolean(props.quality.quality_gate))
const qualityGatePassed = computed(() => props.quality.quality_gate?.passed === true)
const qualityNeedsAttention = computed(() => !qualityGatePassed.value)
const qualityBlocked = computed(() => qualityGateRecorded.value && !qualityGatePassed.value)
const auditFindingCount = computed(() => Number(props.documents.audit_status?.finding_count || 0))
const auditHighRiskCount = computed(() => Number(props.documents.audit_status?.high_risk_count || 0))
const pendingHumanWork = computed(() => manualPending.value || (qualityNeedsAttention.value ? 1 : 0))
const pendingHumanLabel = computed(() => manualPending.value ? '复杂表等待人工确认' : qualityGatePassed.value ? '当前没有人工阻断项' : qualityGateRecorded.value ? '质量门禁存在阻断' : '质量门禁待验证')
const currentStageKey = computed(() => {
  if (manualPending.value) return 'manual'
  if (!props.documents.built) return 'jobs'
  if (qualityNeedsAttention.value) return 'evaluation'
  return 'versions'
})
const currentStageLabel = computed(() => stages.value.find(item => item.key === currentStageKey.value)?.label || '发布验证')
const currentStageStatus = computed(() => manualPending.value ? '待人工处理' : qualityGateRecorded.value && !qualityGatePassed.value ? '存在阻断' : !qualityGateRecorded.value && props.documents.built ? '待验证' : props.documents.built ? '可继续发布' : '待构建')
const currentStageStatusClass = computed(() => manualPending.value ? 'status-pill-amber' : qualityBlocked.value ? 'status-pill-red' : !qualityGateRecorded.value && props.documents.built ? 'status-pill-amber' : 'status-pill-blue')
const currentStageAction = computed(() => manualPending.value ? '进入复杂表队列' : qualityNeedsAttention.value && props.documents.built ? '打开质量验证' : props.documents.built ? '查看版本关系' : '打开构建任务')
const nextActionTitle = computed(() => manualPending.value ? `完成 ${manualPending.value} 个复杂表结构化任务` : qualityNeedsAttention.value && props.documents.built ? '通过候选质量门禁' : props.documents.built ? '查看当前活动版本' : '提交候选构建')
const currentStageOwner = computed(() => manualPending.value ? '人工处理' : qualityNeedsAttention.value && props.documents.built ? '质量验证' : props.documents.built ? '版本管理' : '系统构建')
const currentStageMeta = computed(() => manualPending.value ? '责任人：内容校对人员 · 阻塞发布：是 · 预计产物：结构化表数据' : qualityNeedsAttention.value && props.documents.built ? `责任人：质量负责人 · 阻塞发布：是 · 产物：质量门禁记录${qualityBlocked.value ? ` · ${props.quality.quality_gate?.failed_checks?.length || 0} 项阻断` : ''}` : props.documents.built ? '责任人：知识库维护人员 · 阻塞发布：否 · 产物：活动知识版本' : '责任人：系统 · 阻塞发布：是 · 产物：候选知识版本')
const currentStageDescription = computed(() => {
  if (manualPending.value) return `检测到 ${manualPending.value} 项复杂表结构化任务。请保留原页面、表格行列关系和适用条件，完成确认后再进入候选构建。`
  if (!props.documents.built) return '当前还没有可用知识库产物。请先提交候选构建，系统会在候选版本中执行解析、索引和门禁。'
  if (!qualityGateRecorded.value) return '当前知识库已构建，但质量门禁尚未运行。请先完成评估，确认检索与回答质量后再发布候选版本。'
  if (qualityBlocked.value) return '质量门禁尚未通过。请查看失败项的具体证据，完成修正或记录可接受的例外后重新验证。'
  return '当前知识库已构建。可以查看活动版本，或进入构建任务提交下一次候选变更。'
})
const completedStageCount = computed(() => stages.value.filter(item => item.state === 'done').length)
const stageProgress = computed(() => Math.round((completedStageCount.value / stages.value.length) * 100))

const stages = computed(() => [
  { key: 'sources', index: '01', label: '规范来源', state: props.documents.document_count ? 'done' : 'current', status: props.documents.document_count ? '已完成' : '待登记' },
  { key: 'jobs', index: '02', label: '候选构建', state: props.documents.built ? 'done' : 'current', status: props.documents.built ? '已完成' : '待构建' },
  { key: 'audit', index: '03', label: '机器审计', state: props.documents.built ? 'done' : 'pending', status: !props.documents.built ? '待前置完成' : auditHighRiskCount.value ? `已完成 · ${auditHighRiskCount.value} 项高风险` : auditFindingCount.value ? `已完成 · ${auditFindingCount.value} 项发现` : '已完成' },
  { key: 'review', index: '04', label: '内容校对', state: props.documents.applied_correction_count ? 'done' : 'pending', status: props.documents.applied_correction_count ? '已完成' : '按需处理' },
  { key: 'manual', index: '05', label: '复杂表', state: manualPending.value ? 'current' : 'done', status: manualPending.value ? `${manualPending.value} 项待处理` : '已完成' },
  { key: 'evaluation', index: '06', label: '质量门禁', state: !manualPending.value && qualityNeedsAttention.value ? 'current' : 'pending', status: !props.documents.built || manualPending.value ? '待前置完成' : qualityBlocked.value ? '待整改' : qualityGatePassed.value ? '已通过' : '待验证' },
  { key: 'versions', index: '07', label: '发布验证', state: props.documents.built && qualityGatePassed.value ? 'current' : 'pending', status: props.documents.built && qualityGatePassed.value ? '可发布' : '待前置完成' },
])

const checklist = computed(() => [
  { label: '来源资产和使用边界已登记', state: props.documents.document_count ? 'done' : 'current' },
  { label: '解析、索引和候选产物已生成', state: props.documents.built ? 'done' : 'current' },
  { label: '复杂表和质量门禁已处理', state: manualPending.value || qualityNeedsAttention.value ? 'current' : props.documents.built ? 'done' : 'pending' },
  { label: '候选版本等待发布', state: props.documents.built && qualityGatePassed.value ? 'current' : 'pending' },
])

const timeline = computed(() => [
  { label: '来源 revision 已固化', description: props.documents.document_count ? '来源目录已经登记，可追溯到资产版本。' : '等待来源目录登记。', state: props.documents.document_count ? 'done' : 'pending' },
  { label: '候选版本构建', description: props.documents.built ? '当前活动知识包已完成构建。' : '等待提交构建任务。', state: props.documents.built ? 'done' : 'current' },
  { label: '人工质量处理', description: manualPending.value ? `${manualPending.value} 项复杂表待确认。` : '当前没有复杂表待处理。', state: manualPending.value ? 'current' : 'done' },
  { label: '候选版本激活', description: qualityNeedsAttention.value ? '质量门禁尚未通过，暂不能激活候选。' : '前置门禁通过后可激活候选。', state: qualityNeedsAttention.value ? 'pending' : 'current' },
])

const nextReleaseLabel = computed(() => manualPending.value ? '复杂表结构化' : qualityNeedsAttention.value ? '质量验证' : '候选版本发布')
const nextReleaseDescription = computed(() => manualPending.value ? `${manualPending.value} 项待人工确认` : !qualityGateRecorded.value ? '尚未运行质量门禁' : qualityBlocked.value ? '存在质量门禁阻断' : '前置条件已满足')
const qualityChecks = computed(() => [
  { label: '自动质量门禁', ok: props.quality.quality_gate?.passed === true, value: props.quality.quality_gate ? (props.quality.quality_gate.passed ? '通过' : '未通过') : '无记录' },
  { label: '候选版本激活', ok: props.quality.candidate_activation?.passed === true, value: props.quality.candidate_activation?.available ? (props.quality.candidate_activation.passed ? '通过' : '未通过') : '无记录' },
  { label: '结构化评估', ok: (props.quality.structured_evaluation?.structured_table_hit_rate || 0) >= .95, value: percent(props.quality.structured_evaluation?.structured_table_hit_rate) },
  { label: '回答级盲测', ok: (props.quality.answer_evaluation?.pass_rate || 0) >= .95, value: percent(props.quality.answer_evaluation?.pass_rate) },
])

function stageClass(stage: { key: string, state: string }) {
  return stage.key === currentStageKey.value ? 'workflow-stage-current' : `workflow-stage-${stage.state}`
}
function stageTarget(stage: { key: string }) { return stageTargetForKey(stage.key) }
function stageTargetForKey(key: string) { return key === 'audit' ? 'jobs' : key }
function shortHash(value?: string) { return value ? value.slice(0, 12) : '尚未生成' }
function formatDate(value?: string) { if (!value) return '暂无时间'; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false }) }
function percent(value?: number | null) { return typeof value === 'number' ? `${Math.round(value * 100)}%` : '-' }

const providerStatusLabels: Record<string, string> = { ok: '可用', not_configured: '未配置', auth_failed: '鉴权失败', rate_limited: '已限流', timeout: '超时', unavailable: '不可用', request_failed: '请求失败', invalid_response: '响应无效' }
async function runProviderProbe() {
  if (probingProviders.value) return
  probingProviders.value = true
  providerProbeError.value = ''
  try { providerProbe.value = await probeModelProviders() } catch (error) { providerProbe.value = null; providerProbeError.value = errorMessage(error) } finally { probingProviders.value = false }
}
function providerName(provider: string, capability: string) { if (provider === 'zhipuai' && capability === 'embedding') return '智谱 Embedding'; if (provider === 'mimo' && capability === 'chat') return 'MiMo 聊天'; return `${provider} ${capability}` }
function providerStatusLabel(status: string) { return providerStatusLabels[status] || status }
function providerStatusClass(status: string) { if (status === 'ok') return 'provider-ok'; if (['rate_limited', 'timeout'].includes(status)) return 'provider-warn'; if (status === 'not_configured') return 'provider-muted'; return 'provider-error' }
</script>
