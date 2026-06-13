<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold text-gray-800">匹配结果</h2>
        <p class="text-sm text-gray-400 mt-1">
          共为你匹配到 {{ results.length }} 个岗位
          <span v-if="results.length" class="ml-2">
            最高分 <span class="text-green-500 font-semibold">{{ results[0]?.match_score }} 分</span>
          </span>
          <span v-if="totalCandidates" class="ml-2 text-gray-300">
            (候选 {{ totalCandidates }}，硬性过滤 {{ hardFiltered }})
          </span>
        </p>
      </div>
      <div class="flex items-center gap-3">
        <el-tag v-if="useLlm" type="success" effect="dark" size="large">🤖 AI 增强分析</el-tag>
        <el-tag v-else type="info" effect="dark" size="large">📋 规则评分 + AI 语义评分共同组成最终分数；AI 同时生成匹配理由、风险和申请建议。</el-tag>
        <el-button @click="goBack"><span class="flex items-center gap-1">← 重新填写</span></el-button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-20">
      <el-progress type="circle" :percentage="100" :stroke-width="6" :width="80" indeterminate />
      <p class="mt-4 text-gray-400">正在匹配中，请稍候...</p>
    </div>

    <div v-else-if="error" class="text-center py-16">
      <el-result icon="error" title="匹配失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goBack">返回重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else>
      <el-empty v-if="results.length === 0" description="暂无匹配结果，试试调整筛选条件" />
      <div class="space-y-4">
        <div v-for="item in results" :key="item.job.id"
          class="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
          <div class="p-6">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-2 mb-2">
                  <h3 class="text-lg font-semibold text-gray-900">{{ item.job.school }}</h3>
                  <el-tag size="small" type="primary" effect="plain">{{ item.job.position }}</el-tag>
                  <el-tag v-if="!item.hard_constraint_passed" size="small" type="danger">硬性条件未通过</el-tag>
                </div>
                <p class="text-sm text-gray-400">
                  {{ [item.job.department, item.job.location, item.job.job_type, item.job.education_requirement].filter(Boolean).join(' · ') }}
                </p>
                <p v-if="item.job.deadline" class="text-xs text-gray-300 mt-1">
                  ⏰ 截止日期：{{ item.job.deadline }}
                </p>
              </div>
              <div class="text-center">
                <el-progress type="circle" :percentage="item.match_score" :width="80" :stroke-width="8"
                  :color="scoreColor(item.match_score)" />
                <p class="text-xs text-gray-400 mt-1">置信度 {{ item.confidence_score }}%</p>
              </div>
            </div>

            <el-divider class="!my-3" />

            <!-- Hard constraint failures -->
            <div v-if="item.hard_constraint_failures.length" class="mb-2">
              <el-tag v-for="f in item.hard_constraint_failures" :key="f" type="danger" size="small" effect="plain" class="mr-1 mb-1">
                ❌ {{ f }}
              </el-tag>
            </div>

            <!-- Match reasons & risks -->
            <div class="flex flex-wrap gap-2 mb-3">
              <el-tag v-for="reason in item.match_reasons" :key="reason" type="success" size="small" effect="plain">
                ✅ {{ reason }}
              </el-tag>
              <el-tag v-for="risk in item.potential_risks" :key="risk" type="warning" size="small" effect="plain">
                ⚠️ {{ risk }}
              </el-tag>
            </div>

            <div v-if="item.llm_summary"
              class="bg-blue-50 border border-blue-100 rounded-lg p-4 mt-3 text-sm leading-relaxed text-gray-700">
              <p class="font-medium text-blue-800 mb-1">🤖 AI 分析</p>
              <p>{{ item.llm_summary }}</p>
            </div>

            <div class="flex items-center gap-3 mt-4 pt-3 border-t border-gray-50">
              <el-button type="primary" link @click="openLink(item.job.source_url)" class="!text-base">
                🔗 查看原文
              </el-button>
              <el-tag v-for="action in item.suggested_actions" :key="action" type="info" size="small" effect="plain">
                💡 {{ action }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { matchJobs } from '../api/index.js'

const MATCH_DATA_KEY = 'university-recruitment-match-data'
const router = useRouter()
const results = ref([])
const loading = ref(true)
const error = ref('')
const useLlm = ref(false)
const totalCandidates = ref(0)
const hardFiltered = ref(0)

function scoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  return '#ef4444'
}

function openLink(url) {
  const u = (url || '').toString().trim()
  if (!u.startsWith('http://') && !u.startsWith('https://')) {
    ElMessage.warning('不支持打开非 HTTP/HTTPS 链接')
    return
  }
  window.open(u, '_blank', 'noopener,noreferrer')
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
    const { user, useLlm: llm } = JSON.parse(raw)
    useLlm.value = llm
    const res = await matchJobs(user, 10, llm)
    results.value = res.data.results || []
    totalCandidates.value = res.data.total_candidates || 0
    hardFiltered.value = res.data.hard_filtered_out || 0
  } catch (e) {
    console.error('Match failed:', e)
    error.value = '匹配请求失败，请稍后重试'
    sessionStorage.removeItem(MATCH_DATA_KEY)
  } finally {
    loading.value = false
  }
})
</script>
