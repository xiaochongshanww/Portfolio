<template>
  <el-dialog
    :model-value="visible"
    title="创建新备份"
    width="600px"
    :z-index="9999"
    append-to-body
    @update:model-value="emit('update:visible', $event)"
    @close="resetForm"
  >
    <el-form
      :model="form"
      :rules="rules"
      label-width="120px"
    >
      <el-form-item label="备份类型" prop="backup_type">
        <el-select v-model="form.backup_type" placeholder="请选择备份类型">
          <el-option label="全量备份" value="full">
            <div class="option-detail">
              <div>全量备份</div>
              <div class="option-desc">完整备份所有数据和文件</div>
            </div>
          </el-option>
          <el-option label="增量备份" value="incremental">
            <div class="option-detail">
              <div>增量备份</div>
              <div class="option-desc">仅备份自上次备份后的更改</div>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="备份内容">
        <div class="backup-options">
          <el-checkbox v-model="form.include_database">
            <div class="option-detail">
              <div>数据库</div>
              <div class="option-desc">包含所有数据库表和数据</div>
            </div>
          </el-checkbox>
          <el-checkbox v-model="form.include_files">
            <div class="option-detail">
              <div>文件系统</div>
              <div class="option-desc">包含上传的文件和静态资源</div>
            </div>
          </el-checkbox>
        </div>
      </el-form-item>

      <el-form-item label="备份描述">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="请输入备份描述信息（可选）"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="creating" @click="emit('submit', form)">
        {{ creating ? '创建中...' : '创建备份' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive } from 'vue'

defineProps({
  visible: { type: Boolean, default: false },
  creating: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'submit'])

const form = reactive({
  backup_type: 'full',
  include_database: true,
  include_files: true,
  description: ''
})

const rules = {
  backup_type: [
    { required: true, message: '请选择备份类型', trigger: 'change' }
  ]
}

function resetForm() {
  Object.assign(form, {
    backup_type: 'full',
    include_database: true,
    include_files: true,
    description: ''
  })
}
</script>
