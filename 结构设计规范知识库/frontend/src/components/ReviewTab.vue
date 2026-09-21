<template>
  <div class="review-workspace">
    <section class="panel flex min-h-0 flex-col">
      <div class="border-b border-slate-200 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="panel-title">校对候选</h2>
            <p class="muted mt-1">按规范筛选待审和已处理项</p>
          </div>
          <span class="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">{{ totalPending }} 待审</span>
        </div>
        <p class="muted mt-2">共 {{ totalCandidateCount }} 个候选</p>
      </div>
      <div class="border-b border-slate-200 p-3">
        <label for="review-doc-filter" class="mb-1 block text-xs font-semibold text-slate-500">来源文档</label>
        <select id="review-doc-filter" v-model="selectedDoc" class="field w-full" :disabled="!candidateDocs.length" @change="selectDoc(selectedDoc)">
          <option v-for="doc in candidateDocs" :key="doc.doc" :value="doc.doc">{{ doc.source_file || doc.doc }}</option>
        </select>
        <label for="review-status-filter" class="sr-only">校对状态</label>
        <select id="review-status-filter" v-model="statusFilter" class="field mt-2 w-full">
          <option value="pending">待审</option>
          <option value="approved">已批准</option>
          <option value="rejected">已拒绝</option>
          <option value="">全部</option>
        </select>
      </div>
      <div class="review-candidate-list min-h-0 flex-1 overflow-auto p-3" aria-live="polite">
        <div v-if="loadingCandidates" class="p-4 text-sm text-slate-500">正在读取校对候选...</div>
        <template v-else-if="filteredCandidates.length">
          <button
            v-for="candidate in filteredCandidates"
            :key="candidate.id"
            class="review-candidate-item mb-2 w-full rounded-md border border-slate-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
            :class="selectedCandidate?.id === candidate.id ? 'border-blue-500 bg-blue-50' : 'bg-white'"
            type="button"
            @click="openCandidate(candidate)"
          >
            <div class="flex items-start justify-between gap-2 text-sm font-semibold">
              <span class="min-w-0 break-words">{{ candidate.id }}</span>
              <span :class="riskClass(candidate.severity)">{{ severityLabel(candidate.severity) }}</span>
            </div>
            <div class="mt-1 text-xs text-slate-500">
              第 {{ candidate.page }} 页 · 元素 {{ candidate.element_index }} · {{ issueTypeLabel(candidate.issue_type) }} · {{ statusLabel(candidate.status) }}
            </div>
          </button>
        </template>
        <div v-else-if="candidateDocs.length && statusFilter === 'pending'" class="p-4 text-sm leading-6 text-slate-500">
          当前文档没有待审候选。可切换到“已批准”或“全部”查看已处理项。
        </div>
        <div v-else-if="candidateDocs.length" class="p-4 text-sm leading-6 text-slate-500">当前筛选下暂无候选，请切换筛选条件。</div>
        <div v-else class="p-4 text-sm leading-6 text-slate-500">暂无校对候选。请先运行内容审计或等待候选生成。</div>
      </div>
    </section>

    <section class="panel flex min-h-0 flex-col overflow-hidden">
      <div class="flex items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">原 PDF 页面</h2>
          <p class="muted mt-1">{{ selectedCandidate ? `第 ${selectedCandidate.page} 页 · 元素 ${selectedCandidate.element_index}` : '选择左侧候选后显示页面截图' }}</p>
        </div>
        <div v-if="selectedCandidate" class="pdf-toolbar flex shrink-0 items-center gap-1" aria-label="PDF 查看工具">
          <button class="btn h-8 w-8 px-0 text-base" type="button" title="缩小" aria-label="缩小" data-testid="pdf-zoom-out" @click="zoomOut">−</button>
          <span class="min-w-12 text-center text-xs text-slate-500">{{ Math.round(pdfScale * 100) }}%</span>
          <button class="btn h-8 w-8 px-0 text-base" type="button" title="放大" aria-label="放大" data-testid="pdf-zoom-in" @click="zoomIn">+</button>
          <button class="btn h-8 px-2 text-xs" type="button" title="适应宽度" data-testid="pdf-fit-width" @click="fitPdfWidth">适应宽度</button>
        </div>
      </div>
      <div class="pdf-viewport min-h-0 flex-1 overflow-auto bg-slate-200 p-5" data-testid="pdf-viewport">
        <div v-if="pageImageStatus === 'loading' && !pageImageUrl" class="flex h-full items-center justify-center text-sm text-slate-500" aria-live="polite">正在加载页面截图...</div>
        <div v-else-if="pageImageStatus === 'error'" class="flex h-full flex-col items-center justify-center gap-3 text-center text-sm text-slate-500" role="alert">
          <span>页面截图加载失败，请重试。</span>
          <button class="btn h-8 px-3 text-xs" type="button" @click="retryPageImage">重新加载</button>
        </div>
        <div v-else-if="pageImageUrl" class="pdf-image-stage" :style="{ width: `${pdfScale * 100}%` }">
          <img
            :src="pageImageUrl"
            :alt="`${selectedDoc || '原 PDF'} 第 ${selectedCandidate?.page || ''} 页`"
            class="block h-auto w-full rounded-sm bg-white shadow"
            @error="handlePageImageError"
            @load="pageImageStatus = 'ready'"
          >
        </div>
        <div v-else class="flex h-full items-center justify-center text-sm text-slate-500">从左侧候选中选择一项开始核对。</div>
      </div>
    </section>

    <section class="panel review-detail-panel flex min-h-0 flex-col overflow-hidden">
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">候选详情与审批</h2>
        <p class="muted mt-1">{{ selectedCandidate ? `${selectedDoc} · ${selectedCandidate.id}` : '先从左侧候选列表选择一项' }}</p>
      </div>

      <div class="review-detail-scroll min-h-0 flex-1 overflow-auto">
        <div class="flex flex-wrap items-center gap-2 border-b border-slate-200 p-3">
          <button class="btn btn-primary" :disabled="!selectedDoc || !hasApprovedForSelectedDoc" type="button" @click="promoteApproved">应用当前文档已批准修正</button>
          <span v-if="selectedDoc && !hasApprovedForSelectedDoc" class="text-xs text-slate-500">当前文档暂无已批准修正</span>
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
            <textarea id="final-correction-text" v-model="finalText" class="field min-h-56 w-full resize-y leading-7"></textarea>
            <div class="review-final-preview mt-3 rounded-md border border-slate-200 bg-white p-3">
              <div class="mb-2 text-xs font-semibold uppercase text-slate-500">最终修正文预览</div>
              <div v-if="containsHtmlTable(finalText)" class="table-preview max-h-96 overflow-auto text-sm text-slate-800" v-html="safeHtml(finalText)"></div>
              <div v-else-if="containsMarkdownTable(finalText)" class="markdown-preview max-h-96 overflow-auto text-sm text-slate-800" v-html="renderMarkdown(finalText)"></div>
              <div v-else-if="containsLatex(finalText)" class="math-preview max-h-96 overflow-auto text-sm leading-7 text-slate-800" v-html="renderMathText(finalText)"></div>
              <div v-else class="whitespace-pre-wrap text-sm leading-6 text-slate-700">{{ finalText || '暂无修正文' }}</div>
            </div>
          </div>
        </div>
        <div v-else class="p-6 text-sm leading-6 text-slate-500">{{ loadingCandidates ? '正在读取候选，请稍候。' : '当前没有选中的候选。请从左侧列表选择一项，或切换候选状态。' }}</div>
      </div>

      <div class="review-action-bar border-t border-slate-200 bg-white p-4" data-testid="review-action-bar">
        <div class="grid grid-cols-4 gap-2">
          <button class="btn btn-primary" :disabled="!selectedCandidate" @click="approveCandidate">批准</button>
          <button class="btn btn-danger" :disabled="!selectedCandidate" @click="setCandidateStatus('rejected')">拒绝</button>
          <button class="btn" :disabled="!selectedCandidate" @click="setCandidateStatus('pending')">待审</button>
          <button class="btn" :disabled="!selectedCandidate || !finalText.trim()" @click="saveApproved">保存修正</button>
        </div>
        <p v-if="message" class="mt-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ message }}</p>
        <p v-if="error" class="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import MarkdownIt from 'markdown-it'
