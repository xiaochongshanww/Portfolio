<template>
  <div class="grid gap-5 xl:grid-cols-[1fr_420px]">
    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <MetricCard label="文档数" :value="documents.document_count ?? 0" />
      <MetricCard label="Chunk 数" :value="documents.chunk_count ?? 0" />
      <MetricCard label="图片数" :value="documents.image_count ?? 0" />
      <MetricCard label="应用修正" :value="documents.applied_correction_count ?? correctionCount" />
      <div class="panel col-span-full p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="panel-title">文档清单</h2>
          <span class="muted max-w-[60%] break-all text-right">{{ documents.data_version_hash || '-' }}</span>
        </div>
        <div class="overflow-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-slate-50 text-xs text-slate-500">
              <tr><th class="px-3 py-2">规范</th><th class="px-3 py-2">编号</th><th class="px-3 py-2">版本</th><th class="px-3 py-2">Chunk</th><th class="px-3 py-2">状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="doc in documents.documents || []" :key="doc.source_file" class="border-t border-slate-100">
                <td class="px-3 py-2">{{ doc.name }}</td>
                <td class="px-3 py-2">{{ doc.code }}</td>
                <td class="px-3 py-2">{{ doc.version || '-' }}</td>
                <td class="px-3 py-2">{{ doc.chunk_count }}</td>
                <td class="px-3 py-2">{{ doc.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="panel col-span-full p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="panel-title">质量运营</h2>
          <span class="muted">自动化状态与人工工作量</span>
        </div>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCard label="待处理逻辑表" :value="quality.pending_task_count ?? 0" />
          <MetricCard label="AI 建议覆盖" :value="`${quality.suggestion_count ?? 0}/${quality.logical_task_count ?? 0}`" />
          <MetricCard label="人工发布资产" :value="quality.manual_publication_count ?? 0" />
          <MetricCard label="未解决失败任务" :value="quality.unresolved_failed_job_count ?? quality.recent_failed_job_count ?? 0" />
        </div>
        <div class="mt-4 grid gap-4 md:grid-cols-2">
          <div class="rounded-md border border-slate-200 p-3">
            <div class="text-xs font-medium text-slate-500">草稿状态</div>
            <KeyValueList class="mt-2" :data="quality.draft_statuses || {}" />
          </div>
          <div class="rounded-md border border-slate-200 p-3">
            <div class="text-xs font-medium text-slate-500">评估状态</div>
            <div class="mt-2 space-y-2 text-sm">
              <div class="flex justify-between"><span>常规失败</span><strong>{{ quality.regular_evaluation?.failure_count ?? '-' }}</strong></div>
              <div class="flex justify-between"><span>结构化命中率</span><strong>{{ percent(quality.structured_evaluation?.structured_table_hit_rate) }}</strong></div>
              <div class="flex justify-between"><span>回答通过率</span><strong>{{ percent(quality.answer_evaluation?.pass_rate) }}</strong></div>
              <div class="flex justify-between"><span>截图可访问率</span><strong>{{ percent(quality.answer_evaluation?.image_http_rate) }}</strong></div>
              <div class="flex justify-between"><span>阻断建议</span><strong>{{ quality.blocked_suggestion_count ?? 0 }}</strong></div>
              <div class="flex justify-between">
                <span>候选版本激活门禁</span>
                <strong :class="quality.candidate_activation?.passed ? 'text-emerald-700' : 'text-slate-500'">
                  {{ quality.candidate_activation?.available ? (quality.candidate_activation?.passed ? '通过' : '未通过') : '无记录' }}
                </strong>
              </div>
              <div class="flex justify-between">
                <span>自动质量门禁（完整发布）</span>
                <strong :class="quality.quality_gate?.passed ? 'text-emerald-700' : 'text-rose-700'">
                  {{ quality.quality_gate?.passed ? '通过' : '未通过' }}
                </strong>
              </div>
              <div v-if="quality.quality_gate?.failed_checks?.length" class="rounded bg-rose-50 px-2 py-1 text-xs text-rose-700">
                {{ quality.quality_gate.failed_checks.join('、') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="grid gap-4">
      <div class="panel p-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h2 class="panel-title">模型供应商</h2>
          <button
            class="btn shrink-0"
            data-testid="provider-probe-button"
            :disabled="probingProviders"
            title="发起一次最小 Embedding 与聊天调用"
            @click="runProviderProbe"
          >
            {{ probingProviders ? '检测中' : '检测' }}
          </button>
        </div>
        <div v-if="providerProbeError" class="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
          {{ providerProbeError }}
        </div>
        <div v-else-if="providerProbe" class="divide-y divide-slate-200 border-y border-slate-200">
          <div v-for="item in providerProbe.providers" :key="`${item.provider}:${item.capability}`" class="py-3">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="text-sm font-medium text-slate-900">{{ providerName(item.provider, item.capability) }}</div>
                <div class="mt-1 break-all text-xs text-slate-500">{{ item.model }}</div>
              </div>
              <span class="shrink-0 text-xs font-semibold" :class="providerStatusClass(item.status)">
                {{ providerStatusLabel(item.status) }}
              </span>
            </div>
            <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
              <span>{{ item.latency_ms }} ms</span>
              <span v-if="item.http_status">HTTP {{ item.http_status }}</span>
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-slate-500">尚未检测</p>
      </div>
      <div class="panel p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="panel-title">Ready Checks</h2>
          <span :class="ready?.ready ? 'text-emerald-700' : 'text-rose-700'" class="text-xs font-semibold">
            {{ ready?.status || 'unknown' }}
          </span>
        </div>
        <div v-if="ready?.reasons?.length" class="mb-3 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {{ ready.reasons.join('、') }}
        </div>
        <KeyValueList :data="ready?.checks || {}" />
      </div>
      <div class="panel p-4">
        <h2 class="panel-title mb-3">Metrics</h2>
        <KeyValueList :data="metrics || {}" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { probeModelProviders } from '../admin-api'
import { errorMessage } from '../api'
import type {
  KnowledgeDocumentsView,
  ProviderProbesResponse,
  QualityStatusView,
  ReadinessResponse,
} from '../contracts'
import MetricCard from './shared/MetricCard.vue'
import KeyValueList from './shared/KeyValueList.vue'

const props = defineProps<{
  ready: ReadinessResponse | null
  documents: KnowledgeDocumentsView
  metrics: Record<string, unknown>
  quality: QualityStatusView
}>()
const correctionCount = computed(() => props.documents?.correction_status?.applied_count || 0)
const probingProviders = ref(false)
const providerProbe = ref<ProviderProbesResponse | null>(null)
const providerProbeError = ref('')

const providerStatusLabels: Record<string, string> = {
  ok: '可用',
  not_configured: '未配置',
  auth_failed: '鉴权失败',
  rate_limited: '已限流',
  timeout: '超时',
  unavailable: '不可用',
  request_failed: '请求失败',
  invalid_response: '响应无效',
}

async function runProviderProbe() {
  if (probingProviders.value) return
  probingProviders.value = true
  providerProbeError.value = ''
  try {
    providerProbe.value = await probeModelProviders()
  } catch (error) {
    providerProbe.value = null
    providerProbeError.value = errorMessage(error)
  } finally {
    probingProviders.value = false
  }
}

function providerName(provider: string, capability: string) {
  if (provider === 'zhipuai' && capability === 'embedding') return '智谱 Embedding'
  if (provider === 'mimo' && capability === 'chat') return 'MiMo 聊天'
  return `${provider} ${capability}`
}

function providerStatusLabel(status: string) {
  return providerStatusLabels[status] || status
}

function providerStatusClass(status: string) {
  if (status === 'ok') return 'text-emerald-700'
  if (['rate_limited', 'timeout'].includes(status)) return 'text-amber-700'
  if (status === 'not_configured') return 'text-slate-500'
  return 'text-rose-700'
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '-'
}
</script>
