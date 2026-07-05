<template>
  <div
    class="grid h-full min-h-[760px] gap-5"
    :class="focusEditor ? 'grid-cols-1' : 'grid-cols-[300px_minmax(480px,1fr)_minmax(480px,34vw)]'"
  >
    <section v-if="!focusEditor" class="panel flex min-h-0 flex-col">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">人工结构化</h2>
        <p class="muted mt-1">{{ totalPending }} 个复杂表待处理</p>
      </div>
      <div class="border-b border-slate-200 p-3">
        <div class="grid grid-cols-2 gap-2">
          <button class="btn" :disabled="busy" @click="scanQueue">扫描复杂表</button>
          <button class="btn btn-primary" :disabled="busy" @click="startBatchSuggestions">批量 AI 建议</button>
        </div>
      </div>
      <div class="min-h-0 flex-1 overflow-auto p-3">
        <button
          v-for="doc in documents"
          :key="doc.doc"
          class="mb-2 w-full rounded-md border border-slate-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
          :class="selectedDoc === doc.doc ? 'border-blue-500 bg-blue-50' : 'bg-white'"
          @click="selectDoc(doc.doc)"
        >
          <div class="line-clamp-2 text-sm font-semibold">{{ doc.doc }}</div>
          <div class="mt-2 flex items-center gap-2 text-xs text-slate-500">
            <span>{{ doc.pending_task_count ?? doc.pending_count ?? 0 }} pending</span>
            <span>{{ doc.approved_task_count ?? doc.approved_count ?? 0 }} done</span>
            <span>{{ doc.suggestion_count || 0 }} AI</span>
          </div>
        </button>
        <p v-if="!documents.length" class="p-4 text-sm text-slate-500">暂无复杂表队列。</p>
      </div>
    </section>

    <section v-if="!focusEditor" class="panel flex min-h-0 flex-col overflow-hidden">
      <div class="flex items-center justify-between border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">原 PDF 页面</h2>
          <p class="muted mt-1">{{ previewItem ? `page ${previewItem.page} · element ${previewItem.element_index}` : '选择任务后显示页面截图' }}</p>
        </div>
        <button class="btn" :disabled="!selectedDoc" @click="loadDocQueue">刷新队列</button>
      </div>
      <div v-if="groupMembers.length > 1" class="flex gap-2 overflow-x-auto border-b border-slate-200 px-4 py-2">
        <button
          v-for="member in groupMembers"
          :key="member.id"
          class="btn h-8 shrink-0 px-3 text-xs"
          :class="previewItem?.id === member.id ? 'border-blue-500 bg-blue-50 text-blue-700' : ''"
          @click="previewMember(member)"
        >
          page {{ member.page }}
        </button>
      </div>
      <div class="min-h-0 flex-1 overflow-auto bg-slate-200 p-5">
        <img v-if="pageImageUrl" :src="pageImageUrl" class="mx-auto max-w-full rounded-sm bg-white shadow" />
        <div v-else class="flex h-full items-center justify-center text-slate-500">暂无页面预览</div>
      </div>
    </section>

    <section class="panel flex min-h-0 flex-col">
      <div class="flex items-center justify-between border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">复杂表详情</h2>
          <p class="muted mt-1">{{ selectedDoc || '未选择文档' }}</p>
        </div>
        <button class="btn" :disabled="!selectedItem" @click="focusEditor = !focusEditor">
          {{ focusEditor ? '退出专注' : '专注编辑' }}
        </button>
      </div>

      <div class="min-h-0 flex-1 overflow-auto">
        <div class="border-b border-slate-200 p-3">
          <select v-model="statusFilter" class="field h-9">
            <option value="pending">待处理</option>
            <option value="approved">已完成</option>
            <option value="rejected">暂不处理</option>
            <option value="">全部</option>
          </select>
        </div>

        <div class="max-h-72 overflow-auto border-b border-slate-200 p-3">
          <button
            v-for="item in filteredItems"
            :key="item.id"
            class="mb-2 w-full rounded-md border border-slate-200 p-3 text-left hover:bg-blue-50"
            :class="selectedItem?.id === item.id ? 'border-blue-500 bg-blue-50' : 'bg-white'"
            @click="openItem(item)"
          >
            <div class="flex items-center justify-between gap-2 text-sm font-semibold">
              <span class="line-clamp-1">{{ item.title || item.id }}</span>
              <span :class="riskClass(item.severity)">{{ item.severity }}</span>
            </div>
            <div class="mt-1 text-xs text-slate-500">
              {{ item.group_size > 1 ? `pages ${(item.group_pages || []).join(', ')}` : `page ${item.page}` }}
              · element {{ item.element_index }} · {{ item.issue_type }} · {{ item.status }}
            </div>
          </button>
          <p v-if="selectedDoc && !filteredItems.length" class="p-4 text-sm text-slate-500">该筛选下暂无任务。</p>
        </div>

        <div v-if="selectedItem" class="space-y-4 p-4">
          <div v-if="selectedItem.group_size > 1" class="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-950">
            <div class="font-semibold">跨页合并任务 · {{ selectedItem.group_size }} 个来源元素</div>
            <div class="mt-1">页码：{{ (selectedItem.group_pages || []).join('、') }}</div>
            <div class="mt-1 text-xs text-blue-700">
              {{ selectedItem.group_reason }} · {{ selectedItem.group_confidence }} confidence
            </div>
          </div>

          <div>
            <div class="mb-1 text-xs font-semibold uppercase text-slate-500">命中规则</div>
            <div class="space-y-2">
              <div v-for="rule in selectedItem.matched_rules" :key="rule.id" class="rounded-md bg-amber-50 p-3 text-sm leading-6 text-amber-900">
                <div class="font-semibold">{{ rule.label || rule.id }}</div>
                <div>{{ rule.reason }}</div>
                <div class="text-xs text-amber-700">terms: {{ (rule.matched_terms || []).join(' / ') }}</div>
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
                <button class="btn h-8 px-3 text-xs" :disabled="busy" @click="buildDraft">
                  {{ selectedItem.group_size > 1 ? '生成合并草稿' : '生成' }}
                </button>
                <button
                  class="btn h-8 px-3 text-xs"
                  :disabled="busy || aiGenerating || !draftText.trim()"
                  @click="generateAiSuggestion"
                >
                  {{ aiGenerating ? 'AI 生成中' : 'AI 生成建议' }}
                </button>
                <button class="btn h-8 px-3 text-xs" :disabled="busy || !draftText.trim()" @click="saveDraft">保存草稿</button>
                <button class="btn h-8 px-3 text-xs" :disabled="busy || !draftText.trim()" @click="validateDraft">校验</button>
                <button class="btn btn-primary h-8 px-3 text-xs" :disabled="busy || draftStatus !== 'validated'" @click="publishDraft">发布</button>
                <button class="btn btn-danger h-8 px-3 text-xs" :disabled="busy || draftStatus !== 'published'" @click="rollbackDraft">回滚</button>
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

      <div class="grid grid-cols-3 gap-2 border-t border-slate-200 p-4">
        <button class="btn btn-primary" :disabled="!selectedItem" @click="setStatus('approved')">已结构化</button>
        <button class="btn" :disabled="!selectedItem" @click="setStatus('pending')">待处理</button>
        <button class="btn btn-danger" :disabled="!selectedItem" @click="setStatus('rejected')">暂不处理</button>
      </div>
      <p v-if="message" class="mx-4 mb-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ message }}</p>
      <p v-if="error" class="mx-4 mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { apiBlobUrl, apiGet, apiPatch, apiPost, apiPut } from '../api'
