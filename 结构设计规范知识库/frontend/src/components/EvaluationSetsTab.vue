<template>
  <div class="space-y-5">
    <section v-if="viewMode === 'catalog'" class="panel overflow-hidden">
      <div class="border-b border-slate-200 p-5">
        <h2 class="panel-title">评估集管理</h2>
        <p class="muted mt-1">管理质量验证所使用的评估用例和已发布版本。选择一个评估集进入工作区。</p>
      </div>

      <div v-if="loading" class="p-10 text-center text-sm text-slate-500">正在读取评估集...</div>
      <div v-else-if="error && !sets.length" class="p-10 text-center text-sm text-rose-700" role="alert">{{ error }}</div>
      <div v-else class="divide-y divide-slate-200">
        <article v-for="item in sets" :key="item.evaluation_set_id" class="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-base font-semibold text-slate-900">{{ item.name }}</h3>
              <span class="status-pill" :class="item.draft ? 'status-pill-amber' : 'status-pill-green'">
                {{ item.draft ? '有未发布修改' : '已发布' }}
              </span>
            </div>
            <p class="mt-1 text-sm leading-6 text-slate-600">{{ setDescription(item.evaluation_set_id) }}</p>
            <div class="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
              <span><strong class="font-semibold text-slate-700">{{ item.case_count }}</strong> 条已发布用例</span>
              <span>当前版本：<strong class="font-semibold text-slate-700">{{ revisionLabel(item.published_revision) }}</strong></span>
              <span v-if="item.draft">编辑中：<strong class="font-semibold text-amber-700">{{ item.draft.case_count }} 条用例</strong></span>
              <span>更新于 {{ formatDate(item.updated_at || item.published_revision.published_at || item.published_revision.created_at) }}</span>
            </div>
          </div>
          <button class="btn shrink-0" :class="item.draft ? 'btn-primary' : ''" type="button" :disabled="busy" @click="openSet(item.evaluation_set_id)">
            {{ item.draft ? '继续编辑' : '打开' }}
          </button>
        </article>
        <div v-if="!sets.length" class="p-10 text-center text-sm text-slate-500">当前没有可管理的评估集。</div>
      </div>
    </section>

    <template v-else-if="detail && selectedSet">
      <section class="panel overflow-hidden">
        <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <button class="mb-3 text-sm text-blue-700 hover:text-blue-900" type="button" @click="backToCatalog">← 返回评估集管理</button>
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-xl font-semibold text-slate-950">{{ detail.name }}</h2>
              <span class="status-pill" :class="detail.draft ? 'status-pill-amber' : 'status-pill-green'">
                {{ detail.draft ? '有未发布修改' : '已发布' }}
              </span>
            </div>
            <p class="mt-1 text-sm leading-6 text-slate-600">{{ setDescription(detail.evaluation_set_id) }}</p>
            <div class="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
              <span>{{ detail.case_count }} 条已发布用例</span>
              <span>当前版本：{{ revisionLabel(detail.published_revision) }}</span>
              <span v-if="detail.draft" class="text-amber-700">编辑中，共 {{ detail.draft.case_count }} 条用例</span>
            </div>
          </div>
          <button class="btn" type="button" @click="emit('navigate', 'evaluation')">前往质量验证</button>
        </div>

        <nav class="flex overflow-x-auto border-b border-slate-200 px-5" role="tablist" aria-label="评估集工作区">
          <button
            v-for="tab in workspaceTabs"
            :key="tab.key"
            class="min-w-max border-b-2 px-4 py-3 text-sm font-medium"
            :class="activeWorkspaceTab === tab.key ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-800'"
            type="button"
            role="tab"
            :aria-selected="activeWorkspaceTab === tab.key"
            @click="setWorkspaceTab(tab.key)"
          >
            {{ tab.label }}
            <span v-if="tab.key === 'cases'" class="ml-1 text-xs text-slate-400">{{ workingCases.length }}</span>
          </button>
        </nav>
      </section>

      <section v-if="activeWorkspaceTab === 'cases'" class="panel overflow-hidden">
        <template v-if="caseEditorMode === 'list'">
          <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 p-5">
            <div>
              <h2 class="panel-title">用例</h2>
              <p class="muted mt-1">{{ detail.draft ? '当前显示未发布修改，保存后需要重新检查。' : '当前显示已发布内容；开始编辑后才能修改。' }}</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button v-if="!detail.draft" class="btn btn-primary" type="button" :disabled="busy" @click="createDraft(false)">开始编辑</button>
              <button v-else class="btn btn-primary" type="button" :disabled="busy" @click="beginCreateCase">新增用例</button>
            </div>
          </div>

          <div class="grid gap-3 border-b border-slate-200 bg-slate-50 p-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <input v-model="caseSearch" class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" type="search" placeholder="搜索用例 ID 或问题" aria-label="搜索评估用例" />
            <select v-model="caseTypeFilter" class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" aria-label="按评估类型筛选">
              <option value="">全部类型</option>
              <option v-for="type in availableCaseTypes" :key="type" :value="type">{{ caseTypeLabel(type) }}</option>
            </select>
          </div>

          <div class="flex min-h-[540px] flex-col">
            <ul v-if="pagedCases.length" class="divide-y divide-slate-200">
              <li v-for="item in pagedCases" :key="String(item.id)" class="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <strong class="break-all text-sm text-slate-900">{{ item.id || '未命名用例' }}</strong>
                    <span class="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{{ caseTypeLabel(String(item.type || '')) }}</span>
                  </div>
                  <p class="mt-1 text-sm leading-6 text-slate-700">{{ item.query || '未填写问题' }}</p>
                  <p class="mt-1 text-xs text-slate-500">{{ caseExpectationSummary(item) }}</p>
                </div>
                <button class="btn h-9 shrink-0 px-3 text-sm" type="button" @click="openCase(item)">{{ detail.draft ? '编辑' : '查看' }}</button>
              </li>
            </ul>
            <div v-else class="flex flex-1 items-center justify-center p-10 text-sm text-slate-500">没有符合当前条件的用例。</div>

            <div class="mt-auto flex items-center justify-between border-t border-slate-200 px-5 py-3">
              <button class="btn h-9 px-3 text-sm" type="button" :disabled="casePage <= 1" @click="casePage--">上一页</button>
              <span class="text-xs text-slate-500">第 {{ casePage }} / {{ casePageCount }} 页 · 共 {{ filteredCases.length }} 条</span>
              <button class="btn h-9 px-3 text-sm" type="button" :disabled="casePage >= casePageCount" @click="casePage++">下一页</button>
            </div>
          </div>
        </template>

        <template v-else-if="editingCase">
          <div class="border-b border-slate-200 p-5">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="panel-title">{{ caseEditorMode === 'create' ? '新增用例' : detail.draft ? '编辑用例' : '查看用例' }}</h2>
                <p class="muted mt-1">{{ editingCase.id || '尚未填写用例 ID' }}</p>
              </div>
              <span v-if="!detail.draft" class="status-pill status-pill-gray">已发布内容只读</span>
            </div>
          </div>
          <div class="p-5">
            <EvaluationCaseEditor
              :model-value="editingCase"
              :evaluation-set-id="selectedId"
              :mode="caseEditorMode"
              :read-only="!detail.draft"
              @save="saveEditedCase"
              @delete="deleteCase"
              @cancel="closeCaseEditor"
            />
          </div>
        </template>
      </section>

      <section v-else-if="activeWorkspaceTab === 'revisions'" class="panel overflow-hidden">
        <div class="border-b border-slate-200 p-5">
          <h2 class="panel-title">版本记录</h2>
          <p class="muted mt-1">每次发布都会保留一个历史版本。恢复历史版本时，系统会生成新的当前版本，不会覆盖原记录。</p>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[760px] text-left text-sm">
            <thead class="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th class="px-5 py-3">版本</th>
                <th class="px-4 py-3">状态</th>
                <th class="px-4 py-3">用例数</th>
                <th class="px-4 py-3">发布时间</th>
                <th class="px-4 py-3">发布者</th>
                <th class="px-5 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="revision in revisions" :key="revision.revision_id" class="border-t border-slate-100">
                <td class="px-5 py-4">
                  <div class="font-medium text-slate-900">{{ revisionLabel(revision) }}</div>
                  <details class="mt-1">
                    <summary class="cursor-pointer text-[11px] text-slate-400">查看内部追溯信息</summary>
                    <div class="mt-1 break-all font-mono text-[11px] text-slate-400">{{ revision.revision_id }} · {{ shortRevisionHash(revision) }}</div>
                  </details>
                </td>
                <td class="px-4 py-4"><span class="status-pill" :class="revision.revision_id === detail.published_revision.revision_id ? 'status-pill-green' : 'status-pill-gray'">{{ revision.revision_id === detail.published_revision.revision_id ? '当前版本' : '历史版本' }}</span></td>
                <td class="px-4 py-4 tabular-nums">{{ revision.case_count }}</td>
                <td class="px-4 py-4 text-slate-500">{{ formatDate(revision.published_at || revision.created_at) }}</td>
                <td class="px-4 py-4 text-slate-500">{{ revision.created_by }}</td>
                <td class="px-5 py-4 text-right">
                  <button class="btn h-9 px-3 text-sm" type="button" :disabled="busy || revision.revision_id === detail.published_revision.revision_id" @click="rollbackRevision(revision)">恢复为当前版本</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else class="panel overflow-hidden">
        <div class="border-b border-slate-200 p-5">
          <h2 class="panel-title">发布</h2>
          <p class="muted mt-1">检查未发布修改，确认后生成新的正式版本。</p>
        </div>

        <div class="grid border-b border-slate-200 bg-slate-50 md:grid-cols-3 md:divide-x md:divide-slate-200">
          <div class="p-5">
            <span class="text-xs text-slate-500">当前发布版本</span>
            <strong class="mt-1 block text-base text-slate-900">{{ revisionLabel(detail.published_revision) }}</strong>
            <span class="mt-1 block text-xs text-slate-500">{{ detail.case_count }} 条用例</span>
          </div>
          <div class="p-5">
            <span class="text-xs text-slate-500">未发布修改</span>
            <strong class="mt-1 block text-base" :class="detail.draft ? 'text-amber-700' : 'text-slate-400'">{{ detail.draft ? '有未发布修改' : '没有未发布修改' }}</strong>
            <span class="mt-1 block text-xs text-slate-500">{{ detail.draft ? `${detail.draft.case_count} 条待发布用例` : '当前无需发布' }}</span>
          </div>
          <div class="p-5">
            <span class="text-xs text-slate-500">发布检查</span>
            <strong class="mt-1 block text-base" :class="isValidated ? 'text-emerald-700' : detail.draft ? 'text-amber-700' : 'text-slate-400'">{{ validationLabel }}</strong>
            <span class="mt-1 block text-xs text-slate-500">{{ publishBlockedReason }}</span>
          </div>
        </div>

        <div v-if="!detail.draft" class="p-10 text-center">
          <h3 class="text-base font-semibold text-slate-900">当前没有未发布修改</h3>
          <p class="mt-2 text-sm text-slate-600">开始编辑后即可维护用例、检查修改并发布。</p>
          <button class="btn btn-primary mt-5" type="button" :disabled="busy" @click="createDraft(false)">开始编辑</button>
        </div>

        <div v-else class="divide-y divide-slate-200">
          <section class="p-5">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 class="text-sm font-semibold text-slate-900">未发布修改</h3>
                <p class="muted mt-1">相对当前发布版本的用例变化。</p>
              </div>
              <button class="btn" type="button" :disabled="busy" @click="loadDiff">{{ diff ? '刷新修改内容' : '查看修改内容' }}</button>
            </div>
            <div v-if="diff" class="mt-4 grid grid-cols-3 divide-x divide-slate-200 rounded-md border border-slate-200 bg-slate-50 text-center">
              <div class="p-4"><strong class="block text-xl text-emerald-700">{{ diff.added.length }}</strong><span class="text-xs text-slate-500">新增</span></div>
              <div class="p-4"><strong class="block text-xl text-amber-700">{{ diff.modified.length }}</strong><span class="text-xs text-slate-500">修改</span></div>
              <div class="p-4"><strong class="block text-xl text-rose-700">{{ diff.removed.length }}</strong><span class="text-xs text-slate-500">删除</span></div>
            </div>
            <p v-else class="mt-4 rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-600">尚未读取修改内容。</p>
          </section>

          <section class="p-5">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 class="text-sm font-semibold text-slate-900">发布检查</h3>
                <p class="muted mt-1">检查字段契约、用例 ID、最低数量和重复问题。</p>
              </div>
              <button class="btn" type="button" :disabled="busy" @click="validateDraft">{{ validation ? '重新检查' : '检查修改' }}</button>
            </div>
            <div v-if="validation" class="mt-4">
              <div class="flex items-center gap-2">
                <span class="status-pill" :class="validation.ok ? 'status-pill-green' : 'status-pill-red'">{{ validation.ok ? '检查通过' : '检查未通过' }}</span>
                <span class="text-sm text-slate-600">{{ validation.ok ? `${validation.case_count || draftCases.length} 条用例通过结构检查` : `${validation.errors?.length || 0} 个阻断问题` }}</span>
              </div>
              <div v-if="validation.errors?.length" class="mt-3 space-y-2">
                <p v-for="item in validation.errors" :key="item" class="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{{ item }}</p>
              </div>
              <div v-if="validation.warnings?.length" class="mt-3 space-y-2">
                <p v-for="item in validation.warnings" :key="item" class="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{{ item }}</p>
              </div>
            </div>
            <p v-else class="mt-4 rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-600">未发布修改尚未检查。</p>
          </section>

          <section class="flex flex-wrap items-center justify-between gap-4 bg-slate-50 p-5">
            <div>
              <h3 class="text-sm font-semibold text-slate-900">发布修改</h3>
              <p class="mt-1 text-sm leading-6 text-slate-600">{{ publishBlockedReason }} 发布后需要在质量验证中心重新运行 {{ reportTypeLabels[selectedId] }}。</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="btn" type="button" :disabled="busy" @click="createDraft(true)">放弃未发布修改</button>
              <button class="btn btn-primary" type="button" :disabled="busy || !isValidated || !diff" @click="publishDraft">发布修改</button>
            </div>
          </section>
        </div>
      </section>
    </template>

    <p v-if="message" class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{{ message }}</p>
    <p v-if="error && sets.length" class="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{{ error }}</p>

    <div v-if="confirmation" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" @keydown="trapConfirmationFocus">
      <section class="w-full max-w-lg rounded-lg border border-slate-200 bg-white shadow-xl" role="dialog" aria-modal="true" aria-labelledby="evaluation-confirmation-title" tabindex="-1">
        <div class="border-b border-slate-200 p-5">
          <h2 id="evaluation-confirmation-title" class="text-base font-semibold text-slate-900">{{ confirmation.title }}</h2>
          <p class="mt-2 text-sm leading-6 text-slate-600">{{ confirmation.message }}</p>
        </div>
        <div class="flex justify-end gap-2 p-4">
          <button ref="confirmCancelButton" class="btn" type="button" @click="cancelConfirmation">取消</button>
          <button ref="confirmPrimaryButton" class="btn btn-primary" type="button" @click="acceptConfirmation">{{ confirmation.confirmLabel }}</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  addAdminEvaluationCase,
  createAdminEvaluationDraft,
  deleteAdminEvaluationCase,
  getAdminEvaluationDiff,
  getAdminEvaluationSet,
  listAdminEvaluationRevisions,
  listAdminEvaluationSets,
  publishAdminEvaluationDraft,
  rollbackAdminEvaluationSet,
  updateAdminEvaluationCase,
  validateAdminEvaluationDraft,
} from '../admin-api'
import { errorMessage } from '../api'
import type {
  EvaluationDiffResponse,
  EvaluationPublishResponse,
  EvaluationRevisionSummary,
  EvaluationSetName,
  EvaluationSetResponse,
  EvaluationSetSummary,
  EvaluationSetsResponse,
  EvaluationValidationResponse,
} from '../contracts'
import EvaluationCaseEditor from './EvaluationCaseEditor.vue'

