<template>
  <div class="overflow-hidden rounded-md border border-slate-200 bg-white">
    <div class="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
      <div class="flex rounded-md border border-slate-200 bg-white p-0.5">
        <button
          class="rounded px-3 py-1.5 text-xs font-medium"
          :class="mode === 'visual' ? 'bg-blue-600 text-white' : 'text-slate-600'"
          @click="mode = 'visual'"
        >
          可视化编辑
        </button>
        <button
          class="rounded px-3 py-1.5 text-xs font-medium"
          :class="mode === 'json' ? 'bg-blue-600 text-white' : 'text-slate-600'"
          @click="mode = 'json'"
        >
          JSON
        </button>
      </div>
      <span v-if="jsonError" class="text-xs font-medium text-red-600">{{ jsonError }}</span>
    </div>

    <div v-if="mode === 'json'" class="p-3">
      <textarea
        :value="modelValue"
        class="field min-h-[560px] w-full resize-y font-mono text-xs leading-5"
        @input="emit('update:modelValue', inputText($event))"
      ></textarea>
    </div>

    <div v-else-if="draft" class="space-y-5 p-4">
      <section>
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-800">来源信息</h3>
          <span class="text-xs text-slate-500">{{ draft.draft_status || 'needs_review' }}</span>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label v-for="field in sourceFields" :key="field.key" class="block">
            <span class="mb-1 block text-xs font-medium text-slate-500">{{ field.label }}</span>
            <input
              :value="sourceValue(field.key)"
              class="field h-9 w-full text-sm"
              :class="errorClass(`source.${field.key}`)"
              @input="updateSource(field.key, inputText($event))"
            />
            <span v-if="errorMessage(`source.${field.key}`)" class="mt-1 block text-xs text-red-600">
              {{ errorMessage(`source.${field.key}`) }}
            </span>
          </label>
          <label class="col-span-2 block">
            <span class="mb-1 block text-xs font-medium text-slate-500">来源页码</span>
            <input
              :value="numberList(draft.source.pages).join(', ')"
              class="field h-9 w-full text-sm"
              :class="errorClass('source.pages')"
              placeholder="例如 35, 36"
              @input="updatePages(inputText($event))"
            />
            <span v-if="errorMessage('source.pages')" class="mt-1 block text-xs text-red-600">
              {{ errorMessage('source.pages') }}
            </span>
          </label>
        </div>
      </section>

      <section>
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-800">列定义</h3>
          <button class="btn h-8 w-8 p-0 text-lg" title="新增列" aria-label="新增列" @click="addColumn">+</button>
        </div>
        <div class="space-y-2">
          <div
            v-for="(column, index) in columns"
            :key="index"
            class="grid grid-cols-[minmax(120px,1fr)_minmax(120px,1fr)_100px_110px_36px] gap-2"
          >
            <input
              :value="column.key"
              class="field h-9 text-sm"
              :class="errorClass(`columns[${index}].key`)"
              placeholder="字段 key"
              @input="updateColumnKey(index, inputText($event))"
            />
            <input
              :value="column.label"
              class="field h-9 text-sm"
              :class="errorClass(`columns[${index}].label`)"
              placeholder="显示名称"
              @input="updateColumn(index, 'label', inputText($event))"
            />
            <input
              :value="column.unit || ''"
              class="field h-9 text-sm"
              placeholder="单位"
              @input="updateColumn(index, 'unit', inputText($event))"
            />
            <select
              :value="columnType(column)"
              class="field h-9 text-sm"
              @change="updateColumn(index, 'value_type', inputText($event))"
            >
              <option value="text">文本</option>
              <option value="number">数字</option>
              <option value="list">列表</option>
              <option value="json">JSON</option>
            </select>
            <button
              class="btn btn-danger h-9 w-9 p-0 text-lg"
              title="删除列"
              aria-label="删除列"
              @click="removeColumn(index)"
            >
              ×
            </button>
          </div>
          <p v-if="!columns.length" class="rounded bg-slate-50 p-3 text-sm text-slate-500">尚未定义列。</p>
        </div>
      </section>

      <section>
        <div class="mb-3 flex items-center justify-between">
          <div>
            <h3 class="text-sm font-semibold text-slate-800">行数据</h3>
            <p class="mt-1 text-xs text-slate-500">{{ rows.length }} 行</p>
          </div>
          <button class="btn h-8 w-8 p-0 text-lg" title="新增行" aria-label="新增行" @click="addRow">+</button>
        </div>
        <div
          class="overflow-auto rounded-md border border-slate-200"
          :class="errorClass('rows')"
        >
          <table class="draft-grid">
            <thead>
              <tr>
                <th class="w-12">#</th>
                <th v-for="column in columns" :key="column.key">
                  {{ column.label || column.key }}
                  <span v-if="column.unit" class="font-normal text-slate-400">({{ column.unit }})</span>
                </th>
                <th class="w-12"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in rows" :key="rowIndex">
                <td class="text-center text-xs text-slate-400">{{ rowIndex + 1 }}</td>
                <td
                  v-for="column in columns"
                  :key="column.key"
                  :class="errorClass(`rows[${rowIndex}]`)"
                >
                  <input
                    v-if="columnType(column) === 'number'"
                    type="number"
                    step="any"
                    :value="cellInputValue(row[column.key], 'number')"
                    class="field h-9 min-w-28 text-sm"
                    @input="updateCell(rowIndex, column, inputText($event))"
                  />
                  <textarea
                    v-else
                    :value="cellInputValue(row[column.key], columnType(column))"
                    class="field min-h-20 min-w-44 resize-y text-sm leading-5"
                    :class="columnType(column) === 'json' ? 'font-mono text-xs' : ''"
                    :placeholder="columnType(column) === 'list' ? '每行一个值' : ''"
                    @input="updateCell(rowIndex, column, inputText($event))"
                  ></textarea>
                </td>
                <td class="text-center">
                  <button
                    class="btn btn-danger h-8 w-8 p-0 text-lg"
                    title="删除行"
                    aria-label="删除行"
                    @click="removeRow(rowIndex)"
                  >
                    ×
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!rows.length" class="p-6 text-center text-sm text-slate-500">新增一行开始录入。</div>
        </div>
        <span v-if="errorMessage('rows')" class="mt-1 block text-xs text-red-600">{{ errorMessage('rows') }}</span>
      </section>

      <section class="grid grid-cols-2 gap-4">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">表格检索别名</span>
          <textarea
            :value="listInput(draft.table_aliases)"
            class="field min-h-28 w-full resize-y text-sm leading-6"
            :class="errorClass('table_aliases')"
            placeholder="每行一个别名"
            @input="updateList('table_aliases', inputText($event))"
          ></textarea>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">表注与限制条件</span>
          <textarea
            :value="listInput(draft.notes)"
            class="field min-h-28 w-full resize-y text-sm leading-6"
            :class="errorClass('notes')"
            placeholder="每行一条说明"
            @input="updateList('notes', inputText($event))"
          ></textarea>
        </label>
      </section>

      <section>
        <h3 class="mb-3 text-sm font-semibold text-slate-800">结构化结果预览</h3>
        <div class="overflow-auto rounded-md border border-slate-200">
          <table class="draft-preview">
            <thead>
              <tr>
                <th v-for="column in columns" :key="column.key">
                  {{ column.label || column.key }}
                  <span v-if="column.unit" class="font-normal text-slate-400">({{ column.unit }})</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in rows" :key="index">
                <td v-for="column in columns" :key="column.key">
                  <span
                    v-if="isLatexColumn(column) && row[column.key]"
                    v-html="renderLatex(String(row[column.key]))"
                  ></span>
                  <span v-else>{{ displayValue(row[column.key]) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!rows.length" class="p-6 text-center text-sm text-slate-500">暂无可预览数据。</div>
        </div>
      </section>
    </div>

    <div v-else class="p-6 text-sm text-red-600">
      JSON 无法解析，请切换到 JSON 模式修正。
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import type { ManualValidationResponse } from '../contracts'

type DraftColumn = Record<string, unknown> & {
  key: string
  label?: string
  unit?: string
  value_type?: string
}

type DraftModel = Record<string, unknown> & {
  draft_status: string
  source: Record<string, unknown>
  columns: DraftColumn[]
  rows: Array<Record<string, unknown>>
}

const props = defineProps<{
  modelValue: string
  validation?: ManualValidationResponse | null
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const mode = ref<'visual' | 'json'>('visual')
const sourceFields = [
  { key: 'code', label: '规范编号' },
  { key: 'name', label: '规范名称' },
  { key: 'source_file', label: '来源文件' },
  { key: 'clause_number', label: '条文号' },
  { key: 'table_id', label: '表号' },
  { key: 'table_name', label: '表名' },
]

const draft = computed<DraftModel | null>(() => {
  try {
    if (!props.modelValue.trim()) return null
    const parsed: unknown = JSON.parse(props.modelValue)
    if (!isRecord(parsed)) return null
    const rawColumns = Array.isArray(parsed.columns) ? parsed.columns.filter(isRecord) : []
    return {
      ...parsed,
      draft_status: stringValue(parsed.draft_status, 'needs_review'),
      source: isRecord(parsed.source) ? { ...parsed.source } : {},
      columns: rawColumns.map((column, index) => ({
        ...column,
        key: stringValue(column.key, `field_${index + 1}`),
        label: stringValue(column.label),
        unit: stringValue(column.unit),
        value_type: stringValue(column.value_type),
      })),
      rows: Array.isArray(parsed.rows) ? parsed.rows.filter(isRecord).map(row => ({ ...row })) : [],
    }
  } catch {
    return null
  }
})

const columns = computed<DraftColumn[]>(() => draft.value?.columns || [])
const rows = computed<Array<Record<string, unknown>>>(() => draft.value?.rows || [])

const jsonError = computed(() => {
  if (!props.modelValue.trim()) return ''
  try {
    JSON.parse(props.modelValue)
    return ''
  } catch (error: unknown) {
    return error instanceof Error ? error.message : 'JSON 无效'
  }
})

function inputText(event: Event) {
  return (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value
}

function mutateDraft(callback: (value: DraftModel) => void) {
  if (!draft.value) return
  const copy = structuredClone(draft.value)
  callback(copy)
  emit('update:modelValue', JSON.stringify(copy, null, 2))
}

function sourceValue(key: string) {
  return draft.value?.source?.[key] ?? ''
}

function updateSource(key: string, value: string) {
  mutateDraft(copy => {
    copy.source ||= {}
    copy.source[key] = value
  })
}

function updatePages(value: string) {
  mutateDraft(copy => {
    copy.source ||= {}
    copy.source.pages = value
      .split(/[,，\s]+/)
      .map(item => Number(item))
      .filter(item => Number.isInteger(item) && item > 0)
  })
}

function columnType(column: DraftColumn) {
  if (column.value_type) return column.value_type
  if (column.key === 'aliases' || column.key === 'variables') return 'list'
  const values = (draft.value?.rows || []).map(row => row[column.key]).filter(value => value != null)
  if (values.some(value => Array.isArray(value))) return 'list'
  if (values.length && values.every(value => typeof value === 'number')) return 'number'
  if (values.some(value => typeof value === 'object')) return 'json'
  return 'text'
}

function updateColumn(index: number, key: string, value: string) {
  mutateDraft(copy => {
    copy.columns[index][key] = value
    if (key === 'unit' && !value) delete copy.columns[index].unit
  })
}

function updateColumnKey(index: number, value: string) {
  mutateDraft(copy => {
    const previous = copy.columns[index].key
    copy.columns[index].key = value
    if (!previous || previous === value) return
    for (const row of copy.rows || []) {
      if (Object.prototype.hasOwnProperty.call(row, previous)) {
        row[value] = row[previous]
        delete row[previous]
      }
    }
  })
}

function addColumn() {
  mutateDraft(copy => {
    copy.columns ||= []
    const existing = new Set(copy.columns.map(column => column.key))
    let number = copy.columns.length + 1
    while (existing.has(`field_${number}`)) number += 1
    copy.columns.push({ key: `field_${number}`, label: `字段 ${number}`, value_type: 'text' })
  })
}

function removeColumn(index: number) {
  mutateDraft(copy => {
    const [removed] = copy.columns.splice(index, 1)
    for (const row of copy.rows || []) delete row[removed.key]
  })
}

function addRow() {
  mutateDraft(copy => {
    copy.rows ||= []
    const row: Record<string, unknown> = {}
    for (const column of copy.columns || []) {
      row[column.key] = columnType(column) === 'list' ? [] : null
    }
    copy.rows.push(row)
  })
}

function removeRow(index: number) {
  mutateDraft(copy => copy.rows.splice(index, 1))
}

function cellInputValue(value: unknown, type: string) {
  if (value == null) return ''
  if (type === 'list') return Array.isArray(value) ? value.join('\n') : String(value)
  if (type === 'json') return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return String(value)
}

function updateCell(rowIndex: number, column: DraftColumn, value: string) {
  mutateDraft(copy => {
    const type = columnType(column)
    if (type === 'number') {
      copy.rows[rowIndex][column.key] = value.trim() === '' ? null : Number(value)
    } else if (type === 'list') {
      copy.rows[rowIndex][column.key] = value.split('\n').map(item => item.trim()).filter(Boolean)
    } else if (type === 'json') {
      try {
        const parsed: unknown = value.trim() ? JSON.parse(value) : null
        copy.rows[rowIndex][column.key] = parsed
      } catch {
        copy.rows[rowIndex][column.key] = value
      }
    } else {
      copy.rows[rowIndex][column.key] = value
    }
  })
}

function listInput(value: unknown) {
  return Array.isArray(value) ? value.join('\n') : ''
}

function updateList(key: string, value: string) {
  mutateDraft(copy => {
    copy[key] = value.split('\n').map(item => item.trim()).filter(Boolean)
  })
}

function validationEntries() {
  return [...(props.validation?.errors || []), ...(props.validation?.warnings || [])]
}

function errorMessage(path: string) {
  return validationEntries().find(entry => entry.path === path)?.message || ''
}

function errorClass(path: string) {
  return validationEntries().some(entry => entry.path === path || entry.path.startsWith(`${path}.`))
    ? 'border-red-400 ring-1 ring-red-200'
    : ''
}

function displayValue(value: unknown) {
  if (value == null) return ''
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function isLatexColumn(column: DraftColumn) {
  return /latex|formula/i.test(column.key)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function numberList(value: unknown): number[] {
  return Array.isArray(value)
    ? value.map(item => Number(item)).filter(Number.isFinite)
    : []
}

function renderLatex(value: string) {
  const formula = value.replace(/^\$+|\$+$/g, '')
  return katex.renderToString(formula, { throwOnError: false, strict: false })
}
</script>

<style scoped>
.draft-grid,
.draft-preview {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
}

.draft-grid th,
.draft-grid td,
.draft-preview th,
.draft-preview td {
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px;
  vertical-align: top;
  text-align: left;
}

.draft-grid th,
.draft-preview th {
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.draft-preview td {
  max-width: 360px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
}
</style>
