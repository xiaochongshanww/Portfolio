<template>
  <div class="max-w-2xl mx-auto">
    <div class="mb-8 text-center">
      <h2 class="text-2xl font-semibold text-gray-800">我的求职画像</h2>
      <p class="text-sm text-gray-400 mt-1">填写您的学术背景与求职偏好，系统将自动匹配最佳岗位</p>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
      <el-form :model="form" label-width="130px" size="large">
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

        <el-form-item label="研究方向">
          <el-input v-model="form.research_direction" placeholder="如：人工智能、大数据" />
        </el-form-item>

        <el-form-item label="个人关键词">
          <el-select v-model="form.keywords" multiple filterable allow-create default-first-option
            placeholder="输入关键词后回车添加" class="w-full!" />
        </el-form-item>

        <el-form-item label="期望地区">
          <el-select v-model="form.target_locations" multiple filterable allow-create default-first-option
            placeholder="如：广州、深圳" class="w-full!" />
        </el-form-item>

        <el-form-item label="期望学校类型">
          <el-select v-model="form.target_school_types" multiple filterable allow-create default-first-option
            placeholder="如：双一流、985、211、公办" class="w-full!" />
        </el-form-item>

        <el-form-item label="岗位偏好">
          <el-select v-model="form.job_preferences" multiple filterable allow-create default-first-option
            placeholder="如：教学科研岗、博士后" class="w-full!" />
        </el-form-item>

        <el-form-item label="限制条件">
          <el-select v-model="form.constraints" multiple filterable allow-create default-first-option
            placeholder="如：编制、落户" class="w-full!" />
        </el-form-item>

        <el-form-item>
          <div class="flex gap-3 pt-2">
            <el-button type="primary" size="large" @click="submitMatch(false)" :loading="submitting" :disabled="submitting" class="flex-1">
              <span class="flex items-center justify-center gap-1">🔍 规则匹配</span>
            </el-button>
            <el-button type="success" size="large" @click="submitMatch(true)" :loading="submitting" :disabled="submitting" class="flex-1">
              <span class="flex items-center justify-center gap-1">🤖 AI 增强匹配</span>
            </el-button>
          </div>
          <div class="flex items-center justify-between mt-3">
            <span class="text-xs text-gray-300">💾 填写内容自动保存到本地浏览器</span>
            <el-button text size="small" @click="clearProfile" class="!text-gray-400 hover:!text-red-500">
              🗑 清空画像
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <div class="mt-6 bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm text-blue-700">
      <p class="font-medium mb-1">💡 匹配说明</p>
      <ul class="list-disc list-inside space-y-1 text-blue-600">
        <li><strong>规则匹配</strong>：基于学历、专业、关键词、地区、学校类型进行结构化匹配和打分</li>
        <li><strong>AI 增强匹配</strong>：规则匹配 + AI 语义重排，输出匹配理由和风险提示</li>
      </ul>
    </div>
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
  const user = { ...form }
  sessionStorage.setItem(MATCH_DATA_KEY, JSON.stringify({ user, useLlm }))
  router.push({ name: 'match' })
}
</script>
