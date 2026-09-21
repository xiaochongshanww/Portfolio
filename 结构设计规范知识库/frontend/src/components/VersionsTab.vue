<template>
  <div class="space-y-5">
    <section class="panel overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">知识版本</h2>
          <p class="muted mt-1">{{ inventory.active_version_id ? `活动版本 ${inventory.active_version_label || inventory.active_version_id}` : '未识别活动版本' }}</p>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-primary" :disabled="busy" @click="createPlan">生成清理计划</button>
        </div>
      </div>

      <div class="grid divide-y divide-slate-200 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        <div class="p-4">
          <div class="text-xs text-slate-500">版本数</div>
          <div class="mt-1 text-2xl font-semibold">{{ inventory.version_count ?? '-' }}</div>
        </div>
        <div class="p-4">
          <div class="text-xs text-slate-500">总占用</div>
          <div class="mt-1 text-2xl font-semibold">{{ formatBytes(inventory.total_bytes) }}</div>
        </div>
        <div class="p-4">
          <div class="text-xs text-slate-500">可清理</div>
          <div class="mt-1 text-2xl font-semibold">{{ inventory.cleanup_candidate_count ?? '-' }}</div>
        </div>
        <div class="p-4">
          <div class="text-xs text-slate-500">预计释放</div>
          <div class="mt-1 text-2xl font-semibold">{{ formatBytes(inventory.cleanup_candidate_bytes) }}</div>
        </div>
      </div>

      <div v-if="inventory.policy" class="grid gap-x-6 gap-y-2 border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm md:grid-cols-3">
        <div><span class="text-slate-500">回滚保留</span><span class="ml-2 font-medium">{{ inventory.policy.keep_recent_passed }} 个</span></div>
        <div><span class="text-slate-500">成功版本期限</span><span class="ml-2 font-medium">{{ inventory.policy.success_max_age_days }} 天</span></div>
        <div><span class="text-slate-500">失败版本期限</span><span class="ml-2 font-medium">{{ inventory.policy.failed_max_age_days }} 天</span></div>
        <div><span class="text-slate-500">最短保护</span><span class="ml-2 font-medium">{{ inventory.policy.minimum_age_hours }} 小时</span></div>
        <div><span class="text-slate-500">高水位</span><span class="ml-2 font-medium">{{ formatBytes(inventory.policy.high_watermark_bytes) }}</span></div>
        <div><span class="text-slate-500">低水位</span><span class="ml-2 font-medium">{{ formatBytes(inventory.policy.low_watermark_bytes) }}</span></div>
      </div>
    </section>

    <section v-if="plan" class="panel overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">待确认清理计划</h2>
          <p class="muted mt-1">{{ plan.plan_id }} · {{ plan.candidate_count }} 个版本 · {{ formatBytes(plan.candidate_bytes) }}</p>
        </div>
        <span class="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">{{ formatExpiry(plan.expires_at) }}</span>
      </div>

      <div v-if="plan.candidates?.length" class="overflow-x-auto">
        <table class="w-full min-w-[760px] text-left text-sm">
          <thead class="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th class="px-4 py-3">版本</th>
              <th class="px-4 py-3">原因</th>
              <th class="px-4 py-3">最后变化</th>
              <th class="px-4 py-3 text-right">占用</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in plan.candidates" :key="item.version_id" class="border-t border-slate-100">
              <td class="px-4 py-3">
                <div class="font-medium">{{ item.version_label || item.version_id }}</div>
                <div class="mt-1 font-mono text-xs text-slate-500">内部 ID：{{ item.version_id }}</div>
              </td>
              <td class="px-4 py-3">{{ cleanupReason(item.reason) }}</td>
              <td class="px-4 py-3 text-slate-500">{{ formatDate(item.modified_at) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ formatBytes(item.size_bytes) }}</td>
            </tr>
          </tbody>
        </table>
        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 p-4">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="planConfirmed" type="checkbox" class="h-4 w-4 rounded border-slate-300">
            已核对版本、原因和预计释放空间
          </label>
          <button class="btn bg-red-600 text-white hover:bg-red-700" :disabled="busy || !planConfirmed" @click="executePlan">
            执行此计划
          </button>
        </div>
      </div>
      <div v-else class="p-8 text-center text-sm text-slate-500">当前策略下没有可清理版本。</div>
    </section>

    <section class="panel overflow-hidden">
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <div class="flex items-baseline gap-2">
            <h2 class="panel-title">版本清单</h2>
            <span class="muted text-xs">{{ matchedVersionCount }} / {{ inventory.version_count ?? 0 }} 个</span>
          </div>
          <p class="muted mt-1 text-xs">活动版本、运行版本和受保护版本不会进入清理计划。</p>
        </div>
        <div class="flex flex-wrap items-end gap-2">
          <label class="text-xs text-slate-600">
            搜索版本
            <input v-model.trim="versionQuery" class="field mt-1 h-9 w-48" type="search" placeholder="版本名称、内部 ID或错误信息">
          </label>
          <label class="text-xs text-slate-600">
            状态
            <select v-model="versionState" class="field mt-1 h-9 w-36" aria-label="筛选版本状态">
              <option value="all">全部状态</option>
              <option value="active">活动</option>
              <option value="running">构建中</option>
              <option value="passed">门禁通过</option>
              <option value="failed_gate">门禁失败</option>
              <option value="invalid_gate">门禁记录异常</option>
              <option value="legacy_complete">旧版完整</option>
              <option value="incomplete">不完整</option>
              <option value="unsafe">路径异常</option>
            </select>
          </label>
          <label class="text-xs text-slate-600">
            范围
            <select v-model="versionScope" class="field mt-1 h-9 w-32" aria-label="筛选版本范围">
              <option value="all">全部版本</option>
              <option value="cleanup">可清理</option>
              <option value="protected">受保护</option>
              <option value="pinned">人工固定</option>
            </select>
          </label>
          <label class="text-xs text-slate-600">
            每页
            <select v-model.number="versionPageSize" class="field mt-1 h-9 w-24" aria-label="每页版本数">
              <option :value="10">10 个</option>
              <option :value="20">20 个</option>
              <option :value="50">50 个</option>
            </select>
          </label>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[980px] text-left text-sm">
          <thead class="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th class="px-4 py-3">版本</th>
              <th class="px-4 py-3">状态</th>
              <th class="px-4 py-3">保护原因</th>
              <th class="px-4 py-3">最后变化</th>
              <th class="px-4 py-3 text-right">文件</th>
              <th class="px-4 py-3 text-right">占用</th>
              <th class="px-4 py-3 text-center">人工固定</th>
              <th class="px-4 py-3 text-center">详情</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in paginatedVersions"
              :key="item.version_id"
              class="border-t border-slate-100"
              :class="item.version_id === inventory.active_version_id ? 'bg-blue-50/60' : ''"
            >
              <td class="px-4 py-3">
                <button type="button" class="text-left font-medium text-blue-700 hover:underline" @click="openVersion(item)">
                  {{ item.version_label || item.version_id }}
                </button>
                <div class="mt-1 font-mono text-xs text-slate-500">内部 ID：{{ item.version_id }}</div>
                <div v-if="item.scan_error" class="mt-1 max-w-[360px] truncate text-xs text-red-600" :title="item.scan_error">{{ item.scan_error }}</div>
              </td>
              <td class="px-4 py-3"><span :class="stateClass(item.state)">{{ stateLabel(item.state) }}</span></td>
              <td class="max-w-[220px] truncate px-4 py-3 text-slate-600" :title="protectionText(item)">{{ protectionText(item) }}</td>
              <td class="px-4 py-3 text-slate-500">{{ formatDate(item.modified_at) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ item.file_count ?? '-' }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ formatBytes(item.size_bytes) }}</td>
              <td class="px-4 py-3 text-center">
                <input
                  type="checkbox"
                  class="h-4 w-4 rounded border-slate-300"
                  :checked="item.pinned"
                  :disabled="busy || pinning === item.version_id || !item.safe"
                  :aria-label="`${item.pinned ? '取消固定' : '固定'}版本 ${item.version_label || item.version_id}`"
                  @click.stop
                  @change="togglePin(item, ($event.target as HTMLInputElement).checked)"
                >
              </td>
              <td class="px-4 py-3 text-center">
                <button type="button" class="btn h-8 px-3 text-xs" @click="openVersion(item)">查看</button>
              </td>
            </tr>
            <tr v-if="!paginatedVersions.length">
              <td colspan="8" class="px-4 py-12 text-center text-slate-500">
                {{ inventory.versions?.length ? '暂无符合条件的版本。' : '暂无版本目录。' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="matchedVersionCount" class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white px-4 py-3">
        <span class="text-xs text-slate-500">第 {{ versionPage }} / {{ totalVersionPages }} 页，共 {{ matchedVersionCount }} 个</span>
        <div class="flex items-center gap-2">
          <button class="btn h-8 px-3 text-xs" :disabled="busy || versionPage <= 1" @click="goToVersionPage(versionPage - 1)">上一页</button>
          <button class="btn h-8 px-3 text-xs" :disabled="busy || versionPage >= totalVersionPages" @click="goToVersionPage(versionPage + 1)">下一页</button>
        </div>
      </div>
    </section>

    <p v-if="message" class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{{ message }}</p>
    <p v-if="error" class="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{{ error }}</p>

    <div v-if="selectedVersion" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/50 p-4" role="presentation" @click.self="closeVersion">
        <section class="w-full max-w-2xl rounded-lg bg-white shadow-xl" role="dialog" aria-modal="true" :aria-label="`版本详情 ${selectedVersion.version_label || selectedVersion.version_id}`">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <div class="text-xs text-slate-500">版本详情</div>
            <h2 class="mt-1 break-all text-lg font-semibold text-slate-900">{{ selectedVersion.version_label || selectedVersion.version_id }}</h2>
            <div class="mt-1 break-all font-mono text-xs text-slate-500">内部 ID：{{ selectedVersion.version_id }}</div>
          </div>
          <button class="btn" type="button" @click="closeVersion">关闭</button>
        </div>
        <div class="grid gap-4 p-5 sm:grid-cols-2">
          <div><div class="text-xs text-slate-500">状态</div><div class="mt-1"><span :class="stateClass(selectedVersion.state)">{{ stateLabel(selectedVersion.state) }}</span></div></div>
          <div><div class="text-xs text-slate-500">最后变化</div><div class="mt-1 text-sm">{{ formatDate(selectedVersion.modified_at) }}</div></div>
          <div><div class="text-xs text-slate-500">文件与占用</div><div class="mt-1 text-sm">{{ selectedVersion.file_count }} 个文件 · {{ formatBytes(selectedVersion.size_bytes) }}</div></div>
          <div><div class="text-xs text-slate-500">保护判断</div><div class="mt-1 text-sm">{{ protectionText(selectedVersion) }}</div></div>
          <div class="sm:col-span-2"><div class="text-xs text-slate-500">版本指纹</div><div class="mt-1 break-all font-mono text-xs text-slate-600">{{ selectedVersion.fingerprint || '-' }}</div></div>
          <div v-if="selectedVersion.scan_error" class="sm:col-span-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700"><strong>扫描错误：</strong>{{ selectedVersion.scan_error }}</div>
          <div class="sm:col-span-2 rounded-md bg-slate-50 px-3 py-3 text-sm text-slate-700">
            <div class="font-medium">状态说明</div>
            <p class="mt-1">{{ stateDescription(selectedVersion.state) }}</p>
          </div>
          <label class="sm:col-span-2 text-sm text-slate-700">
            人工固定备注
            <textarea
              v-model="selectedPinNote"
              class="field mt-1 min-h-20 w-full"
              :disabled="!selectedVersion.pinned || pinNoteBusy || !selectedVersion.safe"
              placeholder="固定版本后填写保留原因，例如：用于回滚验证或故障取证。"
            ></textarea>
            <span v-if="!selectedVersion.pinned" class="mt-1 block text-xs text-slate-500">请先在版本清单中固定此版本，再填写保留原因。</span>
          </label>
        </div>
        <div class="flex flex-wrap justify-end gap-2 border-t border-slate-200 p-4">
          <button class="btn" type="button" @click="closeVersion">关闭</button>
          <button
            v-if="selectedVersion.pinned"
            class="btn btn-primary"
            type="button"
            :disabled="pinNoteBusy || !selectedVersion.safe"
            @click="savePinNote"
          >
            {{ pinNoteBusy ? '保存中' : '保存备注' }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  createAdminVersionCleanupPlan,
  getAdminVersions,
  startAdminVersionCleanup,
  updateAdminVersionRetention,
} from '../admin-api'
import { errorMessage } from '../api'
import type {
  VersionCleanupPlanResponse,
  VersionInventoryResponse,
  VersionSummary,
} from '../contracts'

const emit = defineEmits<{ refreshJobs: [] }>()
const inventory = ref<Partial<VersionInventoryResponse> & { versions: VersionSummary[] }>({
  versions: [],
})
const plan = ref<VersionCleanupPlanResponse | null>(null)
const planConfirmed = ref(false)
const busy = ref(false)
const pinning = ref('')
const message = ref('')
const error = ref('')
const versionQuery = ref('')
type VersionStateFilter = 'active' | 'running' | 'passed' | 'failed_gate' | 'invalid_gate' | 'legacy_complete' | 'incomplete' | 'unsafe'
type VersionScopeFilter = 'cleanup' | 'protected' | 'pinned'
const versionState = ref<'all' | VersionStateFilter>('all')
const versionScope = ref<'all' | VersionScopeFilter>('all')
const versionPage = ref(1)
const versionPageSize = ref(20)
const selectedVersion = ref<VersionSummary | null>(null)
const selectedPinNote = ref('')
const pinNoteBusy = ref(false)

const paginatedVersions = computed(() => inventory.value.versions || [])
const matchedVersionCount = computed(() => Number(inventory.value.matched_version_count ?? inventory.value.version_count ?? 0))
const totalVersionPages = computed(() => Math.max(1, Math.ceil(matchedVersionCount.value / versionPageSize.value)))

let versionFilterTimer: number | undefined
watch([versionQuery, versionState, versionScope, versionPageSize], () => {
  versionPage.value = 1
  if (versionFilterTimer) window.clearTimeout(versionFilterTimer)
  versionFilterTimer = window.setTimeout(() => { void loadInventory() }, 250)
})
watch(totalVersionPages, (pages) => {
  if (versionPage.value > pages) {
    versionPage.value = pages
    void loadInventory()
  }
})

async function loadInventory() {
  busy.value = true
  error.value = ''
  try {
    const response = await getAdminVersions({
      query: {
        q: versionQuery.value.trim() || undefined,
        state: versionState.value === 'all' ? undefined : versionState.value,
        scope: versionScope.value === 'all' ? undefined : versionScope.value,
        offset: (versionPage.value - 1) * versionPageSize.value,
        limit: versionPageSize.value,
      },
    })
    inventory.value = response
    if (selectedVersion.value) {
      const refreshed = inventory.value.versions.find(item => item.version_id === selectedVersion.value?.version_id)
      if (refreshed) {
        selectedVersion.value = refreshed
        selectedPinNote.value = refreshed.pin_note || ''
      }
    }
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function goToVersionPage(page: number) {
  if (page < 1 || page > totalVersionPages.value || page === versionPage.value) return
  versionPage.value = page
  await loadInventory()
}

async function createPlan() {
  busy.value = true
  error.value = ''
  message.value = ''
  planConfirmed.value = false
  try {
    const createdPlan = await createAdminVersionCleanupPlan()
    plan.value = createdPlan
    message.value = createdPlan.candidate_count
      ? '清理计划已生成，请核对后确认执行。'
      : '清理计划已生成，当前没有可清理版本。'
    await loadInventory()
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function executePlan() {
  if (!plan.value?.plan_id || !planConfirmed.value) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const job = await startAdminVersionCleanup({ body: { plan_id: plan.value.plan_id } })
    message.value = `清理任务已提交：${job.job_id}`
    plan.value = null
    planConfirmed.value = false
    emit('refreshJobs')
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function togglePin(item: VersionSummary, pinned: boolean) {
  pinning.value = item.version_id
  error.value = ''
  try {
    await updateAdminVersionRetention({
      path: { version_id: item.version_id },
      body: { pinned, note: item.pin_note || '' },
    })
    message.value = pinned
      ? `已固定版本 ${item.version_label || item.version_id}`
      : `已取消固定版本 ${item.version_label || item.version_id}`
    plan.value = null
    planConfirmed.value = false
    await loadInventory()
  } catch (err: unknown) {
    error.value = errorMessage(err)
    await loadInventory()
  } finally {
    pinning.value = ''
  }
}

function openVersion(item: VersionSummary) {
  selectedVersion.value = item
  selectedPinNote.value = item.pin_note || ''
}

function closeVersion() {
  if (pinNoteBusy.value) return
  selectedVersion.value = null
  selectedPinNote.value = ''
}

async function savePinNote() {
  if (!selectedVersion.value?.pinned || !selectedVersion.value.safe) return
  pinNoteBusy.value = true
  error.value = ''
  try {
    const result = await updateAdminVersionRetention({
      path: { version_id: selectedVersion.value.version_id },
      body: { pinned: true, note: selectedPinNote.value.trim() },
    })
    message.value = `已保存版本 ${selectedVersion.value.version_label || selectedVersion.value.version_id} 的固定备注`
    selectedVersion.value.pin_note = result.note
    await loadInventory()
  } catch (err: unknown) {
    error.value = errorMessage(err)
  } finally {
    pinNoteBusy.value = false
  }
}

function formatBytes(value: unknown) {
  const bytes = Number(value)
  if (!Number.isFinite(bytes)) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let amount = Math.max(0, bytes)
  let index = 0
  while (amount >= 1024 && index < units.length - 1) {
    amount /= 1024
    index += 1
  }
  return `${amount >= 10 || index === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[index]}`
}

function formatDate(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function formatExpiry(value: string) {
  return `有效至 ${formatDate(value)}`
}

function stateLabel(state: string) {
  return ({
    active: '活动',
    running: '构建中',
    passed: '门禁通过',
    failed_gate: '门禁失败',
    invalid_gate: '门禁记录异常',
    legacy_complete: '旧版完整',
    incomplete: '不完整',
    unsafe: '路径异常',
  } as Record<string, string>)[state] || state || '-'
}

function stateDescription(state: string) {
  return ({
    active: '这是当前在线使用的知识库版本，不能进入清理计划。',
    running: '该版本仍与运行中的构建任务相关，任务结束前不会被清理。',
    passed: '候选版本已通过质量门禁，可以作为后续激活或回滚候选。',
    failed_gate: '候选版本未通过质量门禁，应在构建任务或质量验证中心查看失败原因。',
    invalid_gate: '门禁记录缺失或格式异常，系统按风险状态保留该版本。',
    legacy_complete: '该版本具备旧版完整产物，但缺少当前版本格式的全部治理证据。',
    incomplete: '该版本缺少必要构建产物，通常不能用于加载或发布。',
    unsafe: '系统无法安全扫描该版本目录，已按保护状态处理。',
  } as Record<string, string>)[state] || '该版本状态暂无进一步说明。'
}

function stateClass(state: string) {
  const base = 'rounded px-2 py-1 text-xs font-semibold'
  if (state === 'active') return `${base} bg-blue-100 text-blue-700`
  if (state === 'passed') return `${base} bg-emerald-100 text-emerald-700`
  if (state === 'running') return `${base} bg-cyan-100 text-cyan-700`
  if (state === 'failed_gate' || state === 'invalid_gate' || state === 'unsafe') return `${base} bg-red-100 text-red-700`
  return `${base} bg-slate-100 text-slate-600`
}

function protectionText(item: VersionSummary) {
  const labels: Record<string, string> = {
    active: '活动版本',
    running: '运行任务',
    pinned: '人工固定',
    invalid_pin_marker: '固定标记异常',
    unsafe: '路径异常',
    minimum_age: '最短保护期',
    recent_rollback: '近期回滚',
  }
  const reasons = (item.protection_reasons || []).map((reason: string) => labels[reason] || reason)
  return reasons.length ? reasons.join('、') : item.cleanup_eligible ? cleanupReason(item.cleanup_reason) : '策略保留'
}

function cleanupReason(reason?: string) {
  if (!reason) return '-'
  return ({
    expired_failed_or_incomplete: '失败或不完整版本已过期',
    expired_successful: '成功版本已过期',
    disk_pressure: '磁盘高水位回收',
  } as Record<string, string>)[reason] || reason
}

function handlePageAction(event: Event) {
  const detail = (event as CustomEvent<{ key?: string }>).detail
  if (detail?.key === 'versions') void loadInventory()
}

onMounted(() => {
  loadInventory()
  window.addEventListener('admin-page-action', handlePageAction)
})
onBeforeUnmount(() => window.removeEventListener('admin-page-action', handlePageAction))
onBeforeUnmount(() => {
  if (versionFilterTimer) window.clearTimeout(versionFilterTimer)
})
</script>
