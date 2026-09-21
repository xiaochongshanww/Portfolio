<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
      <div class="inline-flex rounded-md border border-slate-200 bg-slate-50 p-1" role="tablist" aria-label="用例编辑模式">
        <button
          class="rounded px-3 py-1.5 text-sm"
          :class="!advancedMode ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600'"
          type="button"
          role="tab"
          :aria-selected="!advancedMode"
          @click="switchMode(false)"
        >
          表单编辑
        </button>
        <button
          class="rounded px-3 py-1.5 text-sm"
          :class="advancedMode ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600'"
          type="button"
          role="tab"
          :aria-selected="advancedMode"
          @click="switchMode(true)"
        >
          高级 JSON
        </button>
      </div>
      <span class="status-pill status-pill-gray">{{ setTypeLabel }}</span>
    </div>

    <template v-if="!advancedMode">
      <section class="space-y-4" aria-labelledby="case-basic-fields">
        <h3 id="case-basic-fields" class="text-sm font-semibold text-slate-900">基本信息</h3>
        <div class="grid gap-4 md:grid-cols-2">
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">用例 ID</span>
            <input v-model="form.id" class="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly" autocomplete="off" />
          </label>
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">评估类型</span>
            <select v-model="form.type" class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly">
              <option v-for="option in typeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
        </div>
        <label class="block text-sm text-slate-700">
          <span class="mb-1.5 block font-medium">问题</span>
          <textarea v-model="form.query" class="min-h-24 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
        </label>
      </section>

      <section v-if="evaluationSetId !== 'answer'" class="space-y-4 border-t border-slate-200 pt-5" aria-labelledby="retrieval-expectations">
        <h3 id="retrieval-expectations" class="text-sm font-semibold text-slate-900">检索期望</h3>
        <div class="grid gap-4 md:grid-cols-2">
          <label v-if="evaluationSetId === 'regular'" class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">期望规范来源（每行一项）</span>
            <textarea v-model="form.expectedSources" class="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
          <label v-if="evaluationSetId === 'regular'" class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">期望关键词（每行一项）</span>
            <textarea v-model="form.expectedKeywords" class="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
          <label v-if="evaluationSetId === 'regular'" class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">期望条文号</span>
            <input v-model="form.expectedClause" class="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly" autocomplete="off" />
          </label>
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">期望表格编号</span>
            <input v-model="form.expectedTableId" class="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly" autocomplete="off" />
          </label>
          <label v-if="evaluationSetId === 'regular'" class="block text-sm text-slate-700 md:col-span-2">
            <span class="mb-1.5 block font-medium">期望权威类型</span>
            <input v-model="form.expectedAuthorityType" class="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly" autocomplete="off" />
          </label>
        </div>
        <div class="flex flex-wrap gap-x-8 gap-y-3">
          <label class="inline-flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.top1SourceRequired" type="checkbox" :disabled="readOnly" />
            首位结果必须命中期望来源
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.keywordRequired" type="checkbox" :disabled="readOnly" />
            必须命中关键词约束
          </label>
        </div>
      </section>

      <section v-else class="space-y-4 border-t border-slate-200 pt-5" aria-labelledby="answer-expectations">
        <h3 id="answer-expectations" class="text-sm font-semibold text-slate-900">回答期望</h3>
        <div class="grid gap-4 md:grid-cols-2">
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">必须包含（每行一项）</span>
            <textarea v-model="form.expectedAll" class="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">必须引用（每行一项）</span>
            <textarea v-model="form.expectedCitations" class="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">任选命中组（每行一组，选项用 | 分隔）</span>
            <textarea v-model="form.expectedAnyGroups" class="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
          <label class="block text-sm text-slate-700">
            <span class="mb-1.5 block font-medium">允许单位组（每行一组，选项用 | 分隔）</span>
            <textarea v-model="form.expectedUnitGroups" class="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
          <label class="block text-sm text-slate-700 md:col-span-2">
            <span class="mb-1.5 block font-medium">禁止出现（每行一项）</span>
            <textarea v-model="form.forbiddenTerms" class="min-h-24 w-full rounded-md border border-slate-300 px-3 py-2 leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" :disabled="readOnly"></textarea>
          </label>
        </div>
        <div class="flex flex-wrap gap-x-8 gap-y-3">
          <label class="inline-flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.requiresImage" type="checkbox" :disabled="readOnly" />
            要求提供引用截图
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.requiresRefusal" type="checkbox" :disabled="readOnly" />
            要求拒答
          </label>
        </div>
      </section>
    </template>

    <div v-else>
      <label class="block text-sm text-slate-700">
        <span class="mb-1.5 block font-medium">完整用例 JSON</span>
        <textarea
          v-model="jsonText"
          class="min-h-[520px] w-full rounded-md border border-slate-300 bg-slate-950 p-4 font-mono text-xs leading-5 text-slate-100 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          :disabled="readOnly"
          spellcheck="false"
          aria-label="评估用例 JSON"
        ></textarea>
      </label>
    </div>

    <p v-if="localError" class="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{{ localError }}</p>

    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
      <button v-if="mode === 'edit' && !readOnly" class="btn btn-danger" type="button" @click="emit('delete')">删除用例</button>
      <span v-else></span>
      <div class="flex gap-2">
        <button class="btn" type="button" @click="emit('cancel')">返回列表</button>
        <button v-if="!readOnly" class="btn btn-primary" type="button" @click="submit">{{ mode === 'create' ? '新增用例' : '保存用例' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import type { EvaluationSetName } from '../contracts'

type JsonCase = Record<string, unknown>
type EditorMode = 'edit' | 'create'

const props = defineProps<{
  modelValue: JsonCase
  evaluationSetId: EvaluationSetName
  mode: EditorMode
  readOnly?: boolean
}>()

const emit = defineEmits<{
  save: [value: JsonCase]
  cancel: []
  delete: []
}>()

type CaseForm = {
  id: string
  query: string
  type: string
  expectedSources: string
  expectedClause: string
  expectedKeywords: string
  expectedAuthorityType: string
  expectedTableId: string
  top1SourceRequired: boolean
  keywordRequired: boolean
  expectedAll: string
  expectedAnyGroups: string
  forbiddenTerms: string
  expectedCitations: string
  expectedUnitGroups: string
  requiresRefusal: boolean
  requiresImage: boolean
}

const advancedMode = ref(false)
const jsonText = ref('')
const localError = ref('')
const baseCase = ref<JsonCase>({})
const form = reactive<CaseForm>(emptyForm())

const typeOptions = computed(() => {
  if (props.evaluationSetId === 'answer') {
    return [
      { value: 'direct_value', label: '直接数值' },
      { value: 'formula', label: '公式' },
      { value: 'boundary', label: '适用边界' },
      { value: 'false_premise', label: '错误前提' },
      { value: 'no_evidence', label: '无依据拒答' },
    ]
  }
  if (props.evaluationSetId === 'structured') return [{ value: 'structured_table', label: '复杂表格' }]
  return [
    { value: 'clause', label: '条文查询' },
    { value: 'table', label: '表格取值' },
    { value: 'definition', label: '定义' },
    { value: 'classification', label: '分类' },
    { value: 'general', label: '一般检索' },
    { value: 'alias', label: '别名' },
    { value: 'code', label: '规范编号' },
    { value: 'multi_spec', label: '多规范' },
    { value: 'formula', label: '公式' },
  ]
})

const setTypeLabel = computed(() => ({ regular: '常规检索', structured: '复杂表专项', answer: '回答盲测' })[props.evaluationSetId])

function emptyForm(): CaseForm {
  return {
    id: '',
    query: '',
    type: '',
    expectedSources: '',
    expectedClause: '',
    expectedKeywords: '',
    expectedAuthorityType: '',
    expectedTableId: '',
    top1SourceRequired: true,
    keywordRequired: true,
    expectedAll: '',
    expectedAnyGroups: '',
    forbiddenTerms: '',
    expectedCitations: '',
    expectedUnitGroups: '',
    requiresRefusal: false,
    requiresImage: true,
  }
}

function stringList(value: unknown) {
  return Array.isArray(value) ? value.map(item => String(item)).join('\n') : ''
}

function groupList(value: unknown) {
  return Array.isArray(value)
    ? value.map(group => Array.isArray(group) ? group.map(item => String(item)).join(' | ') : String(group)).join('\n')
    : ''
}

function parseList(value: string) {
  return value.split(/\r?\n/).map(item => item.trim()).filter(Boolean)
}

function parseGroups(value: string) {
  return parseList(value).map(line => line.split('|').map(item => item.trim()).filter(Boolean)).filter(group => group.length)
}

function applyCase(value: JsonCase) {
  baseCase.value = { ...value }
  Object.assign(form, emptyForm(), {
    id: String(value.id || ''),
    query: String(value.query || ''),
    type: String(value.type || typeOptions.value[0]?.value || ''),
    expectedSources: stringList(value.expected_sources),
    expectedClause: String(value.expected_clause || ''),
    expectedKeywords: stringList(value.expected_keywords),
    expectedAuthorityType: String(value.expected_authority_type || ''),
    expectedTableId: String(value.expected_table_id || ''),
    top1SourceRequired: value.top1_source_required === undefined ? true : Boolean(value.top1_source_required),
    keywordRequired: value.keyword_required === undefined ? true : Boolean(value.keyword_required),
    expectedAll: stringList(value.expected_all),
    expectedAnyGroups: groupList(value.expected_any_groups),
    forbiddenTerms: stringList(value.forbidden_terms),
    expectedCitations: stringList(value.expected_citations),
    expectedUnitGroups: groupList(value.expected_unit_groups),
    requiresRefusal: Boolean(value.requires_refusal),
    requiresImage: value.requires_image === undefined ? true : Boolean(value.requires_image),
  })
  jsonText.value = JSON.stringify(value, null, 2)
  localError.value = ''
}

function setOptionalString(target: JsonCase, key: string, value: string) {
  const normalized = value.trim()
  if (normalized) target[key] = normalized
  else delete target[key]
}

function buildCase(): JsonCase {
  const result: JsonCase = { ...baseCase.value, id: form.id.trim(), query: form.query.trim(), type: form.type }
  if (props.evaluationSetId === 'answer') {
    result.expected_all = parseList(form.expectedAll)
    result.expected_any_groups = parseGroups(form.expectedAnyGroups)
    result.forbidden_terms = parseList(form.forbiddenTerms)
    result.expected_citations = parseList(form.expectedCitations)
    result.expected_unit_groups = parseGroups(form.expectedUnitGroups)
    result.requires_refusal = form.requiresRefusal
    result.requires_image = form.requiresImage
    for (const key of ['expected_sources', 'expected_clause', 'expected_keywords', 'expected_authority_type', 'expected_table_id', 'top1_source_required', 'keyword_required']) delete result[key]
  } else {
    result.expected_sources = parseList(form.expectedSources)
    result.expected_keywords = parseList(form.expectedKeywords)
    result.top1_source_required = form.top1SourceRequired
    result.keyword_required = form.keywordRequired
    setOptionalString(result, 'expected_clause', form.expectedClause)
    setOptionalString(result, 'expected_authority_type', form.expectedAuthorityType)
    setOptionalString(result, 'expected_table_id', form.expectedTableId)
    for (const key of ['expected_all', 'expected_any_groups', 'forbidden_terms', 'expected_citations', 'expected_unit_groups', 'requires_refusal', 'requires_image']) delete result[key]
  }
  return result
}

function parseAdvancedJson(): JsonCase | null {
  try {
    const parsed = JSON.parse(jsonText.value) as JsonCase
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('用例必须是 JSON 对象。')
    return parsed
  } catch (cause) {
    localError.value = cause instanceof Error ? cause.message : 'JSON 无法解析。'
    return null
  }
}

function switchMode(nextAdvanced: boolean) {
  if (nextAdvanced === advancedMode.value) return
  localError.value = ''
  if (nextAdvanced) {
    jsonText.value = JSON.stringify(buildCase(), null, 2)
    advancedMode.value = true
    return
  }
  const parsed = parseAdvancedJson()
  if (!parsed) return
  applyCase(parsed)
  advancedMode.value = false
}

function submit() {
  localError.value = ''
  const value = advancedMode.value ? parseAdvancedJson() : buildCase()
  if (!value) return
  if (!String(value.id || '').trim()) {
    localError.value = '请填写用例 ID。'
    return
  }
  if (!String(value.query || '').trim()) {
    localError.value = '请填写问题。'
    return
  }
  if (!String(value.type || '').trim()) {
    localError.value = '请选择评估类型。'
    return
  }
  emit('save', value)
}

watch(
  () => [props.modelValue, props.evaluationSetId] as const,
  ([value]) => {
    advancedMode.value = false
    applyCase(value)
  },
  { deep: true, immediate: true },
)
</script>
