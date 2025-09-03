<template>
  <el-dialog
    v-model="dialogVisible"
    title="上传媒体文件"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="upload-dialog">
      <!-- 上传区域 -->
      <div class="upload-area">
        <el-upload
          ref="uploadRef"
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :on-progress="handleUploadProgress"
          :before-upload="beforeUpload"
          :show-file-list="false"
          drag
          multiple
          accept="image/*"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 JPG、PNG、WebP 格式，单个文件不超过 2MB
            </div>
          </template>
        </el-upload>
      </div>

      <!-- 文件列表 -->
      <div class="file-list" v-if="fileList.length > 0">
        <div class="list-header">
          <span>上传文件 ({{ fileList.length }})</span>
          <el-button text @click="clearFiles">清空</el-button>
        </div>
        
        <div class="file-items">
          <div 
            v-for="(file, index) in fileList" 
            :key="index"
            class="file-item"
          >
            <div class="file-preview">
              <img v-if="file.preview" :src="file.preview" />
              <el-icon v-else size="32"><Document /></el-icon>
            </div>
            
            <div class="file-info">
              <div class="file-name">{{ file.name }}</div>
              <div class="file-meta">
                {{ formatFileSize(file.size) }}
                <span v-if="file.dimensions"> • {{ file.dimensions }}</span>
              </div>
            </div>
            
            <div class="file-status">
              <div v-if="file.status === 'uploading'" class="uploading">
                <el-progress 
                  :percentage="file.progress" 
                  :show-text="false"
                  :stroke-width="3"
                />
                <span class="progress-text">{{ file.progress }}%</span>
              </div>
              <el-icon v-else-if="file.status === 'success'" color="#67c23a" size="20">
                <CircleCheck />
              </el-icon>
              <el-icon v-else-if="file.status === 'error'" color="#f56c6c" size="20">
                <CircleClose />
              </el-icon>
              <el-icon v-else color="#909399" size="20">
                <Clock />
              </el-icon>
            </div>
            
            <div class="file-actions">
              <el-button 
                text 
                @click="removeFile(index)"
                :disabled="file.status === 'uploading'"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 上传设置 -->
      <div class="upload-settings">
        <el-form :model="uploadSettings" label-width="80px">
          <el-form-item label="目标文件夹">
            <el-select 
              v-model="uploadSettings.folderId" 
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
          
          <el-form-item label="可见性">
            <el-radio-group v-model="uploadSettings.visibility">
              <el-radio label="private">私有</el-radio>
              <el-radio label="shared">共享</el-radio>
              <el-radio label="public">公开</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="标签">
            <el-select
              v-model="uploadSettings.tags"
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
        </el-form>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button 
          type="primary" 
          @click="startUpload"
          :loading="uploading"
          :disabled="fileList.length === 0"
        >
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch, inject } from 'vue'
import { ElMessage } from 'element-plus'
import mediaApi from '@/api/media'