type JsonCase = Record<string, unknown>
type ValidationResult = EvaluationValidationResponse['validation'] & { ok?: boolean; errors?: string[]; warnings?: string[]; case_count?: number }
type WorkspaceTab = 'cases' | 'revisions' | 'release'
type CaseEditorMode = 'list' | 'edit' | 'create'

const emit = defineEmits<{ navigate: [tab: string] }>()

const workspaceTabs: ReadonlyArray<{ key: WorkspaceTab; label: string }> = [
  { key: 'cases', label: '用例' },
  { key: 'revisions', label: '版本记录' },
  { key: 'release', label: '发布' },
]
const reportTypeLabels: Record<string, string> = {
  regular: '常规检索评估',
  structured: '结构化专项评估',
  answer: '回答级盲测',
}
const CASE_PAGE_SIZE = 10

const sets = ref<EvaluationSetSummary[]>([])
const selectedId = ref<EvaluationSetName>('regular')
const detail = ref<EvaluationSetResponse | null>(null)
const revisions = ref<EvaluationRevisionSummary[]>([])
const draftCases = ref<JsonCase[]>([])
const validation = ref<ValidationResult | null>(null)
const diff = ref<EvaluationDiffResponse | null>(null)
const viewMode = ref<'catalog' | 'workspace'>('catalog')
const activeWorkspaceTab = ref<WorkspaceTab>('cases')
const caseEditorMode = ref<CaseEditorMode>('list')
const editingCase = ref<JsonCase | null>(null)
const editingCaseId = ref('')
const caseSearch = ref('')
const caseTypeFilter = ref('')
const casePage = ref(1)
const loading = ref(false)
const busy = ref(false)
const message = ref('')
const error = ref('')
const confirmation = ref<{
  title: string
  message: string
  confirmLabel: string
  action: () => Promise<void>
} | null>(null)
const confirmCancelButton = ref<HTMLButtonElement | null>(null)
const confirmPrimaryButton = ref<HTMLButtonElement | null>(null)
const confirmationRestoreFocus = ref<HTMLElement | null>(null)