import {
  addApprovedCorrection,
  getAdminPageImageObjectUrl,
  getCorrectionCandidateDetail,
  getDocumentElement,
  promoteCorrections,
  updateCorrectionCandidate,
} from '../admin-api'
import type { CandidateDocumentSummary, CorrectionCandidateView } from '../contracts'

const props = defineProps<{ candidateDocs: CandidateDocumentSummary[] }>()
const emit = defineEmits<{ refresh: [] }>()

const selectedDoc = ref('')
const candidates = ref<CorrectionCandidateView[]>([])
const selectedCandidate = ref<CorrectionCandidateView | null>(null)
const statusFilter = ref('pending')
const currentText = ref('')
const finalText = ref('')
const pageImageUrl = ref('')
const pageImageStatus = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
const pdfScale = ref(1)
const loadingCandidates = ref(false)
const error = ref('')
const message = ref('')
const markdown = new MarkdownIt({ html: false, linkify: false, breaks: true })
let selectionRequest = 0

const totalPending = computed(() => props.candidateDocs.reduce((sum, item) => sum + Number(item.pending_count || 0), 0))
const totalCandidateCount = computed(() => props.candidateDocs.reduce((sum, item) => sum + Number(item.candidate_count || 0), 0))
const filteredCandidates = computed(() => {
  if (!statusFilter.value) return candidates.value
  return candidates.value.filter(item => item.status === statusFilter.value)
})
const hasApprovedForSelectedDoc = computed(() => Boolean(
  selectedDoc.value && candidates.value.some(item => item.status === 'approved'),
))