export default {
  name: 'MediaUploadDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    currentFolderId: {
      type: Number,
      default: null
    }
  },
  emits: ['update:visible', 'uploaded'],
  setup(props, { emit }) {
    const uploadRef = ref()
    const fileList = ref([])
    const uploading = ref(false)
    const availableFolders = ref([])
    const availableTags = ref([])
    
    const uploadSettings = ref({
      folderId: props.currentFolderId,
      visibility: 'private',
      tags: []
    })

    // 监听currentFolderId变化
    watch(() => props.currentFolderId, (newValue) => {
      uploadSettings.value.folderId = newValue
    })

    // 从全局状态获取认证信息
    const token = inject('token') || localStorage.getItem('access_token') // 修正token字段名
    
    const dialogVisible = computed({
      get: () => props.visible,
      set: (value) => emit('update:visible', value)
    })

    const uploadUrl = computed(() => {
      return `${import.meta.env.VITE_API_BASE_URL}/api/v1/media/upload`
    })

    const uploadHeaders = computed(() => {
      return {
        'Authorization': `Bearer ${token}`
      }
    })

    const uploadData = computed(() => {
      return {
        folder_id: uploadSettings.value.folderId,
        visibility: uploadSettings.value.visibility,
        tags: JSON.stringify(uploadSettings.value.tags)
      }
    })

    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    // 生成文件预览
    const generatePreview = (file) => {
      return new Promise((resolve) => {
        if (file.type.startsWith('image/')) {
          const reader = new FileReader()
          reader.onload = (e) => resolve(e.target.result)
          reader.readAsDataURL(file)
        } else {
          resolve(null)
        }
      })
    }

    // 获取图片尺寸
    const getImageDimensions = (file) => {
      return new Promise((resolve) => {
        if (file.type.startsWith('image/')) {
          const img = new Image()
          img.onload = () => {
            resolve(`${img.width} × ${img.height}`)
          }
          img.src = URL.createObjectURL(file)
        } else {
          resolve(null)
        }
      })
    }

    // 上传前检查
    const beforeUpload = async (file) => {
      // 检查文件类型
      const isImage = file.type.startsWith('image/')
      if (!isImage) {
        ElMessage.error('只能上传图片文件')
        return false
      }

      // 检查文件大小
      const isLt2M = file.size / 1024 / 1024 < 2
      if (!isLt2M) {
        ElMessage.error('文件大小不能超过 2MB')
        return false
      }

      // 生成预览和获取尺寸
      const [preview, dimensions] = await Promise.all([
        generatePreview(file),
        getImageDimensions(file)
      ])

      // 添加到文件列表
      const fileItem = {
        name: file.name,
        size: file.size,
        type: file.type,
        file: file,
        preview: preview,
        dimensions: dimensions,
        status: 'ready',
        progress: 0
      }
      
      fileList.value.push(fileItem)

      // 阻止自动上传
      return false
    }

    // 开始上传
    const startUpload = async () => {
      if (fileList.value.length === 0) return

      uploading.value = true
      let successCount = 0
      let errorCount = 0

      for (const fileItem of fileList.value) {
        if (fileItem.status === 'success') {
          successCount++
          continue
        }

        try {
          fileItem.status = 'uploading'
          fileItem.progress = 0

          const formData = new FormData()
          formData.append('file', fileItem.file)
          formData.append('folder_id', uploadSettings.value.folderId || '')
          formData.append('visibility', uploadSettings.value.visibility)
          formData.append('tags', JSON.stringify(uploadSettings.value.tags))

          // 模拟上传进度
          const progressInterval = setInterval(() => {
            if (fileItem.progress < 90) {
              fileItem.progress += Math.random() * 30
              if (fileItem.progress > 90) fileItem.progress = 90
            }
          }, 200)

          const response = await mediaApi.uploadMedia(formData)
          
          clearInterval(progressInterval)
          fileItem.progress = 100
          fileItem.status = 'success'
          fileItem.response = response.data
          successCount++

        } catch (error) {
          fileItem.status = 'error'
          fileItem.error = error
          errorCount++
          console.error(`文件 ${fileItem.name} 上传失败:`, error)
        }
      }

      uploading.value = false

      if (errorCount === 0) {
        ElMessage.success(`成功上传 ${successCount} 个文件`)
        emit('uploaded')
        handleClose()
      } else if (successCount > 0) {
        ElMessage.warning(`上传完成：成功 ${successCount} 个，失败 ${errorCount} 个`)
        emit('uploaded')
      } else {
        ElMessage.error(`上传失败，共 ${errorCount} 个文件`)
      }
    }

    // 移除文件
    const removeFile = (index) => {
      fileList.value.splice(index, 1)
    }

    // 清空文件列表
    const clearFiles = () => {
      fileList.value = []
    }

    // 处理上传成功（暂不使用，因为我们自定义了上传流程）
    const handleUploadSuccess = () => {}

    // 处理上传错误
    const handleUploadError = (error) => {
      console.error('上传错误:', error)
    }

    // 处理上传进度
    const handleUploadProgress = () => {}

    // 关闭对话框
    const handleClose = () => {
      if (!uploading.value) {
        fileList.value = []
        uploadSettings.value = {
          folderId: null,
          visibility: 'private',
          tags: []
        }
        dialogVisible.value = false
      }
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

    // 监听对话框显示状态
    watch(() => props.visible, (visible) => {
      if (visible) {
        uploadSettings.value.folderId = props.currentFolderId
        loadAvailableFolders()
      }
    })

    return {
      uploadRef,
      dialogVisible,
      fileList,
      uploading,
      availableFolders,
      availableTags,
      uploadSettings,
      uploadUrl,
      uploadHeaders,
      uploadData,
      formatFileSize,
      beforeUpload,
      startUpload,
      removeFile,
      clearFiles,
      handleUploadSuccess,
      handleUploadError,
      handleUploadProgress,
      handleClose
    }
  }
}
</script>

<style scoped>
.upload-dialog {
  max-height: 70vh;
  overflow-y: auto;
}

.upload-area {
  margin-bottom: 24px;
}

.file-list {
  margin-bottom: 24px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 500;
}

.file-items {
  max-height: 300px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.file-item:last-child {
  border-bottom: none;
}

.file-preview {
  width: 48px;
  height: 48px;
  margin-right: 12px;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-info {
  flex: 1;
  min-width: 0;
  margin-right: 12px;
}

.file-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 12px;
  color: #909399;
}

.file-status {
  width: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}

.uploading {
  display: flex;
  align-items: center;
  gap: 8px;
}

.uploading .el-progress {
  width: 40px;
}

.progress-text {
  font-size: 12px;
  color: #409eff;
}

.file-actions {
  flex-shrink: 0;
}

.upload-settings {
  border-top: 1px solid #e4e7ed;
  padding-top: 24px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>