const selectedSet = computed(() => sets.value.find(item => item.evaluation_set_id === selectedId.value) || null)
const workingCases = computed<JsonCase[]>(() => {
  if (!detail.value) return []
  return detail.value.draft ? draftCases.value : (detail.value.cases || []) as JsonCase[]
})
const filteredCases = computed(() => {
  const search = caseSearch.value.trim().toLocaleLowerCase('zh-CN')
  return workingCases.value.filter(item => {
    const matchesSearch = !search || `${String(item.id || '')} ${String(item.query || '')}`.toLocaleLowerCase('zh-CN').includes(search)
    const matchesType = !caseTypeFilter.value || String(item.type || '') === caseTypeFilter.value
    return matchesSearch && matchesType
  })
})
const casePageCount = computed(() => Math.max(1, Math.ceil(filteredCases.value.length / CASE_PAGE_SIZE)))
const pagedCases = computed(() => filteredCases.value.slice((casePage.value - 1) * CASE_PAGE_SIZE, casePage.value * CASE_PAGE_SIZE))
const availableCaseTypes = computed(() => Array.from(new Set(workingCases.value.map(item => String(item.type || '')).filter(Boolean))).sort())
const isValidated = computed(() => Boolean(validation.value?.ok && detail.value?.draft?.content_hash === validation.value?.content_hash))
const validationLabel = computed(() => {
  if (!detail.value?.draft) return '无需检查'
  if (!validation.value) return '尚未检查'
  return validation.value.ok ? '检查通过' : '检查未通过'
})
const publishBlockedReason = computed(() => {
  if (!detail.value?.draft) return '当前没有需要发布的修改。'
  if (!validation.value) return '需要先检查未发布修改。'
  if (!isValidated.value) return validation.value.ok ? '内容已变化，需要重新检查。' : '请先修复检查发现的问题。'
  if (!diff.value) return '需要先查看并确认修改内容。'
  return '发布检查已完成，可以发布。'
})

