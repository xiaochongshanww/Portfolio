<template>
  <div class="space-y-5">
    <section class="panel overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">知识版本</h2>
          <p class="muted mt-1">{{ inventory.active_version_id ? `活动版本 ${inventory.active_version_id}` : '未识别活动版本' }}</p>
        </div>
        <div class="flex gap-2">
          <button class="btn" :disabled="busy" @click="loadInventory">刷新</button>
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
              <td class="px-4 py-3 font-medium">{{ item.version_id }}</td>
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
      <div class="border-b border-slate-200 p-4">
        <h2 class="panel-title">版本清单</h2>
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
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in inventory.versions || []" :key="item.version_id" class="border-t border-slate-100">
              <td class="px-4 py-3">
                <div class="font-medium">{{ item.version_id }}</div>
                <div v-if="item.scan_error" class="mt-1 max-w-[360px] truncate text-xs text-red-600">{{ item.scan_error }}</div>
              </td>
              <td class="px-4 py-3"><span :class="stateClass(item.state)">{{ stateLabel(item.state) }}</span></td>
              <td class="px-4 py-3 text-slate-600">{{ protectionText(item) }}</td>
              <td class="px-4 py-3 text-slate-500">{{ formatDate(item.modified_at) }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ item.file_count ?? '-' }}</td>
              <td class="px-4 py-3 text-right tabular-nums">{{ formatBytes(item.size_bytes) }}</td>
              <td class="px-4 py-3 text-center">
                <input
                  type="checkbox"
                  class="h-4 w-4 rounded border-slate-300"
                  :checked="item.pinned"
                  :disabled="busy || pinning === item.version_id || !item.safe"
                  @change="togglePin(item, ($event.target as HTMLInputElement).checked)"
                >
              </td>
            </tr>
            <tr v-if="!inventory.versions?.length">
              <td colspan="7" class="px-4 py-12 text-center text-slate-500">暂无版本目录。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p v-if="message" class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{{ message }}</p>
    <p v-if="error" class="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiGet, apiPost, apiPut } from '../api'

const emit = defineEmits<{ refreshJobs: [] }>()
const inventory = ref<any>({ versions: [] })
const plan = ref<any>(null)
const planConfirmed = ref(false)
const busy = ref(false)
const pinning = ref('')
const message = ref('')
const error = ref('')

async function loadInventory() {
  busy.value = true
  error.value = ''
  try {
    inventory.value = await apiGet('/admin/versions')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function createPlan() {
  busy.value = true
  error.value = ''
  message.value = ''
  planConfirmed.value = false
  try {
    plan.value = await apiPost('/admin/versions/cleanup-plans')
    message.value = plan.value.candidate_count
      ? '清理计划已生成，请核对后确认执行。'
      : '清理计划已生成，当前没有可清理版本。'
    await loadInventory()
  } catch (err: any) {
    error.value = err.message || String(err)
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
    const job = await apiPost('/admin/jobs/cleanup-versions', { plan_id: plan.value.plan_id })
    message.value = `清理任务已提交：${job.job_id}`
    plan.value = null
    planConfirmed.value = false
    emit('refreshJobs')
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}

async function togglePin(item: any, pinned: boolean) {
  pinning.value = item.version_id
  error.value = ''
  try {
    await apiPut(`/admin/versions/${encodeURIComponent(item.version_id)}/retention`, { pinned, note: item.pin_note || '' })
    message.value = pinned ? `已固定版本 ${item.version_id}` : `已取消固定版本 ${item.version_id}`
    plan.value = null
    planConfirmed.value = false
    await loadInventory()
  } catch (err: any) {
    error.value = err.message || String(err)
    await loadInventory()
  } finally {
    pinning.value = ''
  }
}

function formatBytes(value: any) {
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

function formatDate(value: string) {
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

function stateClass(state: string) {
  const base = 'rounded px-2 py-1 text-xs font-semibold'
  if (state === 'active') return `${base} bg-blue-100 text-blue-700`
  if (state === 'passed') return `${base} bg-emerald-100 text-emerald-700`
  if (state === 'running') return `${base} bg-cyan-100 text-cyan-700`
  if (state === 'failed_gate' || state === 'invalid_gate' || state === 'unsafe') return `${base} bg-red-100 text-red-700`
  return `${base} bg-slate-100 text-slate-600`
}

function protectionText(item: any) {
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

function cleanupReason(reason: string) {
  return ({
    expired_failed_or_incomplete: '失败或不完整版本已过期',
    expired_successful: '成功版本已过期',
    disk_pressure: '磁盘高水位回收',
  } as Record<string, string>)[reason] || reason || '-'
}

onMounted(loadInventory)
</script>
