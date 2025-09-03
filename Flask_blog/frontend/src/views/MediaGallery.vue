<template>
  <div class="media-gallery">
    <!-- 页面头部 -->
    <div class="gallery-header">
      <div class="header-content">
        <h1 class="page-title">我的媒体库</h1>
        <p class="page-subtitle">管理和浏览我上传的媒体内容</p>
      </div>
      
      <!-- 搜索和筛选工具栏 -->
      <div class="search-toolbar">
        <div class="search-section">
          <el-input
            v-model="searchQuery"
            placeholder="搜索图片、视频..."
            style="width: 300px"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        
        <div class="filter-section">
          <el-select 
            v-model="selectedCategory" 
            placeholder="分类"
            style="width: 120px"
            clearable
            @change="handleCategoryChange"
          >
            <el-option label="全部" value="" />
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
            <el-option label="音频" value="audio" />
          </el-select>
          
          <el-select 
            v-model="sortBy" 
            placeholder="排序"
            style="width: 130px"
            @change="loadMediaData"
          >
            <el-option label="最新上传" value="created_at_desc" />
            <el-option label="最早上传" value="created_at_asc" />
            <el-option label="文件名 A-Z" value="name_asc" />
            <el-option label="文件名 Z-A" value="name_desc" />
            <el-option label="文件大小" value="size_desc" />
          </el-select>
          
          <el-button 
            type="primary"
            @click="showUploadDialog = true"
          >
            <el-icon><Upload /></el-icon>
            上传文件
          </el-button>
          
          <el-button-group>
            <el-button 
              :type="viewMode === 'grid' ? 'primary' : 'default'"
              @click="viewMode = 'grid'"
            >
              <el-icon><Grid /></el-icon>
            </el-button>
            <el-button 
              :type="viewMode === 'masonry' ? 'primary' : 'default'"
              @click="viewMode = 'masonry'"
            >
              <el-icon><Menu /></el-icon>
            </el-button>
          </el-button-group>
        </div>
      </div>
    </div>

    <!-- 媒体内容区 -->
    <div class="gallery-content" v-loading="loading">
      <!-- 网格视图 -->
      <div v-if="viewMode === 'grid'" class="media-grid">
        <div 
          v-for="media in mediaList" 
          :key="media.id"
          class="media-card"
          @click="openLightbox(media)"
        >
          <div class="card-image">
            <img 
              v-if="media.media_type === 'image'" 
              :src="getPreviewUrl(media)"
              :alt="media.alt_text || media.title"
              loading="lazy"
              @error="handleImageError"
            />
            <div v-else class="media-placeholder">
              <el-icon size="48" :component="getMediaIcon(media.media_type)" />
              <p class="placeholder-text">{{ getMediaTypeName(media.media_type) }}</p>
            </div>
            
            <!-- 媒体类型标识 -->
            <div class="media-type-badge">
              <el-tag 
                :type="getMediaTypeColor(media.media_type)" 
                size="small"
                effect="dark"
              >
                {{ getMediaTypeName(media.media_type) }}
              </el-tag>
            </div>
            
            <!-- 悬停信息 -->
            <div class="hover-overlay">
              <div class="hover-content">
                <h4 class="media-title">{{ media.title || media.original_name }}</h4>
                <div class="media-meta">
                  <span class="file-size">{{ formatFileSize(media.file_size) }}</span>
                  <span v-if="media.width && media.height" class="dimensions">
                    {{ media.width }}×{{ media.height }}
                  </span>
                </div>
                <div class="action-buttons">
                  <el-button size="small" type="primary" @click.stop="openLightbox(media)">
                    <el-icon><View /></el-icon>
                    查看
                  </el-button>
                  <el-button size="small" @click.stop="downloadMedia(media)">
                    <el-icon><Download /></el-icon>
                    下载
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          
          <div class="card-info">
            <h4 class="card-title" :title="media.title || media.original_name">
              {{ media.title || media.original_name }}
            </h4>
            <div class="card-meta">
              <span class="upload-date">{{ formatDate(media.created_at) }}</span>
              <span class="author">by {{ media.owner_name }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 瀑布流视图 -->
      <div v-else-if="viewMode === 'masonry'" class="media-masonry">
        <div 
          v-for="media in mediaList" 
          :key="media.id"
          class="masonry-item"
          @click="openLightbox(media)"
        >
          <div class="masonry-image">
            <img 
              v-if="media.media_type === 'image'" 
              :src="getPreviewUrl(media)"
              :alt="media.alt_text || media.title"
              loading="lazy"
              @error="handleImageError"
            />
            <div v-else class="media-placeholder">
              <el-icon size="64" :component="getMediaIcon(media.media_type)" />
              <p class="placeholder-text">{{ getMediaTypeName(media.media_type) }}</p>
            </div>
          </div>
          
          <div class="masonry-info">
            <h4 class="masonry-title">{{ media.title || media.original_name }}</h4>
            <p v-if="media.description" class="masonry-description">
              {{ media.description }}
            </p>
            <div class="masonry-meta">
              <span class="author">{{ media.owner_name }}</span>
              <span class="date">{{ formatDate(media.created_at) }}</span>
            </div>
            <div v-if="media.tags && media.tags.length > 0" class="masonry-tags">
              <el-tag 
                v-for="tag in media.tags.slice(0, 3)" 
                :key="tag" 
                size="small"
                class="tag-item"
              >
                {{ tag }}
              </el-tag>
              <span v-if="media.tags.length > 3" class="more-tags">
                +{{ media.tags.length - 3 }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- API不可用提示 -->
      <div v-if="!loading && apiError" class="api-error-state">
        <el-alert
          title="媒体库暂时不可用"
          type="warning"
          description="媒体库功能正在开发中，敬请期待！"
          show-icon
          :closable="false"
        >
          <template #default>
            <div class="error-actions">
              <el-button @click="testApiConnection">测试连接</el-button>
              <el-button @click="loadMediaData">重试</el-button>
              <el-button type="primary" @click="$router.push('/admin/media')" v-if="userStore.canAccessAdmin">
                前往管理控制台
              </el-button>
            </div>
          </template>
        </el-alert>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading && mediaList.length === 0" class="empty-state">
        <el-empty description="暂无媒体内容">
          <div class="empty-actions">
            <el-button @click="clearFilters">清除筛选条件</el-button>
            <el-button type="primary" @click="showUploadDialog = true">
              上传第一个文件
            </el-button>
            <el-button @click="loadMediaData">刷新数据</el-button>
          </div>
        </el-empty>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination-section">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[12, 24, 48, 96]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 图片灯箱 -->
    <el-dialog
      v-model="lightboxVisible"
      :title="currentMedia?.title || currentMedia?.original_name"
      width="90%"
      class="lightbox-dialog"
      @close="closeLightbox"
    >
      <div v-if="currentMedia" class="lightbox-content">
        <div class="lightbox-media">
          <img 
            v-if="currentMedia.media_type === 'image'" 
            :src="currentMedia.url"
            :alt="currentMedia.alt_text || currentMedia.title"
            class="lightbox-image"
          />
          <video 
            v-else-if="currentMedia.media_type === 'video'"
            :src="currentMedia.url"
            controls
            class="lightbox-video"
          >
            您的浏览器不支持视频播放
          </video>
          <audio 
            v-else-if="currentMedia.media_type === 'audio'"
            :src="currentMedia.url"
            controls
            class="lightbox-audio"
          >
            您的浏览器不支持音频播放
          </audio>
          <div v-else class="lightbox-placeholder">
            <el-icon size="96" :component="getMediaIcon(currentMedia.media_type)" />
            <p>{{ getMediaTypeName(currentMedia.media_type) }}文件</p>
          </div>
        </div>
        
        <div class="lightbox-info">
          <div class="media-details">
            <h3>{{ currentMedia.title || currentMedia.original_name }}</h3>
            
            <div v-if="currentMedia.description" class="description">
              <p>{{ currentMedia.description }}</p>
            </div>
            
            <div class="details-grid">
              <div class="detail-item">
                <strong>文件大小：</strong>
                <span>{{ formatFileSize(currentMedia.file_size) }}</span>
              </div>
              <div v-if="currentMedia.width && currentMedia.height" class="detail-item">
                <strong>尺寸：</strong>
                <span>{{ currentMedia.width }} × {{ currentMedia.height }} 像素</span>
              </div>
              <div class="detail-item">
                <strong>上传者：</strong>
                <span>{{ currentMedia.owner_name }}</span>
              </div>
              <div class="detail-item">
                <strong>上传时间：</strong>
                <span>{{ formatDateTime(currentMedia.created_at) }}</span>
              </div>
            </div>
            
            <div v-if="currentMedia.tags && currentMedia.tags.length > 0" class="tags-section">
              <strong>标签：</strong>
              <div class="tags-list">
                <el-tag 
                  v-for="tag in currentMedia.tags" 
                  :key="tag"
                  size="small"
                  class="tag-item"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="lightbox-actions">
          <el-button @click="downloadMedia(currentMedia)">
            <el-icon><Download /></el-icon>
            下载原图
          </el-button>
          <el-button @click="copyUrl(currentMedia?.url)">
            <el-icon><Link /></el-icon>
            复制链接
          </el-button>
          <el-button @click="closeLightbox">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 上传对话框 -->
    <MediaUploadDialog 
      v-model:visible="showUploadDialog"
      @uploaded="handleUploaded"
    />
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import mediaApi from '@/api/media'
import MediaUploadDialog from '@/components/media/MediaUploadDialog.vue'

export default {
  name: 'MediaGallery',
  components: {
    MediaUploadDialog
  },
  setup() {
    const router = useRouter()
    const userStore = useUserStore()
    const loading = ref(false)
    const mediaList = ref([])
    const searchQuery = ref('')
    const selectedCategory = ref('')
    const sortBy = ref('created_at_desc')
    const viewMode = ref('grid')
    
    // 分页
    const currentPage = ref(1)
    const pageSize = ref(24)
    const total = ref(0)
    
    // 灯箱
    const lightboxVisible = ref(false)
    const currentMedia = ref(null)
    
    // 上传对话框
    const showUploadDialog = ref(false)
    
    // API错误状态
    const apiError = ref(false)

    // 从 API 获取辅助方法
    const { 
      formatFileSize, 
      getMediaTypeName, 
      getMediaIcon 
    } = mediaApi

    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleDateString('zh-CN')
    }

    // 格式化完整日期时间
    const formatDateTime = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleString('zh-CN')
    }

    // 获取预览URL
    const getPreviewUrl = (media) => {
      if (media.variants?.variants?.find(v => v.label === 'medium')) {
        return media.variants.variants.find(v => v.label === 'medium').url
      }
      return media.url
    }

    // 获取媒体类型颜色
    const getMediaTypeColor = (type) => {
      const colorMap = {
        image: 'success',
        video: 'primary',
        audio: 'warning',
        document: 'info'
      }
      return colorMap[type] || 'default'
    }

    // 加载媒体数据
    const loadMediaData = async () => {
      try {
        loading.value = true
        apiError.value = false
        
        const params = {}
        
        // 只添加非空参数
        if (currentPage.value > 1) {
          params.page = currentPage.value
        }
        if (pageSize.value !== 20) {
          params.size = pageSize.value
        }
        if (searchQuery.value.trim()) {
          params.keyword = searchQuery.value.trim()
        }
        if (selectedCategory.value) {
          params.type = selectedCategory.value
        }

        const response = await mediaApi.getMediaList(params)
        
        // 处理不同的响应格式
        let actualData = response.data
        
        // 如果响应是 {code: 0, data: {...}} 格式，取出内层的data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        
        if (actualData) {
          if (actualData.items) {
            mediaList.value = actualData.items || []
            total.value = actualData.total || 0
          } else if (actualData.media) {
            mediaList.value = actualData.media || []
            total.value = actualData.total || 0
          } else if (Array.isArray(actualData)) {
            mediaList.value = actualData
            total.value = actualData.length
          } else {
            mediaList.value = []
            total.value = 0
          }
        } else {
          mediaList.value = []
          total.value = 0
        }

      } catch (error) {
        console.error('加载媒体数据失败:', error)
        console.error('错误详情:', error.response?.data)
        
        // 根据错误类型显示不同的提示信息
        if (error.response?.status === 404) {
          apiError.value = true
          ElMessage.error('媒体库接口不存在，请检查后端配置')
        } else if (error.response?.status === 401) {
          ElMessage.error('请先登录后访问媒体库')
        } else if (error.response?.status === 403) {
          ElMessage.error('没有权限访问媒体库')
        } else {
          apiError.value = true
          ElMessage.error(`加载媒体内容失败: ${error.response?.data?.message || error.message || '未知错误'}`)
        }
        
        mediaList.value = []
        total.value = 0
      } finally {
        loading.value = false
      }
    }

    // 搜索处理
    const handleSearch = () => {
      currentPage.value = 1
      loadMediaData()
    }

    // 分类筛选
    const handleCategoryChange = () => {
      currentPage.value = 1
      loadMediaData()
    }

    // 分页处理
    const handlePageChange = (page) => {
      currentPage.value = page
      loadMediaData()
    }

    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1
      loadMediaData()
    }

    // 打开灯箱
    const openLightbox = (media) => {
      currentMedia.value = media
      lightboxVisible.value = true
    }

    // 关闭灯箱
    const closeLightbox = () => {
      lightboxVisible.value = false
      currentMedia.value = null
    }

    // 下载媒体
    const downloadMedia = async (media) => {
      if (!media) return
      
      try {
        const response = await mediaApi.downloadMedia(media.id)
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.download = media.original_name
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

    // 复制URL
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

    // 清除筛选条件
    const clearFilters = () => {
      searchQuery.value = ''
      selectedCategory.value = ''
      sortBy.value = 'created_at_desc'
      currentPage.value = 1
      loadMediaData()
    }

    // 处理图片加载错误
    const handleImageError = (event) => {
      event.target.style.display = 'none'
    }

    // 处理上传成功
    const handleUploaded = async () => {
      showUploadDialog.value = false
      // 等待一小段时间确保后端处理完成
      setTimeout(async () => {
        await loadMediaData()
        ElMessage.success('文件上传成功！')
      }, 500)
    }


    // 初始化加载
    onMounted(async () => {
      // 检查用户是否已登录
      if (!userStore.isAuthenticated) {
        try {
          await userStore.initAuth()
        } catch (error) {
          ElMessage.error('请先登录后访问媒体库')
          router.push('/login')
          return
        }
      }
      
      loadMediaData()
    })

    return {
      loading,
      mediaList,
      searchQuery,
      selectedCategory,
      sortBy,
      viewMode,
      currentPage,
      pageSize,
      total,
      lightboxVisible,
      currentMedia,
      showUploadDialog,
      apiError,
      userStore,
      formatFileSize,
      getMediaTypeName,
      getMediaIcon,
      formatDate,
      formatDateTime,
      getPreviewUrl,
      getMediaTypeColor,
      loadMediaData,
      handleSearch,
      handleCategoryChange,
      handlePageChange,
      handleSizeChange,
      openLightbox,
      closeLightbox,
      downloadMedia,
      copyUrl,
      clearFilters,
      handleImageError,
      handleUploaded
    }
  }
}
</script>

<style scoped>
.media-gallery {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding-bottom: 60px;
}

.gallery-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 2rem 0;
  margin-bottom: 2rem;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  text-align: center;
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.page-subtitle {
  font-size: 1.1rem;
  color: #7f8c8d;
  margin: 0;
}

.search-toolbar {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.search-section,
.filter-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.gallery-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  min-height: 400px;
}

/* 网格视图 */
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.media-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
}