function setDescription(id: EvaluationSetName) {
  return ({
    regular: '验证规范检索、来源归属和条文引用能力。',
    structured: '验证复杂表、公式和结构化知识的检索能力。',
    answer: '验证最终问答、引用截图和无依据拒答行为。',
  })[id]
}

function caseTypeLabel(type: string) {
  return ({
    clause: '条文查询', table: '表格取值', definition: '定义', classification: '分类', general: '一般检索', alias: '别名', code: '规范编号', multi_spec: '多规范', formula: '公式', structured_table: '复杂表格', direct_value: '直接数值', boundary: '适用边界', false_premise: '错误前提', no_evidence: '无依据拒答',
  } as Record<string, string>)[type] || type || '未分类'
}

function caseExpectationSummary(item: JsonCase) {
  if (selectedId.value === 'answer') {
    const citations = Array.isArray(item.expected_citations) ? item.expected_citations.map(String) : []
    const expected = Array.isArray(item.expected_all) ? item.expected_all.map(String) : []
    return [...citations, ...expected].slice(0, 4).join(' · ') || '未设置回答期望'
  }
  if (selectedId.value === 'structured') return item.expected_table_id ? `期望表格 ${String(item.expected_table_id)}` : '未设置期望表格'
  const sources = Array.isArray(item.expected_sources) ? item.expected_sources.map(String) : []
  return [...sources.slice(0, 2), item.expected_clause ? `条文 ${String(item.expected_clause)}` : ''].filter(Boolean).join(' · ') || '未设置检索期望'
}

