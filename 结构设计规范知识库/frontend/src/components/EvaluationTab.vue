<template>
  <div class="grid h-full min-h-[680px] grid-cols-[360px_minmax(0,1fr)] gap-5">
    <section class="panel p-5">
      <h2 class="panel-title">评估集</h2>
      <div class="mt-4 grid grid-cols-2 gap-3">
        <MetricCard label="Case 数" :value="evaluation.case_count || 0" />
        <MetricCard label="失败项" :value="failureCount" />
        <MetricCard label="结构化专项" :value="evaluation.structured_case_count || 0" />
        <MetricCard label="结构化命中率" :value="percent(structuredLatest?.structured_table_hit_rate)" />
        <MetricCard label="回答盲测" :value="evaluation.answer_case_count || 0" />
        <MetricCard label="回答通过率" :value="percent(answerLatest?.pass_rate)" />
      </div>
      <div v-if="latest" class="mt-4 rounded-md border p-3" :class="latest.ok ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'">
        <div class="text-sm font-semibold" :class="latest.ok ? 'text-emerald-700' : 'text-red-700'">
          {{ latest.ok ? '评估通过' : '评估未通过' }}
        </div>
        <p class="mt-1 text-xs text-slate-600">最近一次评估共 {{ latest.case_count || 0 }} 个用例。</p>
      </div>
      <div class="mt-5">
        <h3 class="mb-2 text-sm font-semibold">类型分布</h3>
        <KeyValueList :data="evaluation.by_type || {}" />
      </div>
      <div class="mt-5 grid grid-cols-3 gap-2">
        <button class="btn" :disabled="busy" @click="runEvaluation">常规评估</button>
        <button class="btn btn-primary" :disabled="busy" @click="runStructuredEvaluation">结构化专项</button>
        <button class="btn" :disabled="busy" @click="runAnswerEvaluation">回答盲测</button>
      </div>
      <p v-if="message" class="mt-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{{ message }}</p>
      <p v-if="error" class="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    </section>

    <section class="panel overflow-hidden">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">最近评估结果</h2>
        <p class="muted mt-1">用于检查检索、引用和答案质量是否退化。</p>
      </div>
      <div v-if="latest" class="space-y-5 overflow-auto p-4">
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-md border border-slate-200 bg-white p-4">
            <div class="text-xs text-slate-500">规范来源命中率</div>
            <div class="mt-2 text-2xl font-semibold">{{ percent(latest.source_hit_rate) }}</div>
          </div>
          <div class="rounded-md border border-slate-200 bg-white p-4">
            <div class="text-xs text-slate-500">条文号命中率</div>
            <div class="mt-2 text-2xl font-semibold" :class="rateClass(latest.clause_hit_rate)">{{ percent(latest.clause_hit_rate) }}</div>
          </div>
          <div class="rounded-md border border-slate-200 bg-white p-4">
            <div class="text-xs text-slate-500">关键词命中率</div>
            <div class="mt-2 text-2xl font-semibold" :class="rateClass(latest.keyword_hit_rate)">{{ percent(latest.keyword_hit_rate) }}</div>
          </div>
        </div>

        <section>
          <div class="mb-2 flex items-center justify-between">
            <h3 class="text-sm font-semibold">失败用例</h3>
            <span class="text-xs text-slate-500">{{ failureCount }} / {{ latest.case_count || 0 }}</span>
          </div>
          <div v-if="failures.length" class="space-y-3">
            <article v-for="item in failures" :key="item.id" class="rounded-md border border-slate-200 bg-white p-4">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold">{{ item.id }}</span>
                <span v-if="!item.source_hit" class="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">来源未命中</span>
                <span v-if="!item.clause_hit" class="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">条文未命中</span>
                <span v-if="!item.keyword_hit" class="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">关键词未命中</span>
              </div>
              <p class="mt-2 text-sm text-slate-700">{{ item.query }}</p>
              <div class="mt-3 overflow-auto rounded-md bg-slate-50">
                <table class="w-full text-left text-xs">
                  <thead class="text-slate-500">
                    <tr>
                      <th class="px-3 py-2">来源</th>
                      <th class="px-3 py-2">条文</th>
                      <th class="px-3 py-2">原因</th>
                      <th class="px-3 py-2">分数</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(result, index) in item.top_results || []" :key="index" class="border-t border-slate-200">
                      <td class="px-3 py-2">{{ result.source_file || '-' }}</td>
                      <td class="px-3 py-2">{{ result.clause_number || '-' }}</td>
                      <td class="px-3 py-2">{{ result.reason || '-' }}</td>
                      <td class="px-3 py-2">{{ number(result.score) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>
          </div>
          <div v-else class="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">没有失败用例。</div>
        </section>

        <section v-if="answerLatest" class="border-t border-slate-200 pt-5">
          <div class="mb-3 flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold">回答级盲测</h3>
              <p class="muted mt-1">独立检查事实、拒答、依据归属和截图可访问性。</p>
            </div>
            <strong :class="rateClass(answerLatest.pass_rate)">{{ percent(answerLatest.pass_rate) }}</strong>
          </div>
          <div class="grid grid-cols-4 gap-3">
            <MetricCard label="事实与格式" :value="`${answerLatest.passed_count || 0}/${answerLatest.case_count || 0}`" />
            <MetricCard label="依据归属" :value="percent(answerLatest.check_rates?.citation_grounded)" />
            <MetricCard label="截图可访问" :value="percent(answerLatest.check_rates?.image_http)" />
            <MetricCard label="拒答正确" :value="percent(answerLatest.refusal_pass_rate)" />
          </div>
          <div v-if="answerFailures.length" class="mt-4 space-y-3">
            <article v-for="item in answerFailures" :key="item.id" class="rounded-md border border-rose-200 bg-rose-50 p-4">
              <div class="flex items-center justify-between gap-3">
                <span class="font-semibold">{{ item.id }}</span>
                <span class="text-xs text-rose-700">{{ (item.failed_checks || []).join('、') }}</span>
              </div>
              <p class="mt-2 text-sm text-slate-700">{{ item.query }}</p>
              <details class="mt-3">
                <summary class="cursor-pointer text-xs font-medium text-slate-600">查看回答原文</summary>
                <pre class="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-white p-3 text-xs leading-5">{{ item.answer || item.error }}</pre>
              </details>
            </article>
          </div>
          <div v-else class="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            回答级盲测没有失败用例。
          </div>
        </section>

        <details class="rounded-md border border-slate-200 bg-white p-4">
          <summary class="cursor-pointer text-sm font-semibold">查看原始 JSON</summary>
          <pre class="mt-3 max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-5 text-slate-100">{{ formattedLatest }}</pre>
        </details>
      </div>
      <div v-else class="overflow-auto p-4">
        <div class="py-20 text-center text-slate-500">暂无评估报告。</div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { apiPost } from '../api'
import KeyValueList from './shared/KeyValueList.vue'
import MetricCard from './shared/MetricCard.vue'

const props = defineProps<{ evaluation: any, jobs: any[] }>()
const emit = defineEmits<{ refresh: [] }>()

const busy = ref(false)
const error = ref('')
const message = ref('')
const latest = computed(() => props.evaluation?.latest || null)
const structuredLatest = computed(() => props.evaluation?.structured_latest || null)
const answerLatest = computed(() => props.evaluation?.answer_latest || null)
const failures = computed(() => latest.value?.failures || [])
const answerFailures = computed(() => answerLatest.value?.failures || [])
const failureCount = computed(() => failures.value.length)
const formattedLatest = computed(() => JSON.stringify(props.evaluation.latest, null, 2))

function percent(value: number) {
  if (typeof value !== 'number') return '-'
  return `${Math.round(value * 100)}%`
}

function number(value: number) {
  if (typeof value !== 'number') return '-'
  return value.toFixed(3)
}

function rateClass(value: number) {
  if (typeof value !== 'number') return ''
  if (value >= 0.95) return 'text-emerald-700'
  if (value >= 0.85) return 'text-amber-700'
  return 'text-red-700'
}

async function runEvaluation() {
  busy.value = true
  error.value = ''
  try {
    const job = await apiPost('/admin/jobs/evaluate', {
      top_k: 5,
      evaluation_set: 'regular',
    })
    message.value = `已提交评估任务 ${job.job_id}`
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function runStructuredEvaluation() {
  busy.value = true
  error.value = ''
  try {
    const job = await apiPost('/admin/jobs/evaluate', {
      top_k: 5,
      evaluation_set: 'structured',
    })
    message.value = `已提交结构化专项评估 ${job.job_id}`
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function runAnswerEvaluation() {
  busy.value = true
  error.value = ''
  try {
    const job = await apiPost('/admin/jobs/evaluate-answers', {
      evaluation_set: 'answer',
    })
    message.value = `已提交回答级盲测 ${job.job_id}`
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}
</script>
