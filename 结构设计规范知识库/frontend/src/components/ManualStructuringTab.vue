<template>
  <div class="manual-page" :class="focusEditor ? 'manual-page-focus' : ''">
    <div v-if="!focusEditor" class="manual-stat-grid">
      <section class="panel p-4">
        <div class="muted">待处理表格</div>
        <strong class="mt-2 block text-2xl text-slate-900">{{ totalPending }}</strong>
        <div class="muted mt-1">当前阻塞候选发布</div>
      </section>
      <section class="panel p-4">
        <div class="muted">已完成</div>
        <strong class="mt-2 block text-2xl text-slate-900">{{ totalApproved }}</strong>
        <div class="muted mt-1">已发布结构化表</div>
      </section>
      <section class="panel p-4">
        <div class="muted">AI 建议覆盖</div>
        <strong class="mt-2 block text-2xl text-slate-900">{{ suggestionCoverage }}</strong>
        <div class="muted mt-1">仍需人工确认</div>
      </section>
      <section class="panel p-4">
        <div class="muted">当前数据版本</div>
        <strong class="mt-2 block truncate font-mono text-xl text-slate-900" :title="activeDataVersion">{{ activeDataVersionLabel }}</strong>
        <div class="muted mt-1">结构化修改不会即时上线</div>
      </section>
    </div>

    <div class="manual-workspace" :class="focusEditor ? 'manual-workspace-focus' : ''">
    <section v-if="!focusEditor" class="panel flex min-h-0 flex-col overflow-hidden">
      <div class="border-b border-slate-200 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="panel-title">复杂表队列</h2>
            <p class="muted mt-1">按规范筛选待处理和已完成项</p>
          </div>
          <span class="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">{{ totalPending }} 待处理</span>
        </div>
        <p class="muted mt-2">共 {{ totalTaskCount }} 个复杂表任务</p>
      </div>
      <div class="border-b border-slate-200 p-3">
        <label for="manual-doc-filter" class="mb-1 block text-xs font-semibold text-slate-500">来源规范</label>
        <select id="manual-doc-filter" v-model="selectedDoc" class="field w-full" :disabled="!documents.length" @change="selectDoc(selectedDoc)">
          <option v-for="doc in documents" :key="doc.doc" :value="doc.doc">{{ doc.doc }}</option>
        </select>
        <label for="manual-status-filter" class="sr-only">结构化状态</label>
        <select id="manual-status-filter" v-model="statusFilter" class="field mt-2 w-full">
          <option value="pending">待处理</option>
          <option value="approved">已结构化</option>
          <option value="rejected">暂不处理</option>
          <option value="">全部</option>
        </select>
        <button class="btn btn-primary mt-2 w-full" type="button" :disabled="busy" @click="startBatchSuggestions">批量 AI 建议</button>
      </div>
      <div class="manual-task-list min-h-0 flex-1 overflow-auto p-3" aria-live="polite">
        <button
          v-for="item in filteredItems"
          :key="item.id"
          class="mb-2 w-full rounded-md border border-slate-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
          :class="selectedItem?.id === item.id ? 'border-blue-500 bg-blue-50' : 'bg-white'"
          type="button"
          @click="openItem(item)"
        >
          <div class="flex items-start justify-between gap-2 text-sm font-semibold">
            <span class="min-w-0 break-words">{{ displayItemTitle(item) }}</span>
            <span :class="riskClass(item.severity)">{{ severityLabel(item.severity) }}</span>
          </div>
          <div class="mt-1 text-xs text-slate-500">
            {{ item.group_size > 1 ? `第 ${(item.group_pages || []).join('、')} 页` : `第 ${item.page} 页` }}
            · 元素 {{ item.element_index }} · {{ issueTypeLabel(item.issue_type) }} · {{ statusLabel(item.status) }}
          </div>
        </button>
        <p v-if="!documents.length" class="p-4 text-sm text-slate-500">暂无复杂表队列。</p>
        <p v-else-if="!filteredItems.length" class="p-4 text-sm leading-6 text-slate-500">当前筛选下暂无任务，请切换规范或状态。</p>
      </div>
    </section>

    <section v-if="!focusEditor" class="panel flex min-h-0 flex-col overflow-hidden">
      <div class="flex items-center justify-between border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">原 PDF 页面</h2>
          <p class="muted mt-1">{{ previewItem ? `page ${previewItem.page} · element ${previewItem.element_index}` : '选择任务后显示页面截图' }}</p>
        </div>
        <button class="btn" type="button" :disabled="!selectedDoc" @click="loadDocQueue">刷新队列</button>
      </div>
      <div v-if="groupMembers.length > 1" class="flex gap-2 overflow-x-auto border-b border-slate-200 px-4 py-2">
        <button
          v-for="member in groupMembers"
          :key="member.id"
          class="btn h-8 shrink-0 px-3 text-xs"
          :class="previewItem?.id === member.id ? 'border-blue-500 bg-blue-50 text-blue-700' : ''"
          type="button"
          @click="previewMember(member)"
        >
          第 {{ member.page }} 页
        </button>
      </div>
      <div class="min-h-0 flex-1 overflow-auto bg-slate-200 p-5">
        <div v-if="pageImageStatus === 'loading' && !pageImageUrl" class="flex h-full items-center justify-center text-sm text-slate-500" aria-live="polite">
          正在加载页面截图...
        </div>
        <div v-else-if="pageImageStatus === 'error'" class="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-slate-600" role="alert">
          <div class="font-semibold text-slate-700">原始 PDF 页面暂时无法显示</div>
          <div class="max-w-md leading-6">{{ pageImageError }}</div>
          <button class="btn h-8 px-3 text-xs" type="button" @click="retryPageImage">重新加载</button>
        </div>
        <img
          v-else-if="pageImageUrl"
          :src="pageImageUrl"
          :alt="`${selectedDoc || '原 PDF'} 第 ${previewItem?.page || ''} 页`"
          class="mx-auto max-w-full rounded-sm bg-white shadow"
          @error="handlePageImageError"
          @load="pageImageStatus = 'ready'"
        />
        <div v-else class="flex h-full items-center justify-center text-sm text-slate-500">从左侧队列中选择一项开始核对。</div>
      </div>
    </section>

    <section class="manual-detail-panel panel flex min-h-0 flex-col overflow-hidden">
      <div class="flex items-center justify-between border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">结构化编辑</h2>
          <p class="muted mt-1">{{ selectedDoc || '未选择文档' }}</p>
        </div>
        <button class="btn" type="button" :disabled="!selectedItem" @click="focusEditor = !focusEditor">
          {{ focusEditor ? '退出专注' : '专注编辑' }}
        </button>
      </div>

      <div v-if="selectedItem" class="border-b border-slate-200 bg-slate-50 p-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="break-words text-sm font-semibold text-slate-800">{{ displayItemTitle(selectedItem) }}</div>
            <div class="mt-1 text-xs text-slate-500">
              {{ selectedItem.group_size > 1 ? `第 ${(selectedItem.group_pages || []).join('、')} 页` : `第 ${selectedItem.page} 页` }}
              · 元素 {{ selectedItem.element_index }} · {{ issueTypeLabel(selectedItem.issue_type) }}
            </div>
          </div>
          <span :class="riskClass(selectedItem.severity)">{{ severityLabel(selectedItem.severity) }}</span>
        </div>
      </div>

      <div class="manual-detail-scroll min-h-0 flex-1 overflow-auto">
        <div v-if="selectedItem" class="space-y-4 p-4">
          <div v-if="selectedItem.group_size > 1" class="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-950">
            <div class="font-semibold">跨页合并任务 · {{ selectedItem.group_size }} 个来源元素</div>
            <div class="mt-1">页码：{{ (selectedItem.group_pages || []).join('、') }}</div>
            <div class="mt-1 text-xs text-blue-700">
              {{ selectedItem.group_reason }} · 置信度 {{ formatConfidence(selectedItem.group_confidence) }}
            </div>
          </div>

          <div>
            <div class="mb-1 text-xs font-semibold uppercase text-slate-500">命中规则</div>
            <div class="space-y-2">
              <div v-for="rule in selectedItem.matched_rules" :key="rule.id" class="rounded-md bg-amber-50 p-3 text-sm leading-6 text-amber-900">
                <div class="font-semibold">{{ rule.label || rule.id }}</div>
                <div>{{ rule.reason }}</div>
                <div class="text-xs text-amber-700">命中词：{{ (rule.matched_terms || []).join(' / ') }}</div>
              </div>
              <div v-if="!selectedItem.matched_rules?.length" class="rounded-md bg-slate-50 p-3 text-sm text-slate-600">
                通用复杂度命中：{{ (selectedItem.generic_reasons || []).join(' / ') }}
              </div>
            </div>
          </div>

          <div>
            <div class="mb-1 text-xs font-semibold uppercase text-slate-500">当前解析预览</div>
            <div v-if="containsHtmlTable(selectedItem.current_text)" class="table-preview max-h-80 overflow-auto rounded-md bg-slate-50 p-3 text-sm text-slate-800" v-html="safeHtml(selectedItem.current_text)"></div>
            <div v-else class="max-h-60 overflow-auto rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700 whitespace-pre-wrap">{{ selectedItem.current_text }}</div>
            <details class="mt-2 rounded-md border border-slate-200 bg-white p-3">
              <summary class="cursor-pointer text-xs font-semibold text-slate-500">查看解析源码</summary>
              <pre class="mt-2 max-h-60 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-600">{{ selectedItem.current_text }}</pre>
            </details>
          </div>

          <div>
            <div class="mb-1 text-xs font-semibold uppercase text-slate-500">建议结构化字段</div>
            <div class="rounded-md bg-blue-50 p-3 text-sm leading-6 text-blue-950">
              <div v-for="(value, key) in selectedItem.target_schema" :key="key">
                <span class="font-semibold">{{ key }}：</span>{{ value }}
              </div>
            </div>
          </div>

          <div>
            <div class="mb-2 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="text-xs font-semibold uppercase text-slate-500">结构化 JSON 草稿</div>
                <span class="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">{{ draftStatus }}</span>
              </div>
              <div class="flex gap-2">
                <button class="btn h-8 px-3 text-xs" type="button" :disabled="busy" @click="buildDraft">
                  {{ selectedItem.group_size > 1 ? '生成合并草稿' : '生成' }}
                </button>
                <button
                  class="btn h-8 px-3 text-xs"
                  :disabled="busy || aiGenerating || !draftText.trim()"
                  type="button"
                  @click="generateAiSuggestion"
                >
                  {{ aiGenerating ? 'AI 生成中' : 'AI 生成建议' }}
                </button>
                <button class="btn h-8 px-3 text-xs" type="button" :disabled="busy || !draftText.trim()" @click="saveDraft">保存草稿</button>
                <button class="btn h-8 px-3 text-xs" type="button" :disabled="busy || !draftText.trim()" @click="validateDraft">校验</button>
                <button class="btn btn-primary h-8 px-3 text-xs" type="button" :disabled="busy || draftState !== 'validated'" @click="publishDraft">发布</button>
                <button class="btn btn-danger h-8 px-3 text-xs" type="button" :disabled="busy || draftState !== 'published'" @click="rollbackDraft">回滚</button>
              </div>
            </div>
            <StructuredDraftEditor v-model="draftText" :validation="validationResult" />
          </div>

          <div v-if="aiSuggestion" class="rounded-md border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-950">
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="font-semibold">AI 结构化建议</div>
                <div class="mt-1 text-xs text-indigo-700">
                  {{ aiSuggestion.model }} · 置信度 {{ formatConfidence(aiSuggestion.proposal?.confidence) }}
                </div>
              </div>
              <button
                class="btn btn-primary h-8 px-3 text-xs"
                type="button"
                :disabled="aiSuggestion.stale || aiSuggestion.proposal?.quality?.applicable === false"
                @click="applyAiSuggestion"
              >
                应用建议
              </button>
            </div>
            <div class="mt-3 grid grid-cols-2 gap-3">
              <div class="rounded bg-white/70 p-3">
                <div class="text-xs text-slate-500">当前草稿</div>
                <div class="mt-1 font-semibold">
                  {{ aiSuggestion.baseline?.column_count || 0 }} 列 · {{ aiSuggestion.baseline?.row_count || 0 }} 行
                </div>
              </div>
              <div class="rounded bg-white/70 p-3">
                <div class="text-xs text-slate-500">AI 建议</div>
                <div class="mt-1 font-semibold">
                  {{ aiSuggestion.proposal?.columns?.length || 0 }} 列 · {{ aiSuggestion.proposal?.rows?.length || 0 }} 行
                </div>
              </div>
            </div>
            <div v-if="aiSuggestion.stale" class="mt-3 rounded bg-amber-100 px-3 py-2 text-amber-900">
              草稿已在建议生成后发生变化，请重新生成建议。
            </div>
            <div v-if="aiSuggestion.proposal?.quality?.warnings?.length" class="mt-3 rounded bg-amber-100 px-3 py-2 text-amber-950">
              <div class="font-semibold">质量提醒</div>
              <ul class="mt-1 list-disc space-y-1 pl-5">
                <li v-for="item in aiSuggestion.proposal.quality.warnings" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div v-if="aiSuggestion.proposal?.quality?.blocking_errors?.length" class="mt-3 rounded bg-red-100 px-3 py-2 text-red-900">
              <div class="font-semibold">无法应用</div>
              <ul class="mt-1 list-disc space-y-1 pl-5">
                <li v-for="item in aiSuggestion.proposal.quality.blocking_errors" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div v-if="aiSuggestion.proposal?.assumptions?.length" class="mt-3">
              <div class="text-xs font-semibold uppercase text-indigo-700">不确定项</div>
              <ul class="mt-1 list-disc space-y-1 pl-5">
                <li v-for="item in aiSuggestion.proposal.assumptions" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>

          <div v-if="validationResult">
            <div class="mb-2 text-xs font-semibold uppercase text-slate-500">校验结果</div>
            <div
              class="rounded-md border p-3 text-sm"
              :class="validationResult.valid ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'"
            >
              <div class="font-semibold">
                {{ validationResult.valid ? '校验通过' : `发现 ${validationResult.error_count} 个错误` }}
                <span v-if="validationResult.warning_count"> · {{ validationResult.warning_count }} 个警告</span>
              </div>
              <ul v-if="validationResult.errors?.length" class="mt-2 space-y-1">
                <li v-for="entry in validationResult.errors" :key="`${entry.path}-${entry.code}`">
                  <span class="font-mono text-xs">{{ entry.path }}</span>：{{ entry.message }}
                </li>
              </ul>
              <ul v-if="validationResult.warnings?.length" class="mt-2 space-y-1 text-amber-800">
                <li v-for="entry in validationResult.warnings" :key="`${entry.path}-${entry.code}`">
                  <span class="font-mono text-xs">{{ entry.path }}</span>：{{ entry.message }}
                </li>
              </ul>
            </div>
          </div>

          <div v-if="versions.length">
            <div class="mb-2 text-xs font-semibold uppercase text-slate-500">发布历史</div>
            <div class="overflow-hidden rounded-md border border-slate-200">
              <div v-for="version in versions" :key="version.version_id" class="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-xs last:border-0">
                <div>
                  <div class="font-mono text-slate-700">{{ version.version_id }}</div>
                  <div class="mt-1 text-slate-500">{{ formatTimestamp(version.created_at) }}</div>
                </div>
                <span :class="version.rolled_back_at ? 'text-amber-700' : 'text-emerald-700'">
                  {{ version.rolled_back_at ? '已回滚' : (version.replaced_existing ? '覆盖发布' : '首次发布') }}
                </span>
              </div>
            </div>
          </div>

          <div>
            <label class="mb-1 block text-xs font-semibold uppercase text-slate-500">处理备注</label>
            <textarea v-model="notes" class="field min-h-28 w-full resize-y leading-6"></textarea>
          </div>
        </div>
        <div v-else class="p-6 text-sm text-slate-500">选择左侧复杂表任务开始处理。</div>
      </div>

      <div class="manual-action-bar border-t border-slate-200 bg-white p-4">
        <div class="grid grid-cols-3 gap-2">
          <button class="btn btn-primary" type="button" :disabled="!selectedItem" @click="setStatus('approved')">已结构化</button>
          <button class="btn" type="button" :disabled="!selectedItem" @click="setStatus('pending')">待处理</button>
          <button class="btn btn-danger" type="button" :disabled="!selectedItem" @click="setStatus('rejected')">暂不处理</button>
        </div>
        <p v-if="message" class="mt-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ message }}</p>
        <p v-if="error" class="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </div>
    </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  buildManualStructuringDraft,
  getAdminJob,
  getAdminPageImageObjectUrl,
  getManualStructuringDetail,
  getManualStructuringDraft,
  getManualStructuringSuggestion,
  listManualStructuringVersions,
  publishManualStructuringDraft,
  rollbackManualStructuringDraft,
  saveManualStructuringDraft,
  scanManualStructuringQueue,
  startManualStructuringBatchSuggestions,
  startManualStructuringSuggestion,
  updateManualStructuringStatus,
  validateManualStructuringDraft,
} from '../admin-api'
import { errorMessage } from '../api'
import type {
  ManualDraftResponse,
  ManualDocumentSummary,
  ManualStructuringItemView,
  ManualValidationResponse,
  ManualVersionSummary,
  StructuringSuggestionView,
} from '../contracts'
import StructuredDraftEditor from './StructuredDraftEditor.vue'

