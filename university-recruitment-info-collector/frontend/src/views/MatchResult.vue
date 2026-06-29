<template>
  <div class="space-y-6">
    <section class="glass-panel-strong p-6 sm:p-8">
      <div class="grid gap-8 xl:grid-cols-[1.2fr_0.8fr] xl:items-end">
        <div>
          <p class="section-kicker">Match Studio</p>
          <h2 class="hero-title mt-3 text-slate-950">岗位匹配结果</h2>
          <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
            将结构化规则筛选与 AI 语义重排组合起来，帮助你在候选岗位中更快识别高契合机会、潜在风险以及需要回原文核对的低质量数据。
          </p>
        </div>

        <div class="flex flex-col items-start gap-3 xl:items-end">
          <el-tag v-if="useLlm" type="success" effect="dark" size="large">规则评分 + AI 语义评分</el-tag>
          <el-tag v-else type="info" effect="dark" size="large">仅使用规则评分</el-tag>
          <el-button @click="goBack" class="!rounded-full">重新填写画像</el-button>
        </div>
      </div>
    </section>

    <div v-if="loading" class="glass-panel-strong py-20 text-center">
      <el-progress type="circle" :percentage="100" :stroke-width="6" :width="88" indeterminate />
      <p class="mt-5 text-sm text-slate-500">正在生成匹配结果，请稍候...</p>
    </div>

    <div v-else-if="error" class="glass-panel-strong py-16">
      <el-result icon="error" title="匹配失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goBack">返回重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else>
      <el-empty v-if="results.length === 0" description="暂无匹配结果，试试调整筛选条件" class="glass-panel-strong py-16" />

      <template v-else>
        <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">已返回岗位</p>
            <p class="mt-3 text-3xl font-semibold text-slate-950">{{ results.length }}</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">最高匹配分</p>
            <p class="mt-3 text-3xl font-semibold text-emerald-700">{{ topScore }}</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">硬性通过</p>
            <p class="mt-3 text-3xl font-semibold text-slate-950">{{ passCount }}</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">低质量数据</p>
            <p class="mt-3 text-3xl font-semibold text-amber-600">{{ lowQualityCount }}</p>
          </div>
        </section>

        <section v-if="previousMatch" class="glass-panel p-4 border border-emerald-100 bg-emerald-50/30">
          <div class="flex flex-wrap items-center gap-4 text-sm">
            <span class="font-semibold text-emerald-800">与上轮对比</span>
            <span>上次: {{ previousMatch.totalCandidates }} 个候选 · {{ previousMatch.useLlm ? 'AI增强' : '规则匹配' }} · {{ formatTime(previousMatch.timestamp) }}</span>
            <span class="text-emerald-700">最高分差: <strong>{{ topScore - (previousMatch.results[0]?.match_score || 0) > 0 ? '+' : '' }}{{ topScore - (previousMatch.results[0]?.match_score || 0) }}</strong></span>
            <el-button text size="small" @click="previousMatch = null">关闭</el-button>
          </div>
        </section>

        <section class="glass-panel p-5">
          <div class="grid gap-3 xl:grid-cols-[auto_auto_auto_auto_1fr] xl:items-center">
            <el-select v-model="sortBy" class="xl:min-w-[10rem]">
              <el-option label="按匹配分" value="score" />
              <el-option label="按置信度" value="confidence" />
              <el-option label="按截止日期" value="deadline" />
            </el-select>
            <el-select v-model="minScore" class="xl:min-w-[9rem]">
              <el-option :value="0" label="全部分数" />
              <el-option :value="60" label="60 分以上" />
              <el-option :value="70" label="70 分以上" />
              <el-option :value="80" label="80 分以上" />
            </el-select>
            <el-checkbox v-model="onlyHardPassed">仅看硬性通过</el-checkbox>
            <el-checkbox v-model="hideLowQuality">隐藏低质量岗位</el-checkbox>
            <div class="text-sm text-slate-500 xl:text-right">
              候选 {{ totalCandidates }}，硬性过滤 {{ hardFiltered }}，当前展示 {{ displayedResults.length }}
            </div>
          </div>
        </section>

        <section class="space-y-4">
          <article
            v-for="item in displayedResults"
            :key="item.job.id"
            class="glass-panel-strong overflow-hidden p-6 transition-transform duration-200 hover:-translate-y-1"
          >
            <div class="grid gap-6 xl:grid-cols-[1fr_108px]">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">{{ item.job.school }}</span>
                  <span class="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">{{ item.job.position }}</span>
                  <el-tag v-if="!item.hard_constraint_passed" size="small" type="danger">硬性未通过</el-tag>
                  <el-tag v-if="item.job.quality_status" :type="qualityTagType(item.job.quality_status)" size="small" effect="plain">
                    {{ qualityLabel(item.job.quality_status) }}
                  </el-tag>
                </div>

                <div class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-500">
                  <span>{{ item.job.department || '未标注部门' }}</span>
                  <span>{{ item.job.location || '未标注地点' }}</span>
                  <span>{{ item.job.job_type || '未标注岗位类型' }}</span>
                  <span>{{ item.job.education_requirement || '未标注学历要求' }}</span>
                </div>

                <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  <div class="rounded-2xl bg-slate-50 px-4 py-3">
                    <p class="text-xs uppercase tracking-[0.18em] text-slate-400">截止日期</p>
                    <p class="mt-2 text-sm font-semibold text-slate-800">{{ item.job.deadline || '长期/未说明' }}</p>
                  </div>
                  <div class="rounded-2xl bg-slate-50 px-4 py-3">
                    <p class="text-xs uppercase tracking-[0.18em] text-slate-400">数据质量</p>
                    <p class="mt-2 text-sm font-semibold text-slate-800">{{ item.job.quality_score ?? '—' }}</p>
                  </div>
                  <div class="rounded-2xl bg-slate-50 px-4 py-3">
                    <p class="text-xs uppercase tracking-[0.18em] text-slate-400">结果置信度</p>
                    <p class="mt-2 text-sm font-semibold text-slate-800">{{ item.confidence_score }}%</p>
                  </div>
                </div>

                <div v-if="item.hard_constraint_failures.length" class="mt-4 flex flex-wrap gap-2">
                  <el-tag v-for="f in item.hard_constraint_failures" :key="f" type="danger" size="small" effect="plain">
                    {{ f }}
                  </el-tag>
                </div>

                <div class="mt-4 flex flex-wrap gap-2">
                  <el-tag v-for="reason in item.match_reasons" :key="reason" type="success" size="small" effect="plain">
                    {{ reason }}
                  </el-tag>
                  <el-tag v-for="risk in item.potential_risks" :key="risk" type="warning" size="small" effect="plain">
                    {{ risk }}
                  </el-tag>
                </div>

                <div v-if="item.llm_summary" class="mt-5 rounded-2xl border border-sky-100 bg-sky-50 p-4 text-sm leading-6 text-slate-700">
                  <p class="font-semibold text-sky-800">AI 分析</p>
                  <p class="mt-2">{{ item.llm_summary }}</p>
                </div>

                <div v-if="item.job.extraction_warnings && item.job.quality_status === 'needs_review'" class="mt-4 rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  <p class="font-semibold">数据提醒</p>
                  <p class="mt-2">{{ formatWarnings(item.job.extraction_warnings) }}</p>
                </div>

                <div class="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
                  <el-button type="primary" link @click="openLink(item.job.source_url)">查看原文</el-button>
                  <span v-for="action in item.suggested_actions" :key="action" class="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                    {{ action }}
                  </span>
                </div>
              </div>

              <div class="flex flex-col items-center justify-start gap-3 rounded-[26px] bg-slate-950 px-4 py-5 text-white">
                <span class="text-xs uppercase tracking-[0.24em] text-slate-400">Match</span>
                <div class="text-4xl font-semibold">{{ item.match_score }}</div>
                <div class="h-2 w-full overflow-hidden rounded-full bg-white/10">
                  <div class="h-full rounded-full bg-emerald-400 transition-all duration-300" :style="{ width: `${item.match_score}%` }"></div>
                </div>
              </div>
            </div>
          </article>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { matchJobs } from '../api/index.js'