.media-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}

.card-image {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.media-card:hover .card-image img {
  transform: scale(1.05);
}

.media-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  color: #6c757d;
}

.placeholder-text {
  margin-top: 0.5rem;
  font-size: 0.9rem;
}

.media-type-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
}

.hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 3;
}

.media-card:hover .hover-overlay {
  opacity: 1;
}

.hover-content {
  text-align: center;
  color: white;
  padding: 1rem;
}

.media-title {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.media-meta {
  margin-bottom: 1rem;
  font-size: 0.9rem;
  opacity: 0.9;
}

.media-meta span {
  margin-right: 1rem;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.card-info {
  padding: 1.5rem;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #7f8c8d;
}

/* 瀑布流视图 */
.media-masonry {
  column-count: 3;
  column-gap: 2rem;
  column-fill: balance;
}

@media (max-width: 1024px) {
  .media-masonry {
    column-count: 2;
  }
}

@media (max-width: 768px) {
  .media-masonry {
    column-count: 1;
  }
}

.masonry-item {
  break-inside: avoid;
  margin-bottom: 2rem;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
}

.masonry-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

.masonry-image img {
  width: 100%;
  height: auto;
  display: block;
}

.masonry-info {
  padding: 1.5rem;
}

.masonry-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.masonry-description {
  color: #7f8c8d;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 1rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.masonry-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #95a5a6;
  margin-bottom: 1rem;
}

.masonry-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.tag-item {
  margin: 0;
}

.more-tags {
  font-size: 0.8rem;
  color: #95a5a6;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-actions {
  margin-top: 1rem;
}

.empty-actions .el-button + .el-button {
  margin-left: 1rem;
}

/* API错误状态 */
.api-error-state {
  padding: 2rem;
  text-align: center;
}

.error-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: center;
  gap: 1rem;
}

/* 分页 */
.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: 3rem;
  padding: 2rem;
}