const props = defineProps<{
  documents: ManualDocumentSummary[]
  activeDataVersion?: string
}>()
const emit = defineEmits<{ refresh: [] }>()

const selectedDoc = ref('')
const items = ref<ManualStructuringItemView[]>([])
const selectedItem = ref<ManualStructuringItemView | null>(null)
const previewItem = ref<ManualStructuringItemView | null>(null)
const statusFilter = ref('pending')
const pageImageUrl = ref('')
const pageImageStatus = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
const pageImageError = ref('')
const notes = ref('')
const draftText = ref('')
const busy = ref(false)
const focusEditor = ref(false)
const message = ref('')
const error = ref('')
const validationResult = ref<ManualValidationResponse | null>(null)
const versions = ref<ManualVersionSummary[]>([])
const aiSuggestion = ref<StructuringSuggestionView | null>(null)
const aiGenerating = ref(false)
let previewRequest = 0

const totalPending = computed(() => props.documents.reduce(
  (sum, item) => sum + Number(item.pending_task_count ?? item.pending_count ?? 0),
  0,
))
const totalApproved = computed(() => props.documents.reduce(
  (sum, item) => sum + Number(item.approved_task_count ?? item.approved_count ?? 0),
  0,
))
const totalTaskCount = computed(() => props.documents.reduce(
  (sum, item) => sum + Number(item.task_count ?? 0),
  0,
))
const totalSuggestionCount = computed(() => props.documents.reduce(
  (sum, item) => sum + Number(item.suggestion_count ?? 0),
  0,
))
const suggestionCoverage = computed(() => `${totalSuggestionCount.value} / ${totalTaskCount.value}`)
const activeDataVersion = computed(() => props.activeDataVersion || '-')
const activeDataVersionLabel = computed(() => activeDataVersion.value === '-' ? '-' : activeDataVersion.value.slice(0, 12))
const draftState = computed(() => {
  try {
    const draft = parseJsonObject(draftText.value || '{}')
    return stringValue(draft.draft_status, '未生成')
  } catch {
    return 'JSON 无效'
  }
})
const draftStatus = computed(() => draftStatusLabel(draftState.value))
const filteredItems = computed(() => {
  const filtered = statusFilter.value
    ? items.value.filter(item => item.status === statusFilter.value)
    : items.value
  const logicalTasks = new Map<string, ManualStructuringItemView>()
  for (const item of filtered) {
    const key = item.group_id || item.id
    if (!logicalTasks.has(key) || item.id === item.group_primary_item_id) {
      logicalTasks.set(key, item)
    }
  }
  return Array.from(logicalTasks.values())
})
const groupMembers = computed(() => {
  if (!selectedItem.value) return []
  const memberIds = selectedItem.value.group_item_ids || [selectedItem.value.id]
  const byId = new Map(items.value.map(item => [item.id, item]))
  return memberIds
    .map(id => byId.get(id))
    .filter((item): item is ManualStructuringItemView => item !== undefined)
})

