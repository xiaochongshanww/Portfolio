<template>
  <div class="grid h-full min-h-[760px] grid-cols-[300px_minmax(460px,1fr)_minmax(460px,34vw)] gap-5">
    <section class="panel flex min-h-0 flex-col">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">校对文档</h2>
        <p class="muted mt-1">{{ totalPending }} 个待审候选</p>
      </div>
      <div class="min-h-0 flex-1 overflow-auto p-3">
        <button
          v-for="doc in candidateDocs"
          :key="doc.doc"
          class="mb-2 w-full rounded-md border border-slate-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
          :class="selectedDoc === doc.doc ? 'border-blue-500 bg-blue-50' : 'bg-white'"
          @click="selectDoc(doc.doc)"
        >
          <div class="line-clamp-2 text-sm font-semibold">{{ doc.doc }}</div>
          <div class="mt-2 flex items-center gap-2 text-xs text-slate-500">
            <span>{{ doc.pending_count || 0 }} pending</span>
            <span>{{ doc.approved_count || 0 }} approved</span>
          </div>
        </button>
        <p v-if="!candidateDocs.length" class="p-4 text-sm text-slate-500">暂无候选文件。</p>
      </div>
    </section>

    <section class="panel flex min-h-0 flex-col overflow-hidden">
      <div class="flex items-center justify-between border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">原 PDF 页面</h2>
          <p class="muted mt-1">{{ selectedCandidate ? `page ${selectedCandidate.page} · element ${selectedCandidate.element_index}` : '选择候选后显示页面截图' }}</p>
        </div>
        <button class="btn" :disabled="!selectedDoc" @click="loadDocCandidates">刷新候选</button>
      </div>
      <div class="min-h-0 flex-1 overflow-auto bg-slate-200 p-5">
        <img v-if="pageImageUrl" :src="pageImageUrl" class="mx-auto max-w-full rounded-sm bg-white shadow" />
        <div v-else class="flex h-full items-center justify-center text-slate-500">暂无页面预览</div>
      </div>
    </section>

    <section class="panel review-detail-panel flex min-h-0 flex-col">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">候选详情与审批</h2>
        <p class="muted mt-1">{{ selectedDoc || '未选择文档' }}</p>
      </div>

      <div class="min-h-0 flex-1 overflow-auto">
        <div class="border-b border-slate-200 p-3">
          <div class="flex gap-2">
            <select v-model="statusFilter" class="field h-9">
              <option value="pending">待审</option>
              <option value="approved">已批准</option>
              <option value="rejected">已拒绝</option>
              <option value="">全部</option>
            </select>
            <button class="btn btn-primary" :disabled="!selectedDoc" @click="promoteApproved">应用已批准</button>
          </div>
        </div>

        <div class="max-h-72 overflow-auto border-b border-slate-200 p-3">
          <button
            v-for="candidate in filteredCandidates"
            :key="candidate.id"
            class="mb-2 w-full rounded-md border border-slate-200 p-3 text-left hover:bg-blue-50"
            :class="selectedCandidate?.id === candidate.id ? 'border-blue-500 bg-blue-50' : 'bg-white'"
            @click="openCandidate(candidate)"
          >
            <div class="flex items-center justify-between gap-2 text-sm font-semibold">
              <span>{{ candidate.id }}</span>
              <span :class="riskClass(candidate.severity)">{{ candidate.severity }}</span>
            </div>
            <div class="mt-1 text-xs text-slate-500">page {{ candidate.page }} · element {{ candidate.element_index }} · {{ candidate.issue_type }} · {{ candidate.status }}</div>
          </button>
          <p v-if="selectedDoc && !filteredCandidates.length" class="p-4 text-sm text-slate-500">该筛选下暂无候选。</p>
        </div>

        <div v-if="selectedCandidate" class="space-y-4 p-4">
          <div>
            <div class="mb-1 text-xs font-semibold uppercase text-slate-500">当前解析文本</div>
            <div
              v-if="containsHtmlTable(currentText)"
              class="table-preview max-h-72 overflow-auto rounded-md bg-slate-50 p-3 text-sm text-slate-800"
              v-html="safeHtml(currentText)"
            ></div>
            <details v-if="containsHtmlTable(currentText)" class="mt-2 rounded-md border border-slate-200 bg-white p-3">
              <summary class="cursor-pointer text-xs font-semibold text-slate-500">查看当前源码</summary>
              <pre class="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-600">{{ currentText }}</pre>
            </details>
            <div
              v-else-if="containsMarkdownTable(currentText)"
              class="markdown-preview max-h-72 overflow-auto rounded-md bg-slate-50 p-3 text-sm text-slate-800"
              v-html="renderMarkdown(currentText)"
            ></div>
            <div
              v-else-if="containsLatex(currentText)"
              class="math-preview max-h-72 overflow-auto rounded-md bg-slate-50 p-3 text-sm leading-7 text-slate-800"
              v-html="renderMathText(currentText)"
            ></div>
            <details v-if="!containsHtmlTable(currentText) && (containsLatex(currentText) || containsMarkdownTable(currentText))" class="mt-2 rounded-md border border-slate-200 bg-white p-3">
              <summary class="cursor-pointer text-xs font-semibold text-slate-500">查看当前源码</summary>
              <pre class="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-600">{{ currentText }}</pre>
            </details>
            <div v-else-if="!containsHtmlTable(currentText)" class="max-h-40 overflow-auto rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700 whitespace-pre-wrap">{{ currentText }}</div>
          </div>
          <div>
            <div class="mb-1 text-xs font-semibold uppercase text-slate-500">AI 证据</div>
            <div class="rounded-md bg-blue-50 p-3 text-sm leading-6 text-blue-950 whitespace-pre-wrap">{{ selectedCandidate.evidence_text || '无' }}</div>
          </div>
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase text-slate-500">最终修正文</label>
            <textarea v-model="finalText" class="field min-h-72 w-full resize-y leading-7"></textarea>
            <div v-if="containsHtmlTable(finalText)" class="mt-3">
              <div class="mb-1 text-xs font-semibold uppercase text-slate-500">最终表格预览</div>
              <div class="table-preview max-h-96 overflow-auto rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-800" v-html="safeHtml(finalText)"></div>
            </div>
            <div v-else-if="containsMarkdownTable(finalText)" class="mt-3">
              <div class="mb-1 text-xs font-semibold uppercase text-slate-500">最终 Markdown 预览</div>
              <div class="markdown-preview max-h-96 overflow-auto rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-800" v-html="renderMarkdown(finalText)"></div>
            </div>
            <div v-else-if="containsLatex(finalText)" class="mt-3">
              <div class="mb-1 text-xs font-semibold uppercase text-slate-500">最终公式预览</div>
              <div class="math-preview max-h-96 overflow-auto rounded-md border border-slate-200 bg-white p-3 text-sm leading-7 text-slate-800" v-html="renderMathText(finalText)"></div>
            </div>
          </div>
        </div>
        <div v-else class="p-6 text-sm text-slate-500">选择左侧候选开始校对。</div>
      </div>

      <div class="grid grid-cols-4 gap-2 border-t border-slate-200 p-4">
        <button class="btn btn-primary" :disabled="!selectedCandidate" @click="approveCandidate">批准</button>
        <button class="btn btn-danger" :disabled="!selectedCandidate" @click="setCandidateStatus('rejected')">拒绝</button>
        <button class="btn" :disabled="!selectedCandidate" @click="setCandidateStatus('pending')">待审</button>
        <button class="btn" :disabled="!selectedCandidate || !finalText.trim()" @click="saveApproved">保存修正</button>
      </div>

      <p v-if="message" class="mx-4 mb-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ message }}</p>
      <p v-if="error" class="mx-4 mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import MarkdownIt from 'markdown-it'