const MATCH_DATA_KEY = 'university-recruitment-match-data'
const MATCH_HISTORY_KEY = 'university-recruitment-match-history'
const router = useRouter()
const results = ref([])
const loading = ref(true)
const error = ref('')
const useLlm = ref(false)
const totalCandidates = ref(0)
const hardFiltered = ref(0)
const sortBy = ref('score')
const minScore = ref(0)
const onlyHardPassed = ref(true)
const hideLowQuality = ref(false)
const previousMatch = ref(null)
const requestOptions = ref({
  resultLimit: 10,
  candidateLimit: 50,
  includeHardConstraintFailures: false,
})

function loadMatchHistory() {
  try {
    const raw = localStorage.getItem(MATCH_HISTORY_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data.results && data.results.length > 0) {
        previousMatch.value = data
      }
    }
  } catch {}
}

function saveMatchHistory(currentResults, llmUsed) {
  try {
    const history = {
      timestamp: new Date().toISOString(),
      useLlm: llmUsed,
      totalCandidates: totalCandidates.value,
      results: currentResults.map(r => ({
        job_id: r.job?.id,
        school: r.job?.school,
        position: r.job?.position,
        match_score: r.match_score,
      })),
    }
    localStorage.setItem(MATCH_HISTORY_KEY, JSON.stringify(history))
  } catch {}
}

