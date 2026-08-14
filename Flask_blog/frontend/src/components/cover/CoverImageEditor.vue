<template>
  <el-card class="cover-card" shadow="hover">
    <template #header>
      <h3 class="card-title">
        <el-icon class="title-icon"><Picture /></el-icon>
        封面图片
      </h3>
    </template>

    <div class="cover-section">
      <!-- 上传区域 -->
      <div class="upload-section">
        <el-form-item label="选择封面图">
          <div class="upload-area">
            <!-- 主要上传选项 -->
            <div class="primary-upload">
              <el-upload
                class="cover-uploader"
                action="#"
                :auto-upload="false"
                :on-change="handleCoverSelect"
                :show-file-list="false"
                accept="image/*"
                :disabled="uploading"
              >
                <el-button
                  type="primary"
                  size="large"
                  :loading="uploading"
                  :icon="uploading ? Loading : UploadFilled"
                >
                  {{ uploading ? '上传中...' : '上传新图片' }}
                </el-button>
              </el-upload>

              <div v-if="uploading" class="upload-progress">
                <el-progress :percentage="uploadProgress" />
              </div>
            </div>

            <!-- 分隔线 -->
            <div class="option-divider">
              <span class="divider-text">或</span>
            </div>

            <!-- 媒体库选择 -->
            <div class="media-library-option">
              <el-button
                type="success"
                size="large"
                :icon="Picture"
                :disabled="uploading"
                plain
                @click="showMediaSelector = true"
              >
                从媒体库选择
              </el-button>
              <div class="option-hint">
                选择已上传的图片作为封面
              </div>
            </div>
          </div>
          <div class="input-hint">
            <el-icon class="hint-icon"><InfoFilled /></el-icon>
            支持 JPG、PNG、WebP 格式，建议尺寸 1200x630 像素，文件大小不超过 5MB
          </div>
        </el-form-item>
      </div>

      <!-- URL输入作为高级选项 -->
      <div class="url-section">
        <el-collapse>
          <el-collapse-item title="高级选项：使用图片链接" name="url">
            <el-form-item label="封面图片URL">
              <el-input
                :model-value="image"
                placeholder="https://example.com/cover.jpg 或使用上传功能"
                size="large"
                clearable
                @update:model-value="emit('update:image', $event)"
              >
                <template #prefix>
                  <el-icon><Link /></el-icon>
                </template>
              </el-input>
              <div class="input-hint">
                直接输入图片网络地址，适合已有图片链接的用户
              </div>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 封面预览 -->
      <div v-if="image" class="cover-preview">
        <label class="preview-label">封面预览</label>
        <div class="preview-container">
          <CoverImage
            :src="image"
            alt="封面预览"
            container-class="preview-image-container"
            image-class="preview-image"
          />
        </div>
      </div>

      <!-- 焦点裁剪 -->
      <div v-if="image" class="focal-section">
        <ImageFocalCropper v-model="imageModel" @focal-change="onFocal" />
      </div>
    </div>

    <!-- 媒体选择器 -->
    <MediaSelector
      v-model:visible="showMediaSelector"
      :multiple="false"
      accept="image/*"
      @selected="handleMediaSelected"
    />
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Loading, UploadFilled, Link } from '@element-plus/icons-vue'
import { UploadsService } from '../../generated'
import CoverImage from '../CoverImage.vue'
import ImageFocalCropper from '../ImageFocalCropper.vue'
import MediaSelector from '../media/MediaSelector.vue'

const props = defineProps({
  image: { type: String, default: '' },
})

const emit = defineEmits(['update:image', 'focal-change'])

const imageModel = computed({
  get: () => props.image,
  set: (val) => emit('update:image', val),
})

// 上传状态
const uploading = ref(false)
const uploadProgress = ref(0)
const showMediaSelector = ref(false)

/** @param {import('element-plus').UploadFile} file */
async function handleCoverSelect(file) {
  if (!file || !file.raw) return

  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  if (!allowedTypes.includes(file.raw.type)) {
    ElMessage.warning('不支持的文件格式，请选择 JPG、PNG 或 WebP 格式的图片')
    return
  }

  const maxSize = 5 * 1024 * 1024
  if (file.raw.size > maxSize) {
    ElMessage.warning('文件过大，请选择小于 5MB 的图片')
    return
  }

  uploading.value = true
  uploadProgress.value = 0

  try {
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 100)

    const response = await UploadsService.postApiV1UploadsImage({
      file: file.raw
    })

    clearInterval(progressInterval)
    uploadProgress.value = 100

    if (response.data?.url) {
      emit('update:image', response.data.url)
      ElMessage.success({
        message: '🖼️ 封面图片上传成功！',
        duration: 3000
      })
    } else {
      ElMessage.error('上传成功但未获取到图片地址')
    }
  } catch (e) {
    console.error('Cover upload error:', e)
    const err = /** @type {{ response?: { data?: { message?: string } } }} */ (e)
    ElMessage.error(err.response?.data?.message || '封面图片上传失败，请稍后重试')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

/** @param {{ url?: string }} selectedMedia */
function handleMediaSelected(selectedMedia) {
  if (selectedMedia && selectedMedia.url) {
    emit('update:image', selectedMedia.url)
    ElMessage.success({
      message: '🖼️ 已从媒体库选择封面图片！',
      duration: 3000
    })
  }
  showMediaSelector.value = false
}

/** @param {{ x?: number, y?: number }} f */
function onFocal(f) {
  emit('focal-change', f)
}
</script>

<style scoped>
.cover-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.upload-area {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: flex-start;
}

.primary-upload {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.upload-progress {
  width: 200px;
}

.option-divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #9ca3af;
  font-size: 0.875rem;
}

.divider-text {
  padding: 0 0.5rem;
}

.option-hint {
  color: #9ca3af;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.cover-preview {
  margin-top: 0.5rem;
}

.preview-label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #374151;
}

.input-hint {
  color: #6b7280;
  font-size: 0.875rem;
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
</style>
