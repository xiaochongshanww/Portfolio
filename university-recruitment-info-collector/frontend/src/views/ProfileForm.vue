<template>
  <div class="space-y-6">
    <section class="glass-panel-strong p-6 sm:p-8">
      <div class="grid gap-8 xl:grid-cols-[1.15fr_0.85fr] xl:items-start">
        <div>
          <p class="section-kicker">Profile Designer</p>
          <h2 class="hero-title mt-3 text-slate-950">构建你的求职画像</h2>
          <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
            把学历、专业、研究方向与偏好约束组合成一个可复用的匹配模板。你可以用它快速比较不同高校岗位，也可以切换到 AI 增强模式获取风险提示。
          </p>
        </div>

        <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">必填核心</p>
            <p class="mt-3 text-lg font-semibold text-slate-950">学历 + 专业</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">候选池</p>
            <p class="mt-3 text-lg font-semibold text-slate-950">{{ form.candidate_limit }} 个候选</p>
          </div>
          <div class="metric-card">
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">结果返回</p>
            <p class="mt-3 text-lg font-semibold text-slate-950">{{ form.result_limit }} 个岗位</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid gap-6 xl:grid-cols-[1.35fr_0.65fr] xl:items-start">
      <div class="glass-panel-strong p-6 sm:p-8">
        <el-form :model="form" label-position="top" size="large" class="grid gap-5 md:grid-cols-2">
          <el-form-item label="最高学历" required>
            <el-select v-model="form.education" placeholder="请选择最高学历" class="w-full!">
              <el-option label="博士" value="博士" />
              <el-option label="硕士" value="硕士" />
              <el-option label="本科" value="本科" />
            </el-select>
          </el-form-item>

          <el-form-item label="专业" required>
            <el-input v-model="form.major" placeholder="如：计算机科学与技术" />
          </el-form-item>

          <el-form-item label="研究方向" class="md:col-span-2">
            <el-input v-model="form.research_direction" placeholder="如：人工智能、大数据、教育学评估" />
          </el-form-item>

          <el-form-item label="个人关键词" class="md:col-span-2">
            <el-select v-model="form.keywords" multiple filterable allow-create default-first-option placeholder="输入关键词后回车添加" class="w-full!" />
          </el-form-item>

          <el-form-item label="期望地区">
            <el-select v-model="form.target_locations" multiple filterable allow-create default-first-option placeholder="如：广州、深圳" class="w-full!" />
          </el-form-item>

          <el-form-item label="期望学校类型">
            <el-select v-model="form.target_school_types" multiple filterable allow-create default-first-option placeholder="如：双一流、985、公办" class="w-full!" />
          </el-form-item>

          <el-form-item label="岗位偏好">
            <el-select v-model="form.job_preferences" multiple filterable allow-create default-first-option placeholder="如：教学科研岗、博士后" class="w-full!" />
          </el-form-item>

          <el-form-item label="限制条件">
            <el-select v-model="form.constraints" multiple filterable allow-create default-first-option placeholder="如：编制、落户、海外经历" class="w-full!" />
          </el-form-item>

          <div class="md:col-span-2 soft-divider"></div>

          <el-form-item label="返回结果数" class="md:col-span-2">
            <div class="w-full rounded-2xl bg-slate-50 px-4 py-4">
              <div class="flex items-center gap-4">
                <el-slider v-model="form.result_limit" :min="5" :max="30" :step="5" class="flex-1" />
                <span class="w-12 text-right text-sm font-semibold text-slate-700">{{ form.result_limit }}</span>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="候选池大小" class="md:col-span-2">
            <div class="w-full rounded-2xl bg-slate-50 px-4 py-4">
              <div class="flex items-center gap-4">
                <el-slider v-model="form.candidate_limit" :min="20" :max="100" :step="10" class="flex-1" />
                <span class="w-12 text-right text-sm font-semibold text-slate-700">{{ form.candidate_limit }}</span>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="硬性未通过岗位" class="md:col-span-2 !mb-1">
            <div class="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p class="text-sm font-semibold text-slate-800">保留人工比较空间</p>
                <p class="mt-1 text-xs text-slate-500">开启后会把硬性条件未通过的岗位也返回到结果页中。</p>
              </div>
              <el-switch v-model="form.include_hard_constraint_failures" />
            </div>
          </el-form-item>

          <div class="md:col-span-2 flex flex-col gap-3 pt-2 sm:flex-row">
            <el-button type="primary" size="large" @click="submitMatch(false)" :loading="submitting" :disabled="submitting" class="!h-14 flex-1 !rounded-2xl">
              规则匹配
            </el-button>
            <el-button type="success" size="large" @click="submitMatch(true)" :loading="submitting" :disabled="submitting" class="!h-14 flex-1 !rounded-2xl">
              AI 增强匹配
            </el-button>
          </div>

          <div class="md:col-span-2 flex items-center justify-between">
            <span class="text-xs text-slate-400">填写内容自动保存在浏览器当前环境中</span>
            <el-button text size="small" @click="clearProfile" class="!text-slate-400 hover:!text-rose-500">清空画像</el-button>
          </div>
        </el-form>
      </div>

      <div class="space-y-4">
        <section class="glass-panel p-5">
          <p class="section-kicker">How It Works</p>
          <div class="mt-4 space-y-4 text-sm leading-6 text-slate-600">
            <div>
              <p class="font-semibold text-slate-900">规则匹配</p>
              <p>基于学历、专业、地点、岗位偏好和硬性约束计算结构化得分。</p>
            </div>
            <div>
              <p class="font-semibold text-slate-900">AI 增强匹配</p>
              <p>在候选池中进行语义重排，补充匹配理由、潜在风险与建议动作。</p>
            </div>
          </div>
        </section>

        <section class="glass-panel p-5">
          <p class="section-kicker">Recommended Inputs</p>
          <div class="mt-4 flex flex-wrap gap-2 text-sm text-slate-600">
            <span class="rounded-full bg-slate-100 px-3 py-1">研究方向尽量具体</span>
            <span class="rounded-full bg-slate-100 px-3 py-1">关键词不要只写一个</span>
            <span class="rounded-full bg-slate-100 px-3 py-1">限制条件要写真实门槛</span>
            <span class="rounded-full bg-slate-100 px-3 py-1">候选池建议 40-60</span>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const STORAGE_KEY = 'university-recruitment-profile'