import { apiBlobUrl, apiGet, apiPatch, apiPost } from '../api'

const props = defineProps<{ candidateDocs: any[] }>()
const emit = defineEmits<{ refresh: [] }>()

const selectedDoc = ref('')
const candidates = ref<any[]>([])
const selectedCandidate = ref<any>(null)
const statusFilter = ref('pending')
const currentText = ref('')
const finalText = ref('')
const pageImageUrl = ref('')
const error = ref('')
const message = ref('')
const markdown = new MarkdownIt({ html: false, linkify: false, breaks: true })

const totalPending = computed(() => props.candidateDocs.reduce((sum, item) => sum + Number(item.pending_count || 0), 0))
const filteredCandidates = computed(() => {
  if (!statusFilter.value) return candidates.value
  return candidates.value.filter(item => item.status === statusFilter.value)
})

async function selectDoc(doc: string) {
  selectedDoc.value = doc
  selectedCandidate.value = null
  currentText.value = ''
  finalText.value = ''
  pageImageUrl.value = ''
  await loadDocCandidates()
}

async function loadDocCandidates() {
  if (!selectedDoc.value) return
  const detail = await apiGet(`/admin/corrections/candidates/${encodeURIComponent(selectedDoc.value)}`)
  candidates.value = normalizeCandidates(detail.candidates || detail.corrections || [])
  if (!selectedCandidate.value && filteredCandidates.value.length) {
    await openCandidate(filteredCandidates.value[0])
  }
}