import StructuredDraftEditor from './StructuredDraftEditor.vue'

const props = defineProps<{ documents: any[] }>()
const emit = defineEmits<{ refresh: [] }>()

const selectedDoc = ref('')
const items = ref<any[]>([])
const selectedItem = ref<any>(null)
const previewItem = ref<any>(null)
const statusFilter = ref('pending')
const pageImageUrl = ref('')
const notes = ref('')
const draftText = ref('')
const busy = ref(false)
const focusEditor = ref(false)
const message = ref('')
const error = ref('')
const validationResult = ref<any>(null)
const versions = ref<any[]>([])
const aiSuggestion = ref<any>(null)
const aiGenerating = ref(false)

const totalPending = computed(() => props.documents.reduce(
  (sum, item) => sum + Number(item.pending_task_count ?? item.pending_count ?? 0),
  0,
))
const draftStatus = computed(() => {
  try {
    return JSON.parse(draftText.value || '{}').draft_status || '未生成'
  } catch {
    return 'JSON 无效'
  }
})
const filteredItems = computed(() => {
  const filtered = statusFilter.value
    ? items.value.filter(item => item.status === statusFilter.value)
    : items.value
  const logicalTasks = new Map<string, any>()
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
  return memberIds.map((id: string) => byId.get(id)).filter(Boolean)
})