function revisionLabel(revision: EvaluationRevisionSummary) {
  if (revision.source === 'builtin') return '内置基线'
  const publishedAt = revision.published_at || revision.created_at
  return publishedAt ? `版本 ${publishedAt.slice(0, 10)}` : '托管版本'
}

function shortRevisionHash(revision: EvaluationRevisionSummary) {
  const hash = String(revision.content_hash || '').trim()
  return hash ? hash.slice(0, 12) : '无'
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '未记录'
}

function defaultCase(): JsonCase {
  if (selectedId.value === 'answer') {
    return { id: '', query: '', type: 'direct_value', expected_all: [], expected_any_groups: [], forbidden_terms: [], expected_citations: [], expected_unit_groups: [], requires_refusal: false, requires_image: true }
  }
  if (selectedId.value === 'structured') return { id: '', query: '', type: 'structured_table', expected_table_id: '', keyword_required: false, top1_source_required: false }
  return { id: '', query: '', type: 'general', expected_sources: [], expected_clause: '', expected_keywords: [], top1_source_required: true, keyword_required: true }
}

async function loadSets(preferredId = selectedId.value) {
  const response = await listAdminEvaluationSets({}) as EvaluationSetsResponse
  sets.value = response.sets || []
  if (!sets.value.some(item => item.evaluation_set_id === preferredId)) selectedId.value = sets.value[0]?.evaluation_set_id || 'regular'
  else selectedId.value = preferredId
}

