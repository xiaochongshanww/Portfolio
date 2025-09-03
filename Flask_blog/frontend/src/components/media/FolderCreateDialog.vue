<template>
  <el-dialog
    v-model="dialogVisible"
    title="新建文件夹"
    width="400px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
    >
      <el-form-item label="文件夹名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入文件夹名称"
          maxlength="50"
          show-word-limit
          @keyup.enter="handleSubmit"
        />
      </el-form-item>
      
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="请输入文件夹描述（可选）"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
      
      <el-form-item label="可见性" prop="visibility">
        <el-radio-group v-model="form.visibility">
          <el-radio label="private">
            <div class="radio-option">
              <div class="radio-title">
                <el-icon><Lock /></el-icon>
                私有
              </div>
              <div class="radio-desc">仅您可以访问</div>
            </div>
          </el-radio>
          
          <el-radio label="shared">
            <div class="radio-option">
              <div class="radio-title">
                <el-icon><Share /></el-icon>
                共享
              </div>
              <div class="radio-desc">编辑者及以上角色可访问</div>
            </div>
          </el-radio>
          
          <el-radio label="public">
            <div class="radio-option">
              <div class="radio-title">
                <el-icon><View /></el-icon>
                公开
              </div>
              <div class="radio-desc">所有登录用户都可访问</div>
            </div>
          </el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          创建
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import mediaApi from '@/api/media'

export default {
  name: 'FolderCreateDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    parentFolderId: {
      type: Number,
      default: null
    }
  },
  emits: ['update:visible', 'created'],
  setup(props, { emit }) {
    const formRef = ref()
    const loading = ref(false)
    
    const form = reactive({
      name: '',
      description: '',
      visibility: 'private'
    })

    const rules = {
      name: [
        { required: true, message: '请输入文件夹名称', trigger: 'blur' },
        { min: 1, max: 50, message: '文件夹名称长度在 1 到 50 个字符', trigger: 'blur' },
        {
          pattern: /^[^\/\\:*?"<>|]+$/,
          message: '文件夹名称不能包含特殊字符 / \\ : * ? " < > |',
          trigger: 'blur'
        }
      ],
      description: [
        { max: 200, message: '描述不能超过 200 个字符', trigger: 'blur' }
      ],
      visibility: [
        { required: true, message: '请选择可见性', trigger: 'change' }
      ]
    }

    const dialogVisible = computed({
      get: () => props.visible,
      set: (value) => emit('update:visible', value)
    })

    // 提交表单
    const handleSubmit = async () => {
      try {
        await formRef.value.validate()
        
        loading.value = true
        
        const data = {
          name: form.name,
          description: form.description,
          visibility: form.visibility,
          parent_id: props.parentFolderId
        }

        await mediaApi.createFolder(data)
        
        ElMessage.success('文件夹创建成功')
        emit('created')
        handleClose()
        
      } catch (error) {
        if (error.response?.data?.message) {
          ElMessage.error(error.response.data.message)
        } else {
          ElMessage.error('创建文件夹失败')
        }
        console.error('创建文件夹失败:', error)
      } finally {
        loading.value = false
      }
    }

    // 关闭对话框
    const handleClose = () => {
      form.name = ''
      form.description = ''
      form.visibility = 'private'
      formRef.value?.clearValidate()
      dialogVisible.value = false
    }

    return {
      formRef,
      loading,
      form,
      rules,
      dialogVisible,
      handleSubmit,
      handleClose
    }
  }
}
</script>

<style scoped>
.radio-option {
  width: 100%;
}

.radio-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.radio-desc {
  font-size: 12px;
  color: #909399;
  margin-left: 24px;
}

:deep(.el-radio) {
  margin-bottom: 16px;
  width: 100%;
}

:deep(.el-radio__label) {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>