async function openCandidate(candidate: any) {
  selectedCandidate.value = candidate
  message.value = ''
  error.value = ''
  finalText.value = candidate.suggested_text || candidate.final_text || currentText.value || ''
  try {
    const element = await apiGet(`/admin/elements/${encodeURIComponent(selectedDoc.value)}/${candidate.element_index}`)
    currentText.value = element.text || ''
  } catch {
    currentText.value = candidate.current_text || ''
  }
  if (pageImageUrl.value) URL.revokeObjectURL(pageImageUrl.value)
  pageImageUrl.value = await apiBlobUrl(`/admin/page-image/${encodeURIComponent(selectedDoc.value)}/${candidate.page}`)
}

async function setCandidateStatus(status: string) {
  if (!selectedCandidate.value) return
  const currentId = selectedCandidate.value.id
  const result = await apiPatch(`/admin/corrections/candidates/${encodeURIComponent(selectedDoc.value)}/${encodeURIComponent(selectedCandidate.value.id)}`, { status })
  candidates.value = result.candidates || result.corrections
    ? normalizeCandidates(result.candidates || result.corrections || [])
    : candidates.value.map(item => item.id === selectedCandidate.value.id ? { ...item, status } : item)
  message.value = `已标记为 ${status}`
  emit('refresh')
  const updatedCurrent = candidates.value.find(item => item.id === currentId)
  if (!statusFilter.value || statusFilter.value === status) {
    selectedCandidate.value = updatedCurrent ? { ...updatedCurrent } : { ...selectedCandidate.value, status }
    return
  }
  const next = filteredCandidates.value.find(item => item.id !== currentId) || null
  if (next) {
    await openCandidate(next)
  } else {
    clearSelection()
  }
}

async function saveApproved() {
  if (!selectedCandidate.value) return
  await apiPost(`/admin/corrections/approved/${encodeURIComponent(selectedDoc.value)}`, {
    id: `approved-${selectedCandidate.value.id}`,
    action: selectedCandidate.value.action || 'replace_text',
    target: selectedCandidate.value.target || { element_index: selectedCandidate.value.element_index, field: 'text' },
    value: finalText.value,
  })
  message.value = '已保存到已审批修正。'
}

async function approveCandidate() {
  await saveApproved()
  await setCandidateStatus('approved')
}