async function loadDetail() {
  detail.value = await getAdminEvaluationSet({ path: { evaluation_set_id: selectedId.value } }) as EvaluationSetResponse
  draftCases.value = (detail.value.draft_cases || []) as JsonCase[]
  validation.value = detail.value.draft?.validation_summary as ValidationResult | null || null
  // Validation refreshes metadata without changing the reviewed content.
  if (diff.value && (
    diff.value.evaluation_set_id !== detail.value.evaluation_set_id ||
    diff.value.base_revision_id !== detail.value.published_revision.revision_id ||
    diff.value.draft_content_hash !== detail.value.draft?.content_hash
  )) diff.value = null
}

async function loadRevisions() {
  const response = await listAdminEvaluationRevisions({ path: { evaluation_set_id: selectedId.value } })
  revisions.value = response.revisions || []
}

async function loadWorkspace() {
  await Promise.all([loadDetail(), loadRevisions()])
  casePage.value = 1
  caseEditorMode.value = 'list'
  editingCase.value = null
}

async function refresh() {
  if (busy.value) return
  loading.value = true
  error.value = ''
  try {
    await loadSets()
    if (viewMode.value === 'workspace') await loadWorkspace()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

async function openSet(id: EvaluationSetName) {
  if (busy.value) return
  selectedId.value = id
  viewMode.value = 'workspace'
  activeWorkspaceTab.value = 'cases'
  message.value = ''
  error.value = ''
  loading.value = true
  try {
    await loadWorkspace()
  } catch (cause) {
    error.value = errorMessage(cause)
    viewMode.value = 'catalog'
  } finally {
    loading.value = false
  }
}

function backToCatalog() {
  viewMode.value = 'catalog'
  activeWorkspaceTab.value = 'cases'
  closeCaseEditor()
  message.value = ''
  error.value = ''
}

function setWorkspaceTab(tab: WorkspaceTab) {
  activeWorkspaceTab.value = tab
  closeCaseEditor()
}

function openCase(item: JsonCase) {
  editingCaseId.value = String(item.id || '')
  editingCase.value = { ...item }
  caseEditorMode.value = 'edit'
}

function beginCreateCase() {
  editingCaseId.value = ''
  editingCase.value = defaultCase()
  caseEditorMode.value = 'create'
}

function closeCaseEditor() {
  caseEditorMode.value = 'list'
  editingCase.value = null
  editingCaseId.value = ''
}

async function runMutation(action: () => Promise<unknown>, successMessage: string) {
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    const result = await action()
    message.value = successMessage
    await Promise.all([loadSets(selectedId.value), loadDetail(), loadRevisions()])
    return result
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function requestConfirmation(nextConfirmation: NonNullable<typeof confirmation.value>) {
  confirmationRestoreFocus.value = document.activeElement instanceof HTMLElement ? document.activeElement : null
  confirmation.value = nextConfirmation
  void nextTick(() => confirmCancelButton.value?.focus())
}

function cancelConfirmation() {
  confirmation.value = null
  void nextTick(() => confirmationRestoreFocus.value?.focus())
}

async function acceptConfirmation() {
  const pending = confirmation.value
  if (!pending) return
  confirmation.value = null
  await pending.action()
  void nextTick(() => confirmationRestoreFocus.value?.focus())
}

function trapConfirmationFocus(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    cancelConfirmation()
    return
  }
  if (event.key !== 'Tab') return
  const focusable = [confirmCancelButton.value, confirmPrimaryButton.value].filter((element): element is HTMLButtonElement => Boolean(element))
  if (!focusable.length) return
  const currentIndex = focusable.indexOf(document.activeElement as HTMLButtonElement)
  const nextIndex = event.shiftKey ? (currentIndex <= 0 ? focusable.length - 1 : currentIndex - 1) : (currentIndex === focusable.length - 1 ? 0 : currentIndex + 1)
  event.preventDefault()
  focusable[nextIndex]?.focus()
}

async function createDraft(reset: boolean) {
  const action = async () => {
    await runMutation(
      () => createAdminEvaluationDraft({ path: { evaluation_set_id: selectedId.value }, body: reset ? { reset: true } : undefined }),
      reset ? '未发布修改已放弃。' : '已进入编辑状态，可以开始修改用例。',
    )
    activeWorkspaceTab.value = 'cases'
    closeCaseEditor()
  }
  if (reset) {
    requestConfirmation({
      title: '放弃未发布修改',
      message: '当前未发布修改将被丢弃，并恢复到当前发布版本。是否继续？',
      confirmLabel: '确认放弃',
      action,
    })
    return
  }
  await action()
}

async function saveEditedCase(value: JsonCase) {
  if (!detail.value?.draft) return
  if (caseEditorMode.value === 'create') {
    await runMutation(
      () => addAdminEvaluationCase({ path: { evaluation_set_id: selectedId.value }, body: { case: value } }),
      '用例已新增，请在发布页重新检查修改。',
    )
  } else {
    await runMutation(
      () => updateAdminEvaluationCase({ path: { evaluation_set_id: selectedId.value, case_id: editingCaseId.value }, body: { case: value } }),
      '用例已保存，请在发布页重新检查修改。',
    )
  }
  if (!error.value) closeCaseEditor()
}

function deleteCase() {
  const caseId = editingCaseId.value
  if (!caseId) return
  requestConfirmation({
    title: '删除评估用例',
    message: `确认从未发布修改中删除用例“${caseId}”？删除后需要重新检查修改。`,
    confirmLabel: '确认删除',
    action: async () => {
      await runMutation(
        () => deleteAdminEvaluationCase({ path: { evaluation_set_id: selectedId.value, case_id: caseId } }),
        '用例已从未发布修改中删除，请在发布页重新检查修改。',
      )
      if (!error.value) closeCaseEditor()
    },
  })
}

async function validateDraft() {
  await runMutation(
    () => validateAdminEvaluationDraft({ path: { evaluation_set_id: selectedId.value } }),
    '修改检查已完成。',
  )
}

async function loadDiff() {
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    diff.value = await getAdminEvaluationDiff({ path: { evaluation_set_id: selectedId.value } }) as EvaluationDiffResponse
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function publishDraft() {
  requestConfirmation({
    title: '发布评估集修改',
    message: '发布后，当前未发布修改会成为新的正式版本，原有版本记录会保留，相关旧评估证据将待更新。是否继续？',
    confirmLabel: '确认发布',
    action: async () => {
      const result = await runMutation(
        () => publishAdminEvaluationDraft({ path: { evaluation_set_id: selectedId.value } }),
        '评估集修改已发布。',
      ) as EvaluationPublishResponse | undefined
      if (result?.affected_report_types?.length) message.value = `评估集修改已发布。请在质量验证中心重新运行 ${result.affected_report_types.map(type => reportTypeLabels[type] || type).join('、')}。`
    },
  })
}

function rollbackRevision(revision: EvaluationRevisionSummary) {
  requestConfirmation({
    title: '恢复历史版本',
    message: `确认把“${revisionLabel(revision)}”恢复为当前版本？原有版本记录不会被覆盖。`,
    confirmLabel: '确认恢复',
    action: async () => {
      const result = await runMutation(
        () => rollbackAdminEvaluationSet({ path: { evaluation_set_id: selectedId.value }, body: { revision_id: revision.revision_id } }),
        '历史版本已恢复，并生成了新的发布版本。',
      ) as EvaluationPublishResponse | undefined
      if (result?.affected_report_types?.length) message.value = `历史版本已恢复。请在质量验证中心重新运行 ${result.affected_report_types.map(type => reportTypeLabels[type] || type).join('、')}。`
    },
  })
}

function onPageAction(event: Event) {
  const action = event instanceof CustomEvent ? event.detail : null
  if (action?.key === 'evaluationSets') refresh()
}

watch([caseSearch, caseTypeFilter], () => { casePage.value = 1 })
watch(casePageCount, count => { if (casePage.value > count) casePage.value = count })

onMounted(() => {
  window.addEventListener('admin-page-action', onPageAction)
  refresh()
})
onBeforeUnmount(() => window.removeEventListener('admin-page-action', onPageAction))
</script>