const MATCH_DATA_KEY = 'university-recruitment-match-data'

const router = useRouter()
const submitting = ref(false)

const defaultForm = {
  education: '',
  major: '',
  research_direction: '',
  keywords: [],
  target_locations: [],
  target_school_types: [],
  job_preferences: [],
  constraints: [],
  result_limit: 10,
  candidate_limit: 50,
  include_hard_constraint_failures: false,
}

function loadProfile() {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY) || localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const data = JSON.parse(saved)
      return { ...defaultForm, ...data }
    }
  } catch { /* ignore */ }
  return { ...defaultForm }
}

const form = reactive(loadProfile())

// Auto-save
let saveTimer = null
watch(() => ({ ...form }), (val) => {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(val)) } catch {}
  }, 300)
})

function clearProfile() {
  ElMessageBox.confirm('确定要清空所有已保存的画像数据吗？', '清空确认', {
    confirmButtonText: '确定清空', cancelButtonText: '取消', type: 'warning',
  }).then(() => {
    Object.assign(form, defaultForm)
    sessionStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(STORAGE_KEY)
    ElMessage.success('画像数据已清空')
  }).catch(() => {})
}

function submitMatch(useLlm) {
  if (!form.education || !form.major) {
    ElMessage.warning('请填写最高学历和专业')
    return
  }
  if (submitting.value) return
  submitting.value = true
  const {
    result_limit,
    candidate_limit,
    include_hard_constraint_failures,
    ...user
  } = form
  sessionStorage.setItem(MATCH_DATA_KEY, JSON.stringify({
    user,
    useLlm,
    options: {
      resultLimit: result_limit,
      candidateLimit: candidate_limit,
      includeHardConstraintFailures: include_hard_constraint_failures,
    },
  }))
  router.push({ name: 'match' })
}
</script>
