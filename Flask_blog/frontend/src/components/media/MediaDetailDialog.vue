<template>
  <el-dialog
    v-model="dialogVisible"
    :title="media?.title || media?.original_name"
    width="800px"
    class="media-detail-dialog"
    @close="handleClose"
  >
    <div v-if="media" class="media-detail">
      <div class="detail-content">
        <div class="preview-section">
          <div class="media-preview">
            <img 
              v-if="media.media_type === 'image'" 
              :src="media.url" 
              :alt="media.alt_text"
              @load="handleImageLoad"
              @error="handleImageError"
            />
            <div v-else class="media-placeholder">
              <el-icon size="96" :component="getMediaIcon(media.media_type)" />
              <p>{{ getMediaTypeName(media.media_type) }}文件</p>
            </div>
          </div>
          
          <!-- 图片特有信息 -->
          <div v-if="media.media_type === 'image'" class="image-info">
            <div class="info-item">
              <span class="label">尺寸：</span>
              <span class="value">{{ media.width }} × {{ media.height }} 像素</span>
            </div>
            <div class="info-item" v-if="media.variants?.srcset">
              <span class="label">变体：</span>
              <span class="value">{{ getVariantsCount(media.variants) }} 个尺寸</span>
            </div>
          </div>
        </div>

        <div class="info-section">
          <div class="basic-info">
            <h3>基本信息</h3>
            
            <div class="info-grid">
              <div class="info-item">
                <span class="label">文件名：</span>
                <span class="value">{{ media.original_name }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">文件大小：</span>
                <span class="value">{{ formatFileSize(media.file_size) }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">文件类型：</span>
                <span class="value">{{ media.mime_type }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">媒体类型：</span>
                <span class="value">{{ getMediaTypeName(media.media_type) }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">可见性：</span>
                <el-tag :type="getVisibilityInfo(media.visibility).color" size="small">
                  {{ getVisibilityInfo(media.visibility).name }}
                </el-tag>
              </div>
              
              <div class="info-item">
                <span class="label">所有者：</span>
                <span class="value">{{ media.owner_name }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">上传时间：</span>
                <span class="value">{{ formatDate(media.created_at) }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">更新时间：</span>
                <span class="value">{{ formatDate(media.updated_at) }}</span>
              </div>
            </div>
          </div>

          <!-- 元数据信息 -->
          <div class="metadata-info">
            <h3>元数据</h3>
            
            <div class="info-item full-width" v-if="media.title">
              <span class="label">标题：</span>
              <span class="value">{{ media.title }}</span>
            </div>
            
            <div class="info-item full-width" v-if="media.alt_text">
              <span class="label">替代文本：</span>
              <span class="value">{{ media.alt_text }}</span>
            </div>
            
            <div class="info-item full-width" v-if="media.description">
              <span class="label">描述：</span>
              <span class="value">{{ media.description }}</span>
            </div>
            
            <div class="info-item full-width" v-if="media.tags?.length > 0">
              <span class="label">标签：</span>
              <div class="tags-list">
                <el-tag v-for="tag in media.tags" :key="tag" size="small" class="tag-item">
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 使用统计 -->
          <div class="usage-info">
            <h3>使用统计</h3>
            
            <div class="info-grid">
              <div class="info-item">
                <span class="label">下载次数：</span>
                <span class="value">{{ media.download_count || 0 }}</span>
              </div>
              
              <div class="info-item">
                <span class="label">引用次数：</span>
                <span class="value">{{ media.usage_count || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 技术信息 -->
          <div class="technical-info">
            <h3>技术信息</h3>
            
            <div class="info-grid">
              <div class="info-item">
                <span class="label">文件路径：</span>
                <span class="value code">{{ media.file_path }}</span>
              </div>
              
              <div class="info-item" v-if="media.file_hash">
                <span class="label">文件哈希：</span>
                <span class="value code">{{ media.file_hash }}</span>
              </div>
              
              <div class="info-item" v-if="media.media_type === 'image'">
                <span class="label">焦点坐标：</span>
                <span class="value">{{ media.focal_x?.toFixed(2) }}, {{ media.focal_y?.toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <!-- 变体信息 -->
          <div v-if="media.variants && Object.keys(media.variants).length > 0" class="variants-info">
            <h3>文件变体</h3>
            
            <div class="variants-list">
              <template v-if="media.variants.variants">
                <div 
                  v-for="variant in media.variants.variants" 
                  :key="variant.label"
                  class="variant-item"
                >
                  <div class="variant-label">{{ variant.label.toUpperCase() }}</div>
                  <div class="variant-info">
                    {{ variant.width }} × {{ variant.height }}
                  </div>
                  <div class="variant-actions">
                    <el-button 
                      text 
                      size="small" 
                      @click="copyUrl(variant.url)"
                    >
                      复制链接
                    </el-button>
                  </div>
                </div>
              </template>
              
              <div v-if="media.variants.webp" class="variant-item">
                <div class="variant-label">WebP</div>
                <div class="variant-info">优化格式</div>
                <div class="variant-actions">
                  <el-button 
                    text 
                    size="small" 
                    @click="copyUrl(media.variants.webp)"
                  >
                    复制链接
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="footer-left">
          <el-button @click="downloadMedia">
            <el-icon><Download /></el-icon>
            下载
          </el-button>
          <el-button @click="copyUrl(media?.url)">
            <el-icon><Link /></el-icon>
            复制链接
          </el-button>
        </div>
        
        <div class="footer-right">
          <el-button @click="editMedia">
            <el-icon><Edit /></el-icon>
            编辑信息
          </el-button>
          <el-button type="danger" @click="deleteMedia">
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
          <el-button @click="handleClose">关闭</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import mediaApi from '@/api/media'

export default {
  name: 'MediaDetailDialog',
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
  emits: ['update:visible', 'updated', 'deleted'],
  setup(props, { emit }) {
    const dialogVisible = computed({
      get: () => props.visible,
      set: (value) => emit('update:visible', value)
    })

    // 从 API 客户端获取辅助方法
    const { 
      formatFileSize, 
      getMediaTypeName, 
      getVisibilityInfo, 
      getMediaIcon 
    } = mediaApi

    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleString('zh-CN')
    }

    // 获取变体数量
    const getVariantsCount = (variants) => {
      if (!variants || !variants.variants) return 0
      return variants.variants.length
    }

    // 复制URL到剪贴板
    const copyUrl = async (url) => {
      if (!url) return
      
      try {
        const fullUrl = url.startsWith('http') ? url : `${window.location.origin}${url}`
        await navigator.clipboard.writeText(fullUrl)
        ElMessage.success('链接已复制到剪贴板')
      } catch (error) {
        console.error('复制失败:', error)
        ElMessage.error('复制链接失败')
      }
    }

    // 下载媒体文件
    const downloadMedia = async () => {
      if (!props.media) return
      
      try {
        const response = await mediaApi.downloadMedia(props.media.id)
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.download = props.media.original_name
        document.body.appendChild(link)
        link.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(link)
        ElMessage.success('下载成功')
      } catch (error) {
        console.error('下载失败:', error)
        ElMessage.error('下载失败')
      }
    }

    // 编辑媒体信息
    const editMedia = () => {
      emit('edit', props.media)
      handleClose()
    }

    // 删除媒体文件
    const deleteMedia = async () => {
      if (!props.media) return
      
      try {
        await ElMessageBox.confirm(
          `确定要删除"${props.media.original_name}"吗？此操作不可恢复。`,
          '确认删除',
          { type: 'warning' }
        )
        
        await mediaApi.deleteMedia(props.media.id)
        ElMessage.success('删除成功')
        emit('deleted')
        handleClose()
        
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除失败:', error)
          ElMessage.error('删除失败')
        }
      }
    }

    // 图片加载完成
    const handleImageLoad = (event) => {
      console.log('图片加载成功')
    }

    // 图片加载错误
    const handleImageError = (event) => {
      console.error('图片加载失败')
    }

    // 关闭对话框
    const handleClose = () => {
      dialogVisible.value = false
    }

    return {
      dialogVisible,
      formatFileSize,
      getMediaTypeName,
      getVisibilityInfo,
      getMediaIcon,
      formatDate,
      getVariantsCount,
      copyUrl,
      downloadMedia,
      editMedia,
      deleteMedia,
      handleImageLoad,
      handleImageError,
      handleClose
    }
  }
}
</script>

<style scoped>
.media-detail-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.detail-content {
  display: flex;
  height: 600px;
}

.preview-section {
  width: 300px;
  padding: 24px;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.media-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

.media-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.media-placeholder {
  text-align: center;
  color: #909399;
}

.media-placeholder p {
  margin-top: 12px;
  font-size: 14px;
}

.image-info .info-item {
  display: flex;
  margin-bottom: 8px;
}

.info-section {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.info-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.info-section > div {
  margin-bottom: 24px;
}

.info-section > div:last-child {
  margin-bottom: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: flex-start;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-item .label {
  min-width: 80px;
  color: #606266;
  font-size: 14px;
  margin-right: 12px;
}

.info-item .value {
  color: #303133;
  font-size: 14px;
  word-break: break-all;
}

.info-item .value.code {
  font-family: 'Courier New', monospace;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  margin: 0;
}

.variants-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.variant-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
}

.variant-label {
  min-width: 60px;
  font-weight: 600;
  color: #303133;
}

.variant-info {
  flex: 1;
  margin-left: 12px;
  color: #606266;
  font-size: 14px;
}

.variant-actions {
  margin-left: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
}

.footer-left,
.footer-right {
  display: flex;
  gap: 12px;
}
</style>