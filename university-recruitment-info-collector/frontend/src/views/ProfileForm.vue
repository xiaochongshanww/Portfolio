<template>
  <div style="max-width: 720px; margin: 0 auto;">
    <h3>我的求职画像</h3>
    <el-form :model="form" label-width="140px" size="large">
      <el-form-item label="最高学历" required>
        <el-select v-model="form.education" placeholder="请选择" style="width: 100%">
          <el-option label="博士" value="博士" />
          <el-option label="硕士" value="硕士" />
          <el-option label="本科" value="本科" />
        </el-select>
      </el-form-item>

      <el-form-item label="专业" required>
        <el-input v-model="form.major" placeholder="如：计算机科学与技术" />
      </el-form-item>

      <el-form-item label="研究方向">
        <el-input v-model="form.research_direction" placeholder="如：人工智能" />
      </el-form-item>

      <el-form-item label="个人关键词">
        <el-select
          v-model="form.keywords"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入关键词后回车"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="期望地区">
        <el-select
          v-model="form.target_locations"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如：广州"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="期望学校类型">
        <el-select
          v-model="form.target_school_types"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如：双一流"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="岗位偏好">
        <el-select
          v-model="form.job_preferences"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如：教学科研岗"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="限制条件">
        <el-select
          v-model="form.constraints"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如：编制"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item>
        <div style="display: flex; gap: 12px;">
          <el-button type="primary" @click="submitMatch(false)" :loading="submitting">
            规则匹配
          </el-button>
          <el-button type="success" @click="submitMatch(true)" :loading="submitting">
            LLM 深度匹配
          </el-button>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const submitting = ref(false)

const form = reactive({
  education: '',
  major: '',
  research_direction: '',
  keywords: [],
  target_locations: [],
  target_school_types: [],
  job_preferences: [],
  constraints: [],
})

function submitMatch(useLlm) {
  if (!form.education || !form.major) {
    ElMessage.warning('请填写最高学历和专业')
    return
  }
  submitting.value = true
  const user = { ...form }
  router.push({
    name: 'match',
    query: { data: JSON.stringify(user), use_llm: useLlm ? '1' : '0' },
  })
}
</script>
