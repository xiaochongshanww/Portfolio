<template>
  <section class="panel overflow-hidden">
    <div class="border-b border-slate-200 p-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 class="panel-title">评估集浏览</h2>
          <p class="muted mt-1">查看评估用例、检索期望和回答断言，便于人工审阅评估集质量。</p>
        </div>
        <span class="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">{{ total }} 个用例</span>
      </div>
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <label class="flex items-center gap-2 text-sm text-slate-600">
          <span>评估集</span>
          <select v-model="evaluationSet" class="field min-w-36">
            <option value="regular">常规检索</option>
            <option value="structured">结构化专项</option>
            <option value="answer">回答盲测</option>
          </select>
        </label>
        <input
          v-model="search"
          class="field min-w-64 flex-1"
          placeholder="搜索问题、规范、条文号或关键词"
          @keyup.enter="applyFilters"
        >
        <select v-model="caseType" class="field min-w-36" aria-label="按用例类型筛选">
          <option value="">全部类型</option>
          <option v-for="(count, type) in typeCounts" :key="type" :value="type">{{ type }}（{{ count }}）</option>
        </select>
        <button class="btn" :disabled="loading" @click="applyFilters">{{ loading ? '加载中…' : '查询' }}</button>
      </div>
      <p v-if="error" class="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    </div>

    <div class="grid min-h-[560px] grid-cols-1 lg:grid-cols-[minmax(360px,0.95fr)_minmax(0,1.35fr)]">
      <div class="border-b border-slate-200 lg:border-b-0 lg:border-r">
        <div v-if="loading" class="p-6 text-sm text-slate-500">正在读取评估集…</div>
        <div v-else-if="!cases.length" class="p-6 text-sm text-slate-500">没有匹配的评估用例。</div>
        <div v-else class="max-h-[620px] overflow-auto p-3">
          <button
            v-for="item in cases"
            :key="item.id"
            class="mb-2 block w-full rounded-md border p-3 text-left transition last:mb-0"
            :class="selectedCase?.id === item.id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-200' : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50'"
            @click="selectedCase = item"
          >
            <div class="flex items-start justify-between gap-3">
              <span class="break-all text-sm font-semibold text-slate-900">{{ item.id }}</span>
              <span class="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{{ item.type }}</span>
            </div>
            <p class="mt-2 line-clamp-3 text-sm leading-6 text-slate-700">{{ item.query }}</p>
            <p class="mt-2 truncate text-xs text-slate-500">{{ caseSummary(item) }}</p>
          </button>
        </div>
        <div v-if="pageCount > 1" class="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
          <button class="btn h-8 px-2" :disabled="page <= 1 || loading" @click="changePage(page - 1)">上一页</button>
          <span>第 {{ page }} / {{ pageCount }} 页</span>
          <button class="btn h-8 px-2" :disabled="page >= pageCount || loading" @click="changePage(page + 1)">下一页</button>
        </div>
      </div>

      <article v-if="selectedCase" class="min-w-0 overflow-auto p-5">
        <div class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="break-all text-base font-semibold text-slate-950">{{ selectedCase.id }}</h3>
              <span class="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">{{ selectedCase.type }}</span>
            </div>
            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{{ selectedCase.query }}</p>
          </div>
        </div>

        <div v-if="evaluationSet !== 'answer'" class="mt-5 space-y-5">
          <DetailSection title="期望来源">
            <TagList :items="selectedCase.expected_sources" empty="未设置来源约束" />
          </DetailSection>
          <DetailSection title="条文与结构约束">
            <dl class="grid gap-3 text-sm sm:grid-cols-2">
              <div><dt class="text-xs text-slate-500">期望条文</dt><dd class="mt-1 break-all text-slate-900">{{ selectedCase.expected_clause || '未设置' }}</dd></div>
              <div><dt class="text-xs text-slate-500">权威类型</dt><dd class="mt-1 break-all text-slate-900">{{ selectedCase.expected_authority_type || '未设置' }}</dd></div>
              <div><dt class="text-xs text-slate-500">表格编号</dt><dd class="mt-1 break-all text-slate-900">{{ selectedCase.expected_table_id || '未设置' }}</dd></div>
              <div><dt class="text-xs text-slate-500">首条来源要求</dt><dd class="mt-1 text-slate-900">{{ selectedCase.top1_source_required ? '是' : '否' }}</dd></div>
            </dl>
          </DetailSection>
          <DetailSection title="关键词约束">
            <TagList :items="selectedCase.expected_keywords" empty="未设置关键词约束" />
            <p class="mt-2 text-xs text-slate-500">关键词必须命中：{{ selectedCase.keyword_required ? '是' : '否' }}</p>
          </DetailSection>
        </div>

        <div v-else class="mt-5 space-y-5">
          <DetailSection title="必须出现">
            <TagList :items="selectedCase.expected_all" empty="未设置必现断言" />
          </DetailSection>
          <DetailSection title="任选一组出现">
            <GroupList :groups="selectedCase.expected_any_groups" empty="未设置任选断言" />
          </DetailSection>
          <DetailSection title="引用与单位">
            <div class="space-y-4 text-sm">
              <div><div class="mb-2 text-xs text-slate-500">期望引用</div><TagList :items="selectedCase.expected_citations" empty="未设置引用断言" /></div>
              <div><div class="mb-2 text-xs text-slate-500">期望单位</div><GroupList :groups="selectedCase.expected_unit_groups" empty="未设置单位断言" /></div>
            </div>
          </DetailSection>
          <DetailSection title="禁止与行为要求">
            <div class="space-y-3 text-sm">
              <div><div class="mb-2 text-xs text-slate-500">禁止出现</div><TagList :items="selectedCase.forbidden_terms" empty="未设置禁止词" /></div>
              <div class="grid gap-2 sm:grid-cols-2">
                <div class="rounded-md bg-slate-50 px-3 py-2">必须正确拒答：<strong>{{ selectedCase.requires_refusal ? '是' : '否' }}</strong></div>
                <div class="rounded-md bg-slate-50 px-3 py-2">必须包含截图：<strong>{{ selectedCase.requires_image ? '是' : '否' }}</strong></div>
              </div>
            </div>
          </DetailSection>
        </div>
      </article>
      <div v-else class="flex min-h-[560px] items-center justify-center p-6 text-center text-sm text-slate-500">选择左侧用例查看完整评估条件。</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { listAdminEvaluationCases } from '../admin-api'
