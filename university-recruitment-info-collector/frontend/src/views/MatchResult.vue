<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h3>匹配结果</h3>
      <div>
        <el-tag v-if="useLlm" type="success" effect="dark">LLM 分析已开启</el-tag>
        <el-tag v-else type="info" effect="dark">规则匹配模式</el-tag>
        <el-button style="margin-left: 12px;" @click="goBack">重新填写</el-button>
      </div>
    </div>

    <div v-if="loading" style="text-align: center; padding: 80px 0;">
      <el-progress type="circle" :percentage="100" :stroke-width="6" :width="80" indeterminate />
      <p style="margin-top: 16px; color: #909399;">正在匹配中，请稍候...</p>
    </div>

    <div v-else-if="error" style="text-align: center; padding: 40px 0;">
      <el-result icon="error" title="匹配失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goBack">返回重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else>
      <el-empty v-if="results.length === 0" description="暂无匹配结果" />

      <div v-for="item in results" :key="item.job.id" style="margin-bottom: 20px;">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <h4 style="margin: 0 0 4px;">
                {{ item.job.school }}
                <el-tag size="small" style="margin-left: 8px;">{{ item.job.position }}</el-tag>
              </h4>
              <p style="margin: 0; color: #909399; font-size: 13px;">
                {{ [item.job.department, item.job.location, item.job.job_type].filter(Boolean).join(' | ') }}
              </p>
            </div>
            <el-progress
              type="circle"
              :percentage="item.match_score"
              :width="70"
              :stroke-width="8"
              :color="scoreColor(item.match_score)"
            />
          </div>

          <el-divider style="margin: 12px 0;" />

          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
            <el-tag
              v-for="reason in item.match_reasons"
              :key="reason"
              type="success"
              size="small"
            >
              {{ reason }}
            </el-tag>
            <el-tag
              v-for="risk in item.potential_risks"
              :key="risk"
              type="warning"
              size="small"
            >
              {{ risk }}
            </el-tag>
          </div>

          <div v-if="item.llm_summary" style="background: #f5f7fa; border-radius: 6px; padding: 12px; margin-top: 8px; font-size: 14px; line-height: 1.6;">
            <strong>LLM 分析：</strong>
            <p style="margin: 4px 0 0;">{{ item.llm_summary }}</p>
          </div>

          <div style="margin-top: 12px; display: flex; gap: 8px;">
            <el-button type="primary" link @click="openLink(item.job.source_url)">
              查看原文
            </el-button>
            <el-tag
              v-for="action in item.suggested_actions"
              :key="action"
              type="info"
              size="small"
              effect="plain"
            >
              {{ action }}
            </el-tag>
          </div>
        </el-card>
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
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
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