async function scanQueue() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await scanManualStructuringQueue()
    message.value = `已扫描 ${result.candidate_count || 0} 个复杂表候选`
    emit('refresh')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function startBatchSuggestions() {
  busy.value = true
  error.value = ''
  try {
    const job = await startManualStructuringBatchSuggestions({
      body: { documents: [], force: false },
    })
    message.value = `批量建议任务已提交：${job.job_id}，可在构建任务中查看进度`
    emit('refresh')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function selectDoc(doc: string) {
  selectedDoc.value = doc
  selectedItem.value = null
  previewItem.value = null
  items.value = []
  releasePageImage()
  await loadDocQueue()
}

async function loadDocQueue() {
  if (!selectedDoc.value) return
  const detail = await getManualStructuringDetail({ path: { doc: selectedDoc.value } })
  items.value = normalizeItems(detail.items || [])
  if (!selectedItem.value && filteredItems.value.length) {
    await openItem(filteredItems.value[0])
  }
}

async function openItem(item: ManualStructuringItemView) {
  selectedItem.value = item
  previewItem.value = item
  notes.value = item.notes || ''
  draftText.value = ''
  validationResult.value = null
  versions.value = []
  aiSuggestion.value = null
  message.value = ''
  error.value = ''
  await Promise.all([loadPreviewImage(item), loadDraftIfExists(), loadVersions(), loadAiSuggestion()])
}

async function previewMember(item: ManualStructuringItemView) {
  previewItem.value = item
  await loadPreviewImage(item)
}

async function loadPreviewImage(item: ManualStructuringItemView) {
  releasePageImage()
  const request = ++previewRequest
  pageImageStatus.value = 'loading'
  pageImageError.value = ''
  try {
    const objectUrl = await getAdminPageImageObjectUrl({
      path: { doc: selectedDoc.value, page: Number(item.page) },
    })
    if (request !== previewRequest) {
      URL.revokeObjectURL(objectUrl)
      return
    }
    pageImageUrl.value = objectUrl
    pageImageStatus.value = 'ready'
  } catch (err: unknown) {
    if (request !== previewRequest) return
    pageImageStatus.value = 'error'
    const detail = errorMessage(err)
    pageImageError.value = detail.includes('404')
      ? '当前数据源目录中没有找到对应的源 PDF。请先补充该规范的原始 PDF，再重新扫描队列。'
      : `页面截图加载失败：${detail || '请求未完成'}。请检查服务状态后重试。`
  }
}

async function retryPageImage() {
  if (previewItem.value) await loadPreviewImage(previewItem.value)
}

function handlePageImageError() {
  releasePageImage()
  pageImageStatus.value = 'error'
  pageImageError.value = '页面截图返回了无效内容，请检查源 PDF 和页面资源后重试。'
}

async function setStatus(status: string) {
  if (!selectedItem.value) return
  const currentId = selectedItem.value.id
  await updateManualStructuringStatus({
    path: { doc: selectedDoc.value, item_id: currentId },
    body: { status, notes: notes.value },
  })
  items.value = items.value.map(item => item.id === currentId ? { ...item, status, notes: notes.value } : item)
  message.value = `已标记为 ${statusLabel(status)}`
  emit('refresh')
  if (statusFilter.value && statusFilter.value !== status) {
    const next = filteredItems.value.find(item => item.id !== currentId)
    if (next) await openItem(next)
    else clearSelection()
  }
}

async function buildDraft() {
  if (!selectedItem.value) return
  try {
    const draft = await buildManualStructuringDraft({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    draftText.value = JSON.stringify(draftWithoutPath(draft), null, 2)
    message.value = '已生成结构化草稿'
  } catch (err: unknown) {
    error.value = errorMessage(err)
  }
}

async function loadDraftIfExists() {
  if (!selectedItem.value) return
  try {
    const draft = await getManualStructuringDraft({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    draftText.value = JSON.stringify(draftWithoutPath(draft), null, 2)
    validationResult.value = asValidationResult(draft.validation)
  } catch {
    draftText.value = ''
    validationResult.value = null
  }
}

async function saveDraft() {
  if (!selectedItem.value) return
  try {
    const parsed = parseJsonObject(draftText.value)
    const saved = await saveManualStructuringDraft({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
      body: { draft: parsed },
    })
    draftText.value = JSON.stringify(draftWithoutPath(saved), null, 2)
    validationResult.value = asValidationResult(saved.validation)
    message.value = '结构化草稿已保存'
    return true
  } catch (err: unknown) {
    error.value = errorMessage(err)
    return false
  }
}

async function generateAiSuggestion() {
  if (!selectedItem.value || !await saveDraft()) return
  aiGenerating.value = true
  error.value = ''
  try {
    const job = await startManualStructuringSuggestion({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    message.value = `AI 建议任务已提交：${job.job_id}`
    for (let attempt = 0; attempt < 130; attempt += 1) {
      await delay(1500)
      const current = await getAdminJob({ path: { job_id: job.job_id } })
      if (current.status === 'succeeded') {
        await loadAiSuggestion()
        message.value = `AI 建议已生成：${aiSuggestion.value?.proposal?.rows?.length || 0} 行`
        return
      }
      if (current.status === 'failed') {
        throw new Error(current.error || 'AI 建议生成失败')
      }
    }
    throw new Error('AI 建议生成超时，请在任务列表查看状态')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    aiGenerating.value = false
  }
}

async function loadAiSuggestion() {
  if (!selectedItem.value) return
  try {
    aiSuggestion.value = await getManualStructuringSuggestion({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    }) as StructuringSuggestionView
  } catch {
    aiSuggestion.value = null
  }
}

function applyAiSuggestion() {
  if (!aiSuggestion.value?.proposal || aiSuggestion.value.stale) return
  try {
    const draft = parseJsonObject(draftText.value)
    const proposal = aiSuggestion.value.proposal
    draft.columns = proposal.columns || []
    draft.rows = proposal.rows || []
    draft.table_aliases = proposal.table_aliases || []
    draft.notes = proposal.notes || []
    draft.draft_status = 'needs_review'
    delete draft.validation
    draftText.value = JSON.stringify(draft, null, 2)
    validationResult.value = null
    message.value = 'AI 建议已应用到本地草稿，请核对后保存并校验'
  } catch (err: unknown) {
    error.value = errorMessage(err)
  }
}

async function validateDraft() {
  if (!selectedItem.value) return
  busy.value = true
  error.value = ''
  try {
    if (!await saveDraft()) return
    const validation = await validateManualStructuringDraft({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    validationResult.value = validation
    await loadDraftIfExists()
    message.value = validation.valid ? '草稿校验通过，可以发布' : '草稿校验未通过，请按提示修正'
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function publishDraft() {
  if (!selectedItem.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await publishManualStructuringDraft({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    await Promise.all([loadDraftIfExists(), loadVersions(), loadDocQueue()])
    message.value = `已发布 ${result.target_filename}`
    emit('refresh')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function rollbackDraft() {
  if (!selectedItem.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await rollbackManualStructuringDraft({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    await Promise.all([loadDraftIfExists(), loadVersions(), loadDocQueue()])
    message.value = result.rollback_action === 'restored' ? '已恢复发布前版本' : '已撤下首次发布的结构化表'
    emit('refresh')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function loadVersions() {
  if (!selectedItem.value) return
  try {
    const result = await listManualStructuringVersions({
      path: { doc: selectedDoc.value, item_id: selectedItem.value.id },
    })
    versions.value = result.versions || []
  } catch {
    versions.value = []
  }
}

function draftWithoutPath(draft: ManualDraftResponse) {
  const copy: Record<string, unknown> = { ...draft }
  delete copy.draft_path
  return copy
}

function asValidationResult(value: unknown): ManualValidationResponse | null {
  if (!value || typeof value !== 'object' || typeof (value as { valid?: unknown }).valid !== 'boolean') {
    return null
  }
  return value as ManualValidationResponse
}

function formatTimestamp(value?: number | null) {
  if (!value) return '-'
  return new Date(value * 1000).toLocaleString()
}

function formatConfidence(value: unknown) {
  if (typeof value === 'string' && value.endsWith('%')) return value
  const number = Number(value)
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : '-'
}

function statusLabel(status: string) {
  if (status === 'approved') return '已结构化'
  if (status === 'rejected') return '暂不处理'
  return '待处理'
}

function severityLabel(severity: string) {
  if (severity === 'high') return '高风险'
  if (severity === 'medium') return '中风险'
  return '低风险'
}

function issueTypeLabel(issueType: string) {
  const labels: Record<string, string> = {
    complex_snow_distribution: '复杂表格',
    complex_table: '复杂表格',
    table_misaligned: '普通表格',
    table_header_missing: '表头缺失',
    ocr_error: 'OCR 错误',
    formula_error: '公式识别',
  }
  return labels[issueType] || issueType.replaceAll('_', ' ')
}

function displayItemTitle(item: ManualStructuringItemView) {
  const title = (item.title || item.id).replace(/\$[\s\S]*?\$/g, '').replace(/\s+/g, ' ').trim()
  return title || item.id
}

function draftStatusLabel(status: string) {
  const labels: Record<string, string> = {
    needs_review: '待校对',
    validated: '已校验',
    published: '已发布',
    draft: '草稿',
    '未生成': '未生成',
    'JSON 无效': 'JSON 无效',
  }
  return labels[status] || status
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parseJsonObject(value: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(value)
  if (!isRecord(parsed)) throw new Error('结构化草稿必须是 JSON 对象')
  return parsed
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function numberValue(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function numberArray(value: unknown): number[] {
  return Array.isArray(value)
    ? value.map(item => Number(item)).filter(Number.isFinite)
    : []
}

function normalizeItems(rawItems: Array<Record<string, unknown>>): ManualStructuringItemView[] {
  return rawItems.map(item => {
    const groupItemIds = stringArray(item.group_item_ids)
    const matchedRules = Array.isArray(item.matched_rules)
      ? item.matched_rules.filter(isRecord).map(rule => ({
          id: stringValue(rule.id),
          label: stringValue(rule.label),
          reason: stringValue(rule.reason),
          matched_terms: stringArray(rule.matched_terms),
        }))
      : []
    const id = stringValue(item.id)
    return {
      id,
      status: stringValue(item.status || item.review_status, 'pending'),
      severity: stringValue(item.severity, 'low'),
      page: numberValue(item.page),
      element_index: numberValue(item.element_index),
      issue_type: stringValue(item.issue_type, 'complex_table'),
      title: stringValue(item.title, id),
      notes: stringValue(item.notes),
      current_text: stringValue(item.current_text),
      group_id: stringValue(item.group_id, id),
      group_primary_item_id: stringValue(item.group_primary_item_id, id),
      group_item_ids: groupItemIds.length ? groupItemIds : [id],
      group_pages: numberArray(item.group_pages),
      group_size: numberValue(item.group_size, groupItemIds.length || 1),
      group_reason: stringValue(item.group_reason),
      group_confidence: stringValue(item.group_confidence),
      matched_rules: matchedRules,
      generic_reasons: stringArray(item.generic_reasons),
      target_schema: isRecord(item.target_schema) ? item.target_schema : {},
    }
  })
}

function clearSelection() {
  selectedItem.value = null
  previewItem.value = null
  notes.value = ''
  draftText.value = ''
  validationResult.value = null
  versions.value = []
  aiSuggestion.value = null
  releasePageImage()
}

function releasePageImage() {
  previewRequest += 1
  if (pageImageUrl.value) URL.revokeObjectURL(pageImageUrl.value)
  pageImageUrl.value = ''
  pageImageStatus.value = 'idle'
  pageImageError.value = ''
}

function riskClass(severity: string) {
  const base = 'rounded px-2 py-0.5 text-xs'
  if (severity === 'high') return `${base} bg-red-100 text-red-700`
  if (severity === 'medium') return `${base} bg-amber-100 text-amber-700`
  return `${base} bg-slate-100 text-slate-600`
}

function containsHtmlTable(value: string) {
  return /<table[\s>]/i.test(value || '')
}

function safeHtml(value: string) {
  return (value || '')
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
}

watch(() => props.documents, docs => {
  if (!selectedDoc.value && docs.length) selectDoc(docs[0].doc)
}, { deep: true })

function handlePageAction(event: Event) {
  const detail = (event as CustomEvent<{ key?: string }>).detail
  if (detail?.key === 'manual') void scanQueue()
}

onMounted(() => {
  if (props.documents.length) selectDoc(props.documents[0].doc)
  window.addEventListener('admin-page-action', handlePageAction)
})
onBeforeUnmount(() => {
  window.removeEventListener('admin-page-action', handlePageAction)
  releasePageImage()
})
</script>

<style scoped>
.manual-page {
  min-width: 0;
}

.manual-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.manual-workspace {
  height: calc(100dvh - 250px);
  min-height: 680px;
}

.manual-detail-panel,
.manual-detail-scroll,
.manual-task-list {
  min-height: 0;
}

.manual-action-bar {
  flex: none;
}

@media (max-width: 1180px) {
  .manual-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .manual-workspace {
    height: auto;
  }
}

@media (max-width: 640px) {
  .manual-stat-grid {
    grid-template-columns: 1fr;
  }
}

.table-preview :deep(table) {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  background: white;
}

.table-preview :deep(td),
.table-preview :deep(th) {
  border: 1px solid #cbd5e1;
  padding: 8px 10px;
  vertical-align: middle;
  line-height: 1.6;
}

.table-preview :deep(th),
.table-preview :deep(tr:first-child td) {
  background: #f8fafc;
  font-weight: 700;
}
</style>
