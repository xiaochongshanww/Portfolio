<template>
  <el-dialog
    v-model="dialogVisible"
    title="编辑媒体信息"
    width="600px"
    @close="handleClose"
  >
    <el-form
      v-if="media"
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <!-- 文件预览 -->
      <div class="media-preview-section">
        <div class="preview-container">
          <img 
            v-if="media.media_type === 'image'" 
            :src="media.url" 
            :alt="form.alt_text"
            class="preview-image"
          />
          <div v-else class="preview-placeholder">
            <el-icon size="48" :component="getMediaIcon(media.media_type)" />
            <p>{{ media.original_name }}</p>
          </div>
        </div>
        
        <div class="preview-info">
          <p class="file-name">{{ media.original_name }}</p>
          <p class="file-meta">
            {{ formatFileSize(media.file_size) }} • 
            {{ getMediaTypeName(media.media_type) }}
            <span v-if="media.width && media.height"> • {{ media.width }} × {{ media.height }}</span>
          </p>
        </div>
      </div>

      <!-- 基本信息 -->
      <el-form-item label="标题" prop="title">
        <el-input
          v-model="form.title"
          placeholder="请输入媒体标题"
          maxlength="100"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="替代文本" prop="alt_text" v-if="media.media_type === 'image'">
        <el-input
          v-model="form.alt_text"
          placeholder="用于描述图片内容，提升无障碍访问体验"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="请输入媒体描述"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="标签" prop="tags">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          placeholder="输入或选择标签"
          style="width: 100%"
        >
          <el-option
            v-for="tag in availableTags"
            :key="tag"
            :label="tag"
            :value="tag"
          />
        </el-select>
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

      <el-form-item label="文件夹" prop="folder_id">
        <el-select 
          v-model="form.folder_id" 
          placeholder="选择文件夹"
          clearable
          style="width: 100%"
        >
          <el-option label="根目录" :value="null" />
          <el-option 
            v-for="folder in availableFolders"
            :key="folder.id"
            :label="folder.name"
            :value="folder.id"
          />
        </el-select>
      </el-form-item>

      <!-- 图片特有字段：焦点坐标 -->
      <template v-if="media.media_type === 'image'">
        <el-form-item label="焦点坐标">
          <div class="focal-point-section">
            <div class="focal-point-inputs">
              <div class="input-group">
                <label>X坐标：</label>
                <el-input-number
                  v-model="form.focal_x"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :precision="2"
                  size="small"
                  style="width: 120px"
                />
              </div>
              <div class="input-group">
                <label>Y坐标：</label>
                <el-input-number
                  v-model="form.focal_y"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :precision="2"
                  size="small"
                  style="width: 120px"
                />
              </div>
            </div>
            <div class="focal-point-help">
              <el-text size="small" type="info">
                焦点坐标用于智能裁剪，(0,0)为左上角，(1,1)为右下角
              </el-text>
            </div>
          </div>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          保存
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import mediaApi from '@/api/media'

export default {
  name: 'MediaEditDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    media: {
      type: Object,
      default: null
    }
  },
  emits: ['update:visible', 'updated'],
  setup(props, { emit }) {
    const formRef = ref()
    const loading = ref(false)
    const availableFolders = ref([])
    const availableTags = ref([])
    
    const form = reactive({
      title: '',
      alt_text: '',
      description: '',
      tags: [],
      visibility: 'private',
      folder_id: null,
      focal_x: 0.5,
      focal_y: 0.5
    })

    const rules = {
      title: [
        { max: 100, message: '标题不能超过 100 个字符', trigger: 'blur' }
      ],
      alt_text: [
        { max: 200, message: '替代文本不能超过 200 个字符', trigger: 'blur' }
      ],
      description: [
        { max: 500, message: '描述不能超过 500 个字符', trigger: 'blur' }
      ],
      visibility: [
        { required: true, message: '请选择可见性', trigger: 'change' }
      ]
    }

    const dialogVisible = computed({
      get: () => props.visible,
      set: (value) => emit('update:visible', value)
    })

    // 从 API 客户端获取辅助方法
    const { formatFileSize, getMediaTypeName, getMediaIcon } = mediaApi

    // 初始化表单数据
    const initForm = () => {
      if (!props.media) return
      
      form.title = props.media.title || ''
      form.alt_text = props.media.alt_text || ''
      form.description = props.media.description || ''
      form.tags = props.media.tags || []
      form.visibility = props.media.visibility || 'private'
      form.folder_id = props.media.folder_id
      form.focal_x = props.media.focal_x ?? 0.5
      form.focal_y = props.media.focal_y ?? 0.5
    }

    // 加载可用文件夹
    const loadAvailableFolders = async () => {
      try {
        const response = await mediaApi.getFolders()
        availableFolders.value = response.data
      } catch (error) {
        console.error('加载文件夹失败:', error)
      }
    }

    // 提交表单
    const handleSubmit = async () => {
      try {
        await formRef.value.validate()
        
        loading.value = true
        
        const updateData = {
          title: form.title,
          alt_text: form.alt_text,
          description: form.description,
          tags: form.tags,
          visibility: form.visibility,
          folder_id: form.folder_id,
          focal_x: form.focal_x,
          focal_y: form.focal_y
        }

        await mediaApi.updateMedia(props.media.id, updateData)
        
        ElMessage.success('媒体信息更新成功')
        emit('updated')
        handleClose()
        
      } catch (error) {
        if (error.response?.data?.message) {
          ElMessage.error(error.response.data.message)
        } else {
          ElMessage.error('更新失败')
        }
        console.error('更新媒体信息失败:', error)
      } finally {
        loading.value = false
      }
    }

    // 关闭对话框
    const handleClose = () => {
      formRef.value?.clearValidate()
      dialogVisible.value = false
    }

    // 监听媒体数据变化
    watch(() => props.media, (newMedia) => {
      if (newMedia) {
        initForm()
      }
    }, { immediate: true })

    // 监听对话框显示状态
    watch(() => props.visible, (visible) => {
      if (visible) {
        initForm()
        loadAvailableFolders()
      }
    })

    return {
      formRef,
      loading,
      availableFolders,
      availableTags,
      form,
      rules,
      dialogVisible,
      formatFileSize,
      getMediaTypeName,
      getMediaIcon,
      handleSubmit,
      handleClose
    }
  }
}
</script>

<style scoped>
.media-preview-section {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.preview-container {
  width: 80px;
  height: 80px;
  margin-right: 16px;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-placeholder {
  text-align: center;
  color: #909399;
  font-size: 12px;
}

.preview-placeholder p {
  margin-top: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 60px;
}

.preview-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: #303133;
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

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

.focal-point-section {
  width: 100%;
}

.focal-point-inputs {
  display: flex;
  gap: 24px;
  margin-bottom: 8px;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-group label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.focal-point-help {
  margin-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>