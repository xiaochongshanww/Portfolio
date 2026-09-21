<template>
  <div class="space-y-4">
    <input ref="uploadInput" class="sr-only" type="file" accept="application/pdf,.pdf" :disabled="busy" @change="handleUpload">
    <section class="panel overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">规范来源目录</h2>
          <p class="muted mt-1">{{ catalog.source_count }} 份来源 · {{ catalog.pending_count }} 项待应用 · 目录修订 {{ catalog.catalog_revision }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button v-if="catalog.source_count === 0" class="btn" :disabled="busy" @click="bootstrapLegacy">导入现有规范</button>
          <button class="btn" :disabled="busy" @click="loadSources()">刷新</button>
          <button class="btn btn-primary" :disabled="busy || !catalog.pending_count" @click="openPlan">确认变更</button>
        </div>
      </div>
      <div class="grid divide-y divide-slate-200 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        <div class="p-4"><div class="muted">来源总数</div><div class="mt-1 text-2xl font-semibold">{{ catalog.source_count }}</div></div>
        <div class="p-4"><div class="muted">已上线</div><div class="mt-1 text-2xl font-semibold">{{ statusCount('active') }}</div></div>
        <div class="p-4"><div class="muted">待应用变更</div><div class="mt-1 text-2xl font-semibold">{{ catalog.pending_count }}</div></div>
        <div class="p-4"><div class="muted">活动来源修订</div><div class="mt-2 truncate text-sm font-medium">{{ catalog.active_revision_id || '尚未登记' }}</div></div>
      </div>
    </section>

    <div class="grid min-h-[620px] gap-4 2xl:grid-cols-[minmax(640px,1.45fr)_minmax(420px,1fr)]">
      <section class="panel min-w-0 overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
          <div>
            <h2 class="panel-title">来源清单</h2>
            <p class="muted mt-1">选择一项查看资产版本与治理信息</p>
          </div>
          <select v-model="filter" class="field" aria-label="筛选来源状态">
            <option value="">全部状态</option>
            <option value="pending">有待应用变更</option>
            <option value="active">已上线</option>
            <option value="draft">草稿</option>
            <option value="retired">已下架</option>
          </select>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[760px] text-left text-sm">
            <thead class="bg-slate-50 text-xs text-slate-500">
              <tr><th class="px-4 py-3">规范</th><th class="px-4 py-3">状态</th><th class="px-4 py-3">当前资产</th><th class="px-4 py-3">页数</th><th class="px-4 py-3">更新时间</th></tr>
            </thead>
            <tbody>
              <tr
                v-for="source in filteredSources"
                :key="source.source_id"
                class="cursor-pointer border-t border-slate-100 transition hover:bg-slate-50"
                :class="selectedId === source.source_id ? 'bg-blue-50' : ''"
                :aria-selected="selectedId === source.source_id"
                :tabindex="0"
                @click="selectSource(source.source_id)"
                @keydown.enter.prevent="selectSource(source.source_id)"
                @keydown.space.prevent="selectSource(source.source_id)"
              >
                <td class="px-4 py-3">
                  <div class="font-medium">{{ source.metadata.code || '待补编号' }} {{ source.metadata.name || '' }}</div>
                  <div class="mt-1 max-w-[340px] truncate text-xs text-slate-500">{{ source.metadata.source_file }}</div>
                </td>
                <td class="px-4 py-3"><span :class="statusClass(source)">{{ statusLabel(source) }}</span></td>
                <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ shortHash(selectedVersion(source)?.sha256) }}</td>
                <td class="px-4 py-3 tabular-nums">{{ selectedVersion(source)?.page_count ?? '-' }}</td>
                <td class="px-4 py-3 text-xs text-slate-500">{{ formatDate(source.updated_at) }}</td>
              </tr>
              <tr v-if="!filteredSources.length"><td colspan="5" class="px-4 py-16 text-center text-slate-500">暂无符合条件的规范来源。</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel min-w-0 overflow-hidden">
        <template v-if="selected">
          <div class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 p-4">
            <div class="min-w-0">
              <h2 class="truncate text-sm font-semibold">{{ selected.metadata.code || '待补编号' }} {{ selected.metadata.name || '' }}</h2>
              <p class="muted mt-1">{{ selected.source_id }}</p>
            </div>
            <span :class="statusClass(selected)">{{ statusLabel(selected) }}</span>
          </div>

          <form class="space-y-5 p-4" @submit.prevent="saveSelected">
            <fieldset class="grid gap-3 sm:grid-cols-2">
              <legend class="mb-3 text-sm font-semibold text-slate-800">规范元数据</legend>
              <label class="text-xs text-slate-600">规范编号<input v-model="form.metadata.code" class="field mt-1 w-full" required></label>
              <label class="text-xs text-slate-600">规范名称<input v-model="form.metadata.name" class="field mt-1 w-full" required></label>
              <label class="text-xs text-slate-600">版本<input v-model="form.metadata.version" class="field mt-1 w-full"></label>
              <label class="text-xs text-slate-600">实施日期<input v-model="form.metadata.effective_date" class="field mt-1 w-full" type="date"></label>
              <label class="text-xs text-slate-600 sm:col-span-2">别名（逗号分隔）<input v-model="aliasesText" class="field mt-1 w-full"></label>
              <label class="text-xs text-slate-600 sm:col-span-2">备注<textarea v-model="form.metadata.notes" class="min-h-20 w-full rounded-md border border-slate-300 p-3 text-sm outline-none focus:border-blue-500"></textarea></label>
            </fieldset>

            <fieldset class="grid gap-3 sm:grid-cols-2">
              <legend class="mb-3 text-sm font-semibold text-slate-800">来源与使用边界</legend>
              <label class="text-xs text-slate-600">来源类型<select v-model="form.governance.source_kind" class="field mt-1 w-full"><option value="user_upload">用户上传</option><option value="official_release">官方发布</option><option value="licensed_copy">授权副本</option></select></label>
              <label class="text-xs text-slate-600">权利状态<select v-model="form.governance.rights_status" class="field mt-1 w-full"><option value="A">A · 可分发</option><option value="B">B · 仅内部使用</option><option value="C">C · 禁止使用</option><option value="unknown">待确认</option></select></label>
              <label class="text-xs text-slate-600 sm:col-span-2">来源索引/凭证<input v-model="form.governance.reference_index" class="field mt-1 w-full"></label>
              <label class="text-xs text-slate-600">页面截图访问<select v-model="form.metadata.page_image_access" class="field mt-1 w-full"><option value="disabled">禁用</option><option value="authenticated">仅认证用户</option><option value="public">公开</option></select></label>
              <label class="text-xs text-slate-600">内容图片访问<select v-model="form.metadata.image_access" class="field mt-1 w-full"><option value="disabled">禁用</option><option value="authenticated">仅认证用户</option><option value="public">公开</option></select></label>
            </fieldset>

            <div class="border-t border-slate-200 pt-4">
              <div class="flex items-center justify-between"><h3 class="text-sm font-semibold">资产版本</h3><span class="muted">{{ selected.versions.length }} 个</span></div>
              <div class="mt-3 max-h-40 overflow-auto border border-slate-200">
                <div v-for="version in [...selected.versions].reverse()" :key="version.asset_version_id" class="border-b border-slate-100 px-3 py-2 text-xs last:border-0">
                  <div class="flex justify-between gap-3"><span class="truncate font-medium">{{ version.original_filename }}</span><span>{{ version.page_count }} 页</span></div>
                  <div class="mt-1 truncate font-mono text-slate-500">{{ version.sha256 }}</div>
                </div>
              </div>
            </div>

            <div class="flex flex-wrap gap-2 border-t border-slate-200 pt-4">
              <button class="btn btn-primary" type="submit" :disabled="busy">保存元数据</button>
              <button class="btn" type="button" :disabled="busy" @click="validateSelected">重新校验</button>
              <label class="btn cursor-pointer" :class="busy || selected.pending_action ? 'pointer-events-none opacity-50' : ''">替换 PDF<input class="sr-only" type="file" accept="application/pdf,.pdf" @change="handleReplace"></label>
              <button v-if="selected.active_asset_version_id && !selected.pending_action" class="btn btn-danger" type="button" :disabled="busy" @click="retireSelected">下架</button>
              <button v-if="selected.pending_action" class="btn" type="button" :disabled="busy" @click="discardSelected">撤销待应用变更</button>
              <button v-if="!selected.active_asset_version_id" class="btn btn-danger" type="button" :disabled="busy" @click="deleteSelected">删除草稿</button>
            </div>
          </form>
        </template>
        <div v-else class="flex min-h-[620px] items-center justify-center p-8 text-sm text-slate-500">从左侧选择规范来源，或上传新的 PDF。</div>
      </section>
    </div>

    <div v-if="plan" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/60 p-4" role="dialog" aria-modal="true">
      <section class="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-200 p-4"><h2 class="font-semibold">确认来源变更</h2><button class="btn" @click="plan = null">关闭</button></div>
        <div class="space-y-4 p-5">
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div class="bg-emerald-50 p-3 text-sm">新增 <strong>{{ plan.changes.added.length }}</strong></div>
            <div class="bg-cyan-50 p-3 text-sm">元数据 <strong>{{ plan.changes.updated?.length ?? 0 }}</strong></div>
            <div class="bg-blue-50 p-3 text-sm">替换 <strong>{{ plan.changes.replaced.length }}</strong></div>
            <div class="bg-rose-50 p-3 text-sm">下架 <strong>{{ plan.changes.retired.length }}</strong></div>
            <div class="bg-slate-50 p-3 text-sm">保持 <strong>{{ plan.changes.unchanged.length }}</strong></div>
          </div>
          <div v-if="plan.blockers.length" class="rounded-md bg-rose-50 p-3 text-sm text-rose-700"><div v-for="item in plan.blockers" :key="item.source_id">{{ item.source_id }}：{{ item.message }}</div></div>
          <p class="text-sm text-slate-600">确认后会固化不可变来源快照并提交候选知识库构建。只有检索与结构化门禁通过后才会切换在线版本。</p>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-xs text-slate-600">解析器<select v-model="buildOptions.parser_backend" class="field mt-1 w-full"><option value="mineru">MinerU</option><option value="pymupdf">PyMuPDF</option></select></label>
            <label class="text-xs text-slate-600">构建模式<select v-model="buildOptions.mode" class="field mt-1 w-full"><option value="incremental">增量候选</option><option value="full">全量候选</option></select></label>
          </div>
          <label class="flex items-center gap-2 text-sm"><input v-model="confirmed" type="checkbox"> 已核对新增、替换和下架范围</label>
        </div>
        <div class="flex justify-end gap-2 border-t border-slate-200 p-4"><button class="btn" @click="plan = null">取消</button><button class="btn btn-primary" :disabled="busy || !plan.ready || !confirmed" @click="submitBuild">提交候选构建</button></div>
      </section>
    </div>

    <p v-if="message" class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{{ message }}</p>
    <p v-if="error" class="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { errorMessage } from '../api'