async function promoteApproved() {
  if (!selectedDoc.value) return
  await apiPost(`/admin/corrections/promote/${encodeURIComponent(selectedDoc.value)}`)
  message.value = '已将批准候选提升为正式修正，重建知识库时会应用。'
}

function riskClass(severity: string) {
  const base = 'rounded px-2 py-0.5 text-xs'
  if (severity === 'high') return `${base} bg-red-100 text-red-700`
  if (severity === 'medium') return `${base} bg-amber-100 text-amber-700`
  return `${base} bg-slate-100 text-slate-600`
}

function normalizeCandidates(items: any[]) {
  return items.map(item => ({
    ...item,
    status: item.status || item.review_status || 'pending',
    element_index: item.element_index ?? item.target?.element_index,
    target: item.target || { element_index: item.element_index, field: 'text' },
    action: item.action || item.suggested_patch?.action || 'replace_text',
    suggested_text: item.suggested_text ?? item.suggested_patch?.value ?? item.value ?? '',
    evidence_text: typeof item.evidence === 'string' ? item.evidence : item.evidence?.reason || '',
  }))
}

function clearSelection() {
  selectedCandidate.value = null
  currentText.value = ''
  finalText.value = ''
  if (pageImageUrl.value) URL.revokeObjectURL(pageImageUrl.value)
  pageImageUrl.value = ''
}

function containsHtmlTable(value: string) {
  return /<table[\s>]/i.test(value || '')
}

function containsLatex(value: string) {
  return /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$|\\\(|\\\[|\\frac|\\mu|\\beta|\\sigma|\\eta|\\rho|\\varphi|\\pmb|\\mathbf)/.test(value || '')
}

function containsMarkdownTable(value: string) {
  return /(^|\n)\s*\|.+\|\s*\n\s*\|[\s:|.-]+\|/m.test(value || '')
}

function safeHtml(value: string) {
  return (value || '')
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
}

function renderMathText(value: string) {
  const parts: string[] = []
  const source = value || ''
  const pattern = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g
  let cursor = 0
  for (const match of source.matchAll(pattern)) {
    const raw = match[0]
    const index = match.index ?? 0
    parts.push(escapeHtml(source.slice(cursor, index)))
    const displayMode = raw.startsWith('$$')
    const formula = displayMode ? raw.slice(2, -2).trim() : raw.slice(1, -1).trim()
    try {
      parts.push(katex.renderToString(formula, { displayMode, throwOnError: false, strict: false }))
    } catch {
      parts.push(escapeHtml(raw))
    }
    cursor = index + raw.length
  }
  parts.push(escapeHtml(source.slice(cursor)))
  return parts.join('').replace(/\n/g, '<br>')
}

function renderMarkdown(value: string) {
  return safeRenderedHtml(markdown.render(value || ''))
}

function safeRenderedHtml(value: string) {
  return (value || '')
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

watch(() => props.candidateDocs, docs => {
  if (!selectedDoc.value && docs.length) selectDoc(docs[0].doc)
}, { deep: true })

onMounted(() => {
  if (props.candidateDocs.length) selectDoc(props.candidateDocs[0].doc)
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

.table-preview :deep(sub) {
  font-size: 0.75em;
}

.math-preview :deep(.katex-display) {
  margin: 0.75rem 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.math-preview :deep(.katex) {
  font-size: 1.05em;
}

.markdown-preview :deep(table) {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  background: white;
}

.markdown-preview :deep(th),
.markdown-preview :deep(td) {
  border: 1px solid #cbd5e1;
  padding: 8px 10px;
  line-height: 1.6;
  vertical-align: middle;
}

.markdown-preview :deep(th) {
  background: #f8fafc;
  font-weight: 700;
}

.markdown-preview :deep(p) {
  margin: 0 0 0.75rem;
}

.review-detail-panel {
  resize: horizontal;
  overflow: auto;
  min-width: 460px;
  max-width: min(920px, calc(100vw - 820px));
}
</style>