const displayedResults = computed(() => {
  let arr = [...results.value]
  if (onlyHardPassed.value) {
    arr = arr.filter(item => item.hard_constraint_passed)
  }
  if (hideLowQuality.value) {
    arr = arr.filter(item => item.job?.quality_status !== 'needs_review' && item.job?.quality_status !== 'hidden')
  }
  if (minScore.value > 0) {
    arr = arr.filter(item => Number(item.match_score || 0) >= minScore.value)
  }
  arr.sort((a, b) => {
    if (sortBy.value === 'confidence') {
      return Number(b.confidence_score || 0) - Number(a.confidence_score || 0)
    }
    if (sortBy.value === 'deadline') {
      const ad = a.job?.deadline ? new Date(a.job.deadline).getTime() : Number.MAX_SAFE_INTEGER
      const bd = b.job?.deadline ? new Date(b.job.deadline).getTime() : Number.MAX_SAFE_INTEGER
      return ad - bd
    }
    return Number(b.match_score || 0) - Number(a.match_score || 0)
  })
  return arr
})

const topScore = computed(() => displayedResults.value[0]?.match_score || 0)
const averageScore = computed(() => {
  if (!results.value.length) return 0
  const total = results.value.reduce((sum, item) => sum + Number(item.match_score || 0), 0)
  return Math.round(total / results.value.length)
})
const passCount = computed(() => results.value.filter(item => item.hard_constraint_passed).length)
const lowQualityCount = computed(() => results.value.filter(item => {
  const status = item.job?.quality_status
  return status === 'needs_review' || status === 'hidden'
}).length)

function scoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  return '#ef4444'
}

function qualityTagType(status) {
  if (status === 'normal') return 'success'
  if (status === 'needs_review') return 'warning'
  if (status === 'hidden') return 'danger'
  return 'info'
}

function qualityLabel(status) {
  if (status === 'normal') return '质量正常'
  if (status === 'needs_review') return '待人工复核'
  if (status === 'hidden') return '低可信数据'
  return '质量未知'
}

function formatWarnings(raw) {
  if (!raw) return '该岗位存在字段抽取不完整或可信度不足。'
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.join('；') : String(raw)
  } catch {
    return String(raw)
  }
}

function openLink(url) {
  const u = (url || '').toString().trim()
  if (!u.startsWith('http://') && !u.startsWith('https://')) {
    ElMessage.warning('不支持打开非 HTTP/HTTPS 链接')
    return
  }
  window.open(u, '_blank', 'noopener,noreferrer')
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function goBack() {
  router.push({ name: 'profile' })
}

onMounted(async () => {
  try {
    const raw = sessionStorage.getItem(MATCH_DATA_KEY)
    if (!raw) {
      error.value = '缺少用户画像数据，请先填写求职画像'
      loading.value = false
      return
    }
    const { user, useLlm: llm, options } = JSON.parse(raw)
    useLlm.value = llm
    requestOptions.value = {
      ...requestOptions.value,
      ...(options || {}),
    }
    onlyHardPassed.value = !requestOptions.value.includeHardConstraintFailures
    const res = await matchJobs(user, {
      ...requestOptions.value,
      useLlm: llm,
    })
    results.value = res.data.results || []
    totalCandidates.value = res.data.total_candidates || 0
    hardFiltered.value = res.data.hard_filtered_out || 0
    saveMatchHistory(results.value, llm)
  } catch (e) {
    console.error('Match failed:', e)
    error.value = '匹配请求失败，请稍后重试'
    sessionStorage.removeItem(MATCH_DATA_KEY)
  } finally {
    loading.value = false
  }
})

loadMatchHistory()
</script>