import {
  bootstrapSources,
  buildSourceChanges,
  deleteDraftSource,
  discardPendingSource,
  listSources,
  planSourceChanges,
  replaceSource,
  retireSource,
  updateSource,
  uploadSource,
  validateSource,
  type SourceList,
  type SourceGovernance,
  type SourceMetadata,
  type SourcePlan,
  type SourceRecord,
} from '../source-api'

const emit = defineEmits<{ refreshJobs: [] }>()
const emptyCatalog = (): SourceList => ({ catalog_revision: 0, active_revision_id: '', source_count: 0, pending_count: 0, sources: [] })
const catalog = ref<SourceList>(emptyCatalog())
const selectedId = ref('')
const filter = ref('')
const busy = ref(false)
const message = ref('')
const error = ref('')
const plan = ref<SourcePlan | null>(null)
const confirmed = ref(false)
const aliasesText = ref('')
const uploadInput = ref<HTMLInputElement | null>(null)
const form = reactive({ metadata: {} as SourceMetadata, governance: {} as SourceGovernance })
const buildOptions = reactive({ parser_backend: 'mineru', apply_corrections: true, mode: 'incremental' })

const selected = computed(() => catalog.value.sources.find(item => item.source_id === selectedId.value) || null)
const filteredSources = computed(() => catalog.value.sources.filter((source) => {
  if (filter.value === 'pending') return Boolean(source.pending_action)
  if (filter.value) return source.lifecycle_status === filter.value
  return true
}))