import { errorMessage } from '../api'
import type { EvaluationCaseView, EvaluationCasesView, EvaluationSetName } from '../contracts'

const evaluationSet = ref<EvaluationSetName>('regular')
const search = ref('')
const caseType = ref('')
const page = ref(1)
const pageSize = 50
const total = ref(0)
const typeCounts = ref<Record<string, number>>({})
const cases = ref<EvaluationCaseView[]>([])
const selectedCase = ref<EvaluationCaseView | null>(null)
const loading = ref(false)
const error = ref('')

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function loadCases() {
  loading.value = true
  error.value = ''
  try {
    const payload = await listAdminEvaluationCases({
      query: {
        evaluation_set: evaluationSet.value,
        search: search.value.trim() || undefined,
        case_type: caseType.value || undefined,
        offset: (page.value - 1) * pageSize,
        limit: pageSize,
      },
    }) as EvaluationCasesView
    total.value = payload.total
    typeCounts.value = payload.type_counts
    cases.value = payload.cases
    selectedCase.value = payload.cases[0] || null
  } catch (err: unknown) {
    cases.value = []
    selectedCase.value = null
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  void loadCases()
}

function changePage(nextPage: number) {
  page.value = nextPage
  void loadCases()
}

function caseSummary(item: EvaluationCaseView) {
  if (evaluationSet.value === 'answer') {
    return item.expected_citations.length ? `引用：${item.expected_citations.join('、')}` : '回答断言'
  }
  return item.expected_table_id || item.expected_clause || item.expected_sources.join('、') || '检索约束'
}

watch(evaluationSet, () => {
  search.value = ''
  caseType.value = ''
  page.value = 1
  void loadCases()
})
watch(caseType, () => {
  page.value = 1
  void loadCases()
})
onMounted(() => void loadCases())
</script>

<script lang="ts">
import { defineComponent, h, type PropType } from 'vue'

export default defineComponent({
  components: {
    DetailSection: defineComponent({
      props: { title: { type: String, required: true } },
      setup(props, { slots }) {
        return () => h('section', { class: 'border-t border-slate-100 pt-4 first:border-0 first:pt-0' }, [
          h('h4', { class: 'mb-2 text-sm font-semibold text-slate-900' }, props.title),
          slots.default?.(),
        ])
      },
    }),
    TagList: defineComponent({
      props: { items: { type: Array as PropType<string[]>, required: true }, empty: { type: String, required: true } },
      setup(props) {
        return () => props.items.length
          ? h('div', { class: 'flex flex-wrap gap-2' }, props.items.map(item => h('span', { class: 'max-w-full break-all rounded bg-slate-100 px-2 py-1 text-xs text-slate-700' }, String(item))))
          : h('span', { class: 'text-sm text-slate-400' }, props.empty)
      },
    }),
    GroupList: defineComponent({
      props: { groups: { type: Array as PropType<string[][]>, required: true }, empty: { type: String, required: true } },
      setup(props) {
        return () => props.groups.length
          ? h('ol', { class: 'space-y-2 text-sm text-slate-700' }, props.groups.map((group, index) => h('li', { class: 'rounded-md bg-slate-50 px-3 py-2' }, `${index + 1}. ${group.join('、')}`)))
          : h('span', { class: 'text-sm text-slate-400' }, props.empty)
      },
    }),
  },
})
</script>