async function selectDoc(doc: string) {
  selectionRequest += 1
  selectedDoc.value = doc
  selectedCandidate.value = null
  currentText.value = ''
  finalText.value = ''
  releasePageImage()
  pageImageStatus.value = 'idle'
  await loadDocCandidates()
}

async function loadDocCandidates() {
  if (!selectedDoc.value) return
  loadingCandidates.value = true
  error.value = ''
  try {
    const detail = await getCorrectionCandidateDetail({ path: { doc: selectedDoc.value } })
    candidates.value = normalizeCandidates(detail.corrections || [])
    if (!selectedCandidate.value && filteredCandidates.value.length) {
      await openCandidate(filteredCandidates.value[0])
    }
  } catch (caught) {
    candidates.value = []
    clearSelection()
    error.value = caught instanceof Error ? caught.message : '读取校对候选失败。'
  } finally {
    loadingCandidates.value = false
  }
}

async function openCandidate(candidate: CorrectionCandidateView) {
  const request = ++selectionRequest
  selectedCandidate.value = candidate
  message.value = ''
  error.value = ''
  finalText.value = candidate.suggested_text || candidate.final_text || currentText.value || ''
  pdfScale.value = 1
  releasePageImage()
  pageImageStatus.value = 'loading'
  try {
    const element = await getDocumentElement({
      path: { doc: selectedDoc.value, element_index: Number(candidate.element_index) },
    })
    if (request === selectionRequest) currentText.value = typeof element.text === 'string' ? element.text : ''
  } catch {
    if (request === selectionRequest) currentText.value = candidate.current_text || ''
  }
  try {
    const nextImageUrl = await getAdminPageImageObjectUrl({
      path: { doc: selectedDoc.value, page: Number(candidate.page) },
    })
    if (request !== selectionRequest) {
      if (nextImageUrl.startsWith('blob:')) URL.revokeObjectURL(nextImageUrl)
      return
    }
    pageImageUrl.value = nextImageUrl
    pageImageStatus.value = 'loading'
  } catch {
    if (request === selectionRequest) {
      pageImageStatus.value = 'error'
      error.value = '页面截图加载失败，请检查来源 PDF 或重试。'
    }
  }
}

async function retryPageImage() {
  if (!selectedCandidate.value) return
  await openCandidate(selectedCandidate.value)
}

function handlePageImageError() {
  releasePageImage()
  pageImageStatus.value = 'error'
  error.value = '页面截图加载失败，请检查来源 PDF 或重试。'
}

function zoomOut() {
  pdfScale.value = Math.max(0.5, Number((pdfScale.value - 0.1).toFixed(2)))
}

function zoomIn() {
  pdfScale.value = Math.min(2, Number((pdfScale.value + 0.1).toFixed(2)))
}

function fitPdfWidth() {
  pdfScale.value = 1
}