function selectSource(sourceId: string) {
  selectedId.value = sourceId
  const source = catalog.value.sources.find(item => item.source_id === sourceId)
  if (!source) return
  Object.assign(form.metadata, JSON.parse(JSON.stringify(source.metadata)))
  Object.assign(form.governance, JSON.parse(JSON.stringify(source.governance)))
  aliasesText.value = Array.isArray(source.metadata.aliases) ? source.metadata.aliases.join('，') : ''
}

async function run(action: () => Promise<unknown>, success = '') {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await action()
    if (success) message.value = success
    await loadSources(false)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function loadSources(resetBusy = true) {
  if (resetBusy) busy.value = true
  try {
    catalog.value = await listSources()
    if (selectedId.value && !catalog.value.sources.some(item => item.source_id === selectedId.value)) selectedId.value = ''
    if (!selectedId.value && catalog.value.sources.length) selectSource(catalog.value.sources[0].source_id)
    else if (selectedId.value) selectSource(selectedId.value)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    if (resetBusy) busy.value = false
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  await run(async () => { const result = await uploadSource(file); selectedId.value = result.source.source_id }, 'PDF 已安全上传，请核对并补充元数据。')
  input.value = ''
}

async function handleReplace(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !selected.value) return
  await run(() => replaceSource(selected.value!.source_id, file), '替换版本已登记，旧在线版本未受影响。')
  input.value = ''
}

function saveSelected() {
  if (!selected.value) return
  form.metadata.aliases = aliasesText.value.split(/[，,]/).map(value => value.trim()).filter(Boolean)
  const payload = JSON.parse(JSON.stringify({ metadata: form.metadata, governance: form.governance }))
  return run(() => updateSource(selected.value!.source_id, payload), '元数据已保存。')
}

function validateSelected() { if (selected.value) return run(() => validateSource(selected.value!.source_id), 'PDF 与哈希校验通过。') }
function bootstrapLegacy() { return run(() => bootstrapSources(), '现有 data/raw 规范已登记为来源基线。') }
function discardSelected() { if (selected.value && confirm('撤销这项尚未上线的变更？')) return run(() => discardPendingSource(selected.value!.source_id), '待应用变更已撤销。') }
function deleteSelected() { if (selected.value && confirm('删除此草稿登记？此操作不会删除仍被其他记录引用的内容对象。')) return run(() => deleteDraftSource(selected.value!.source_id), '草稿已删除。') }
function retireSelected() { if (selected.value && confirm('将此规范加入下架计划？在线版本会保持不变，直至候选构建通过门禁。')) return run(() => retireSource(selected.value!.source_id), '已加入待下架变更。') }

async function openPlan() {
  busy.value = true; error.value = ''; confirmed.value = false
  try { plan.value = await planSourceChanges() } catch (err) { error.value = errorMessage(err) } finally { busy.value = false }
}

async function submitBuild() {
  if (!plan.value?.ready || !confirmed.value) return
  await run(async () => {
    const result = await buildSourceChanges(buildOptions)
    message.value = `候选构建已提交：${String(result.job.job_id || '')}`
    plan.value = null
    emit('refreshJobs')
  })
}

function selectedVersion(source: SourceRecord) { const id = source.pending_asset_version_id || source.active_asset_version_id; return source.versions.find(item => item.asset_version_id === id) }
function shortHash(value?: string) { return value ? value.slice(0, 12) : '-' }
function statusLabel(source: SourceRecord) { if (source.pending_action === 'add') return '待新增'; if (source.pending_action === 'update') return '待更新'; if (source.pending_action === 'replace') return '待替换'; if (source.pending_action === 'retire') return '待下架'; return ({ active: '已上线', ready: '待应用', draft: '草稿', retired: '已下架' } as Record<string, string>)[source.lifecycle_status] || source.lifecycle_status }
function statusClass(source: SourceRecord) { const base = 'rounded px-2 py-1 text-xs font-semibold'; if (source.pending_action) return `${base} bg-amber-100 text-amber-800`; if (source.lifecycle_status === 'active') return `${base} bg-emerald-100 text-emerald-700`; if (source.lifecycle_status === 'retired') return `${base} bg-slate-200 text-slate-600`; return `${base} bg-blue-100 text-blue-700` }
function statusCount(status: string) { return catalog.value.sources.filter(item => item.lifecycle_status === status).length }
function formatDate(value?: string) { if (!value) return '-'; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false }) }

function handlePageAction(event: Event) {
  const detail = (event as CustomEvent<{ key?: string }>).detail
  if (detail?.key === 'sources') uploadInput.value?.click()
}

onMounted(() => {
  loadSources()
  window.addEventListener('admin-page-action', handlePageAction)
})
onBeforeUnmount(() => window.removeEventListener('admin-page-action', handlePageAction))
</script>