/* 灯箱样式 */
.lightbox-dialog {
  --el-dialog-bg-color: rgba(0, 0, 0, 0.9);
}

.lightbox-dialog :deep(.el-dialog__header) {
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.lightbox-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.lightbox-content {
  display: flex;
  height: 70vh;
}

.lightbox-media {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: black;
}

.lightbox-image,
.lightbox-video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.lightbox-audio {
  width: 100%;
}

.lightbox-placeholder {
  color: white;
  text-align: center;
}

.lightbox-info {
  flex: 1;
  padding: 2rem;
  background: white;
  overflow-y: auto;
}

.lightbox-info h3 {
  color: #2c3e50;
  margin-bottom: 1rem;
}

.description {
  margin-bottom: 1.5rem;
  color: #7f8c8d;
  line-height: 1.6;
}

.details-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-item {
  display: flex;
}

.detail-item strong {
  min-width: 80px;
  color: #2c3e50;
}

.tags-section {
  margin-top: 1.5rem;
}

.tags-section strong {
  color: #2c3e50;
  margin-bottom: 0.5rem;
  display: block;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.lightbox-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1rem 2rem;
  background: white;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-section,
  .filter-section {
    justify-content: center;
  }
  
  .media-grid {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1.5rem;
  }
  
  .lightbox-content {
    flex-direction: column;
    height: auto;
  }
  
  .lightbox-media {
    height: 40vh;
  }
}
</style>