async function setCandidateStatus(status: string) {
  if (!selectedCandidate.value) return
  const currentId = selectedCandidate.value.id
  await updateCorrectionCandidate({
    path: { doc: selectedDoc.value, candidate_id: selectedCandidate.value.id },
    body: { status },
  })
  candidates.value = candidates.value.map(item => (
    item.id === currentId ? { ...item, status } : item
  ))
  message.value = `已标记为 ${statusLabel(status)}`
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
  await addApprovedCorrection({
    path: { doc: selectedDoc.value },
    body: {
      id: `approved-${selectedCandidate.value.id}`,
      action: selectedCandidate.value.action || 'replace_text',
      target: selectedCandidate.value.target || { element_index: selectedCandidate.value.element_index, field: 'text' },
      value: finalText.value,
    },
  })
  message.value = '已保存到已审批修正。'
}

async function approveCandidate() {
  await saveApproved()
  await setCandidateStatus('approved')
}

async function promoteApproved() {
  if (!selectedDoc.value || !hasApprovedForSelectedDoc.value) return
  await promoteCorrections({ path: { doc: selectedDoc.value } })
  message.value = '已将当前文档的已批准修正提升为正式修正，重建知识库时会应用。'
}

function statusLabel(status: string) {
  return ({ pending: '待审', approved: '已批准', rejected: '已拒绝' } as Record<string, string>)[status] || status
}

function severityLabel(severity: string) {
  return ({ high: '高风险', medium: '中风险', low: '低风险' } as Record<string, string>)[severity] || severity
}

function issueTypeLabel(issueType: string) {
  return ({
    formula_error: '公式识别',
    ocr_error: 'OCR 错误',
    table_misaligned: '普通表格',
    paragraph_merge: '段落合并',
  } as Record<string, string>)[issueType] || issueType.replaceAll('_', ' ')
}

function riskClass(severity: string) {
  const base = 'rounded px-2 py-0.5 text-xs'
  if (severity === 'high') return `${base} bg-red-100 text-red-700`
  if (severity === 'medium') return `${base} bg-amber-100 text-amber-700`
  return `${base} bg-slate-100 text-slate-600`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function numberValue(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function normalizeCandidates(items: Array<Record<string, unknown>>): CorrectionCandidateView[] {
  return items.map(item => {
    const rawTarget = isRecord(item.target) ? item.target : {}
    const patch = isRecord(item.suggested_patch) ? item.suggested_patch : {}
    const evidence = isRecord(item.evidence) ? item.evidence : {}
    const elementIndex = numberValue(item.element_index ?? rawTarget.element_index)
    return {
      id: stringValue(item.id),
      status: stringValue(item.status || item.review_status, 'pending'),
      severity: stringValue(item.severity, 'low'),
      page: numberValue(item.page),
      element_index: elementIndex,
      issue_type: stringValue(item.issue_type, 'unknown'),
      action: stringValue(item.action || patch.action, 'replace_text'),
      target: {
        element_index: numberValue(rawTarget.element_index ?? elementIndex),
        field: stringValue(rawTarget.field, 'text'),
      },
      current_text: stringValue(item.current_text),
      final_text: stringValue(item.final_text),
      suggested_text: stringValue(item.suggested_text ?? patch.value ?? item.value),
      evidence_text: typeof item.evidence === 'string'
        ? item.evidence
        : stringValue(evidence.reason),
    }
  })
}

function clearSelection() {
  selectionRequest += 1
  selectedCandidate.value = null
  currentText.value = ''
  finalText.value = ''
  releasePageImage()
  pageImageStatus.value = 'idle'
}

function releasePageImage() {
  if (pageImageUrl.value.startsWith('blob:')) URL.revokeObjectURL(pageImageUrl.value)
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

onBeforeUnmount(() => releasePageImage())
</script>

<style scoped>
.review-candidate-list {
  scrollbar-gutter: stable;
}

.review-workspace {
  height: calc(100dvh - 134px);
}

.review-candidate-item {
  min-height: 92px;
}

.pdf-viewport {
  scrollbar-gutter: stable both-edges;
}

.pdf-image-stage {
  min-width: 100%;
  margin: 0 auto;
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

.review-final-preview {
  min-height: 88px;
}

.review-detail-panel {
  resize: horizontal;
  min-width: 460px;
  max-width: min(920px, calc(100vw - 820px));
}

.review-detail-scroll {
  scrollbar-gutter: stable;
}

.review-action-bar {
  position: relative;
  z-index: 1;
  flex: 0 0 auto;
  box-shadow: 0 -4px 12px rgb(15 23 42 / 0.04);
}

@media (max-width: 1180px) {
  .review-workspace {
    height: auto;
  }
}
</style>