async function scanQueue() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await apiPost('/admin/manual-structuring/scan')
    message.value = `已扫描 ${result.candidate_count || 0} 个复杂表候选`
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function startBatchSuggestions() {
  busy.value = true
  error.value = ''
  try {
    const job = await apiPost('/admin/manual-structuring/ai-suggestions/batch', { force: false })
    message.value = `批量建议任务已提交：${job.job_id}，可在构建任务中查看进度`
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function selectDoc(doc: string) {
  selectedDoc.value = doc
  selectedItem.value = null
  previewItem.value = null
  pageImageUrl.value = ''
  await loadDocQueue()
}

async function loadDocQueue() {
  if (!selectedDoc.value) return
  const detail = await apiGet(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}`)
  items.value = normalizeItems(detail.items || [])
  if (!selectedItem.value && filteredItems.value.length) {
    await openItem(filteredItems.value[0])
  }
}

async function openItem(item: any) {
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

async function previewMember(item: any) {
  previewItem.value = item
  await loadPreviewImage(item)
}

async function loadPreviewImage(item: any) {
  if (pageImageUrl.value) URL.revokeObjectURL(pageImageUrl.value)
  pageImageUrl.value = ''
  try {
    pageImageUrl.value = await apiBlobUrl(`/admin/page-image/${encodeURIComponent(selectedDoc.value)}/${item.page}`)
  } catch {
    pageImageUrl.value = ''
  }
}

async function setStatus(status: string) {
  if (!selectedItem.value) return
  const currentId = selectedItem.value.id
  await apiPatch(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(currentId)}`, {
    status,
    notes: notes.value,
  })
  items.value = items.value.map(item => item.id === currentId ? { ...item, status, notes: notes.value } : item)
  message.value = `已标记为 ${status}`
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
    const draft = await apiPost(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/draft`)
    draftText.value = JSON.stringify(draftWithoutPath(draft), null, 2)
    message.value = '已生成结构化草稿'
  } catch (err: any) {
    error.value = err.message || String(err)
  }
}

async function loadDraftIfExists() {
  if (!selectedItem.value) return
  try {
    const draft = await apiGet(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/draft`)
    draftText.value = JSON.stringify(draftWithoutPath(draft), null, 2)
    validationResult.value = draft.validation || null
  } catch {
    draftText.value = ''
    validationResult.value = null
  }
}

async function saveDraft() {
  if (!selectedItem.value) return
  try {
    const parsed = JSON.parse(draftText.value)
    const saved = await apiPut(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/draft`, { draft: parsed })
    draftText.value = JSON.stringify(draftWithoutPath(saved), null, 2)
    validationResult.value = saved.validation || null
    message.value = '结构化草稿已保存'
    return true
  } catch (err: any) {
    error.value = err.message || String(err)
    return false
  }
}

async function generateAiSuggestion() {
  if (!selectedItem.value || !await saveDraft()) return
  aiGenerating.value = true
  error.value = ''
  try {
    const job = await apiPost(
      `/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/ai-suggestion`,
    )
    message.value = `AI 建议任务已提交：${job.job_id}`
    for (let attempt = 0; attempt < 130; attempt += 1) {
      await delay(1500)
      const current = await apiGet(`/admin/jobs/${job.job_id}`)
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
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    aiGenerating.value = false
  }
}

async function loadAiSuggestion() {
  if (!selectedItem.value) return
  try {
    aiSuggestion.value = await apiGet(
      `/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/ai-suggestion`,
    )
  } catch {
    aiSuggestion.value = null
  }
}

function applyAiSuggestion() {
  if (!aiSuggestion.value?.proposal || aiSuggestion.value.stale) return
  try {
    const draft = JSON.parse(draftText.value)
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
  } catch (err: any) {
    error.value = err.message || String(err)
  }
}

async function validateDraft() {
  if (!selectedItem.value) return
  busy.value = true
  error.value = ''
  try {
    if (!await saveDraft()) return
    validationResult.value = await apiPost(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/validate`)
    await loadDraftIfExists()
    message.value = validationResult.value.valid ? '草稿校验通过，可以发布' : '草稿校验未通过，请按提示修正'
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function publishDraft() {
  if (!selectedItem.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await apiPost(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/publish`)
    await Promise.all([loadDraftIfExists(), loadVersions(), loadDocQueue()])
    message.value = `已发布 ${result.target_filename}`
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function rollbackDraft() {
  if (!selectedItem.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await apiPost(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/rollback`)
    await Promise.all([loadDraftIfExists(), loadVersions(), loadDocQueue()])
    message.value = result.rollback_action === 'restored' ? '已恢复发布前版本' : '已撤下首次发布的结构化表'
    emit('refresh')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function loadVersions() {
  if (!selectedItem.value) return
  try {
    const result = await apiGet(`/admin/manual-structuring/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedItem.value.id)}/versions`)
    versions.value = result.versions || []
  } catch {
    versions.value = []
  }
}

function draftWithoutPath(draft: any) {
  const copy = { ...draft }
  delete copy.draft_path
  return copy
}

function formatTimestamp(value: number) {
  if (!value) return '-'
  return new Date(value * 1000).toLocaleString()
}

function formatConfidence(value: any) {
  const number = Number(value)
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : '-'
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function normalizeItems(rawItems: any[]) {
  return rawItems.map(item => ({ ...item, status: item.status || item.review_status || 'pending' }))
}

function clearSelection() {
  selectedItem.value = null
  previewItem.value = null
  notes.value = ''
  draftText.value = ''
  validationResult.value = null
  versions.value = []
  aiSuggestion.value = null
  if (pageImageUrl.value) URL.revokeObjectURL(pageImageUrl.value)
  pageImageUrl.value = ''
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

onMounted(() => {
  if (props.documents.length) selectDoc(props.documents[0].doc)
})
</script>

<style scoped>
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
