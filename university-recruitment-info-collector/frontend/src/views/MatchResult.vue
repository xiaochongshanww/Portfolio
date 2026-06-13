<template>
  <div>
    <!-- Header Bar -->
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold text-gray-800">匹配结果</h2>
        <p class="text-sm text-gray-400 mt-1">
          共为你匹配到 {{ results.length }} 个岗位
          <span v-if="results.length" class="ml-2">
            最高分 <span class="text-green-500 font-semibold">{{ results[0]?.match_score }} 分</span>
          </span>
        </p>
      </div>
      <div class="flex items-center gap-3">
        <el-tag v-if="useLlm" type="success" effect="dark" size="large">🤖 LLM 分析已开启</el-tag>
        <el-tag v-else type="info" effect="dark" size="large">📋 规则匹配模式</el-tag>
        <el-button @click="goBack">
          <span class="flex items-center gap-1">← 重新填写</span>
        </el-button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-20">
      <el-progress type="circle" :percentage="100" :stroke-width="6" :width="80" indeterminate />
      <p class="mt-4 text-gray-400">正在匹配中，请稍候...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-16">
      <el-result icon="error" title="匹配失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goBack">返回重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- Results -->
    <template v-else>
      <el-empty v-if="results.length === 0" description="暂无匹配结果，试试调整筛选条件" />

      <div class="space-y-4">
        <div
          v-for="item in results"
          :key="item.job.id"
          class="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
        >
          <div class="p-6">
            <!-- Top Row -->
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <!-- School + Position -->
                <div class="flex flex-wrap items-center gap-2 mb-2">
                  <h3 class="text-lg font-semibold text-gray-900">{{ item.job.school }}</h3>
                  <el-tag size="small" type="primary" effect="plain">{{ item.job.position }}</el-tag>
                </div>
                <!-- Meta -->
                <p class="text-sm text-gray-400">
                  {{ [item.job.department, item.job.location, item.job.job_type, item.job.education_requirement].filter(Boolean).join(' · ') }}
                </p>
                <!-- Deadline -->
                <p v-if="item.job.deadline" class="text-xs text-gray-300 mt-1">
                  ⏰ 截止日期：{{ item.job.deadline }}
                </p>
              </div>
              <!-- Score -->
              <el-progress
                type="circle"
                :percentage="item.match_score"
                :width="80"
                :stroke-width="8"
                :color="scoreColor(item.match_score)"
              />
            </div>

            <el-divider class="!my-3" />

            <!-- Tags -->
            <div class="flex flex-wrap gap-2 mb-3">
              <el-tag
                v-for="reason in item.match_reasons"
                :key="reason"
                type="success"
                size="small"
                effect="plain"
              >
                ✅ {{ reason }}
              </el-tag>
              <el-tag
                v-for="risk in item.potential_risks"
                :key="risk"
                type="warning"
                size="small"
                effect="plain"
              >
                ⚠️ {{ risk }}
              </el-tag>
            </div>

            <!-- LLM Summary -->
            <div
              v-if="item.llm_summary"
              class="bg-blue-50 border border-blue-100 rounded-lg p-4 mt-3 text-sm leading-relaxed text-gray-700"
            >
              <p class="font-medium text-blue-800 mb-1">🤖 LLM 分析</p>
              <p>{{ item.llm_summary }}</p>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-3 mt-4 pt-3 border-t border-gray-50">
              <el-button type="primary" link @click="openLink(item.job.source_url)" class="!text-base">
                🔗 查看原文
              </el-button>
              <el-tag
                v-for="action in item.suggested_actions"
                :key="action"
                type="info"
                size="small"
                effect="plain"
              >
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
import { useRoute, useRouter } from 'vue-router'
import { matchJobs } from '../api/index.js'

const route = useRoute()
const router = useRouter()

const results = ref([])
const loading = ref(true)
const error = ref('')
const useLlm = ref(false)

function scoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  return '#ef4444'
}

function openLink(url) {
  window.open(url, '_blank')
}

function goBack() {
  router.push({ name: 'profile' })
}

onMounted(async () => {
  try {
    const raw = route.query.data
    if (!raw) {
      error.value = '缺少用户画像数据，请先填写求职画像'
      loading.value = false
      return
    }
    const user = JSON.parse(raw)
    useLlm.value = route.query.use_llm === '1'
    const res = await matchJobs(user, 10, useLlm.value)
    results.value = res.data.results
  } catch (e) {
    console.error('Match failed:', e)
    error.value = e.response?.data?.detail || e.message || '匹配请求失败'
  } finally {
    loading.value = false
  }
})
</script>
