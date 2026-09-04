<template>
  <div class="media-page">
    <!-- 页头 -->
    <section class="page-head">
      <div class="eyebrow">媒体库</div>
      <h1>我的媒体库</h1>
      <p>管理和浏览我上传的媒体内容。</p>
    </section>

    <!-- 工具栏 -->
    <section class="toolbar">
      <div class="toolbar-filters">
        <el-input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索文件名、标题..."
          clearable
          @input="handleSearch"
        />
        <el-select
          v-model="selectedCategory"
          class="type-select"
          placeholder="类型"
          clearable
          @change="handleCategoryChange"
        >
          <el-option label="全部类型" value="" />
          <el-option label="图片" value="image" />
          <el-option label="视频" value="video" />
          <el-option label="音频" value="audio" />
        </el-select>
        <el-select
          v-model="sortBy"
          class="sort-select"
          placeholder="排序"
          @change="loadMediaData"
        >
          <el-option label="最新上传" value="created_at_desc" />
          <el-option label="最早上传" value="created_at_asc" />
          <el-option label="文件名 A-Z" value="name_asc" />
          <el-option label="文件名 Z-A" value="name_desc" />
          <el-option label="文件大小" value="size_desc" />
        </el-select>
      </div>
      <div class="toolbar-actions">
        <span class="result-count">共 {{ total }} 个文件</span>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
      </div>
    </section>

    <!-- 加载中 -->
    <section v-if="loading" class="state-section">
      <el-skeleton :rows="6" animated />
    </section>

    <!-- API 不可用 -->
    <section v-else-if="apiError" class="state-section">
      <div class="state-block">
        <p class="state-title">媒体库暂时不可用</p>
        <p>媒体服务暂未连接,请检查后稍后重试。</p>
        <div class="state-actions">
          <button type="button" class="ghost-btn" @click="testApiConnection">测试连接</button>
          <button type="button" class="ghost-btn" @click="loadMediaData">重试</button>
          <button
            v-if="userStore.canAccessAdmin"
            type="button"
            class="ghost-btn"
            @click="$router.push('/admin/media')"
          >
            前往管理控制台
          </button>
        </div>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else-if="mediaList.length === 0" class="state-section">
      <div class="state-block">
        <p class="state-title">暂无媒体内容</p>
        <p>上传第一个文件,或调整筛选条件。</p>
        <div class="state-actions">
          <button type="button" class="ghost-btn" @click="clearFilters">清除筛选条件</button>
          <button type="button" class="ghost-btn primary" @click="showUploadDialog = true">上传第一个文件</button>
          <button type="button" class="ghost-btn" @click="loadMediaData">刷新</button>
        </div>
      </div>
    </section>

    <!-- 媒体网格 -->
    <section v-else class="media-grid">
      <div
        v-for="media in mediaList"
        :key="media.id"
        class="media-card"
        @click="openLightbox(media)"
      >
        <div class="card-thumb">
          <img
            v-if="media.media_type === 'image'"
            :src="getPreviewUrl(media)"
            :alt="(media.alt_text || media.title) || ''"
            loading="lazy"
            @error="handleImageError"
          >
          <div v-else class="thumb-placeholder">
            <el-icon size="34" :component="getMediaIcon(media.media_type)" />
            <span>{{ getMediaTypeName(media.media_type) }}</span>
          </div>

          <div class="thumb-overlay">
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

        <div class="card-copy">
          <b class="card-title" :title="media.title || media.original_name">
            {{ media.title || media.original_name }}
          </b>
          <span class="card-meta">
            {{ formatFileSize(media.file_size) }}
            <template v-if="media.width && media.height"> · {{ media.width }}×{{ media.height }}</template>
            · {{ formatDate(media.created_at) }}
          </span>
        </div>
      </div>
    </section>

    <!-- 分页 -->
    <div v-if="!loading && !apiError && total > pageSize" class="pager">
      <button type="button" class="ghost-btn" :disabled="currentPage === 1" @click="goPage(currentPage - 1)">‹ 上一页</button>
      <span class="pager-info">{{ currentPage }} / {{ totalPages }}</span>
      <button type="button" class="ghost-btn" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页 ›</button>
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
          >
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
          <h3>{{ currentMedia.title || currentMedia.original_name }}</h3>

          <p v-if="currentMedia.description" class="lightbox-description">
            {{ currentMedia.description }}
          </p>

          <div class="details-grid">
            <div class="detail-item">
              <span class="detail-label">文件大小</span>
              <span>{{ formatFileSize(currentMedia.file_size) }}</span>
            </div>
            <div v-if="currentMedia.width && currentMedia.height" class="detail-item">
              <span class="detail-label">尺寸</span>
              <span>{{ currentMedia.width }} × {{ currentMedia.height }} 像素</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">上传者</span>
              <span>{{ currentMedia.owner_name }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">上传时间</span>
              <span>{{ formatDateTime(currentMedia.created_at) }}</span>
            </div>
          </div>

          <div v-if="currentMedia.tags && currentMedia.tags.length > 0" class="tags-section">
            <span class="detail-label">标签</span>
            <div class="tags-list">
              <span v-for="tag in currentMedia.tags" :key="tag" class="tag-chip">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="lightbox-actions">
          <el-button @click="downloadMedia(currentMedia)">
            <el-icon><Download /></el-icon>
            下载原文件
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
/**
 * 媒体库(V2 重构,原型 media-gallery-v1)
 * 结构:PageHead + Toolbar + Media Grid + 四态 + Pager;灯箱与上传对话框保留。
 * 视觉走公开站 token(--bg/--surface/--text/--muted/--line),克制 hover,无渐变。
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { API } from '@/api'
import { formatFileSize, getMediaTypeName, getMediaIcon } from '@/utils/mediaUtils'
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
    /** @type {import('vue').Ref<import('@/types').MediaFile[]>} */
    const mediaList = ref([])
    const searchQuery = ref('')
    const selectedCategory = ref('')
    const sortBy = ref('created_at_desc')

    // 分页
    const currentPage = ref(1)
    const pageSize = ref(24)
    const total = ref(0)
    const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

    // 灯箱
    const lightboxVisible = ref(false)
    /** @type {import('vue').Ref<import('@/types').MediaFile | null>} */
    const currentMedia = ref(null)

    // 上传对话框
    const showUploadDialog = ref(false)

    // API错误状态
    const apiError = ref(false)

    // 格式化日期
    /** @param {string | undefined} dateStr */
    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleDateString('zh-CN')
    }

    // 格式化完整日期时间
    /** @param {string | undefined} dateStr */
    const formatDateTime = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleString('zh-CN')
    }

    // 获取预览URL
    /** @param {import('@/types').MediaFile} media
     * @returns {string} */
    const getPreviewUrl = (media) => {
      const medium = media.variants?.variants?.find(v => v.label === 'medium')
      if (medium && medium.url) {
        return medium.url
      }
      return media.url || ''
    }

    // 加载媒体数据
    const loadMediaData = async () => {
      try {
        loading.value = true
        apiError.value = false

        /** @type {Record<string, unknown>} */
        const params = {}

        // 只添加非空参数
        if (currentPage.value > 1) {
          params.page = currentPage.value
        }
        if (searchQuery.value.trim()) {
          params.keyword = searchQuery.value.trim()
        }
        if (selectedCategory.value) {
          params.type = selectedCategory.value
        }

        const response = await API.getMediaList(params)

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
        const err = /** @type {{ response?: { data?: { message?: string }, status?: number }, message?: string }} */ (error);

        // 根据错误类型显示不同的提示信息
        if (err.response?.status === 404) {
          apiError.value = true
          ElMessage.error('媒体库接口不存在，请检查后端配置')
        } else if (err.response?.status === 401) {
          ElMessage.error('请先登录后访问媒体库')
        } else if (err.response?.status === 403) {
          ElMessage.error('没有权限访问媒体库')
        } else {
          apiError.value = true
          ElMessage.error(`加载媒体内容失败: ${err.response?.data?.message || err.message || '未知错误'}`)
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

    // 类型筛选
    const handleCategoryChange = () => {
      currentPage.value = 1
      loadMediaData()
    }

    // 翻页
    /** @param {number} page */
    const goPage = (page) => {
      if (page < 1 || page > totalPages.value) return
      currentPage.value = page
      loadMediaData()
    }

    // 打开灯箱
    /** @param {import('@/types').MediaFile} media */
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
    /** @param {import('@/types').MediaFile | null} media */
    const downloadMedia = async (media) => {
      if (!media) return

      try {
        const response = await API.downloadMedia(media.id)
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.download = media.original_name || ''
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
    /** @param {string | undefined} url */
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
    /** @param {Event} event */
    const handleImageError = (event) => {
      const target = /** @type {HTMLElement} */ (event.target)
      target.style.display = 'none'
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

    // 测试 API 连接（重新加载媒体数据以验证连通性）
    const testApiConnection = async () => {
      await loadMediaData()
      if (!apiError.value) {
        ElMessage.success('连接正常')
      }
    }

    // 初始化加载
    onMounted(async () => {
      // 检查用户是否已登录
      if (!userStore.isAuthenticated) {
        try {
          await userStore.initAuth()
        } catch {
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
      currentPage,
      pageSize,
      total,
      totalPages,
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
      loadMediaData,
      handleSearch,
      handleCategoryChange,
      goPage,
      openLightbox,
      closeLightbox,
      downloadMedia,
      copyUrl,
      clearFilters,
      handleImageError,
      handleUploaded,
      testApiConnection
    }
  }
}
</script>

<style scoped>
.page-head {
  padding: 6px 0 20px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.page-head h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.04em;
  color: var(--text);
}
.page-head p {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--muted);
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 0;
}
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.search-input {
  width: 260px;
}
.type-select,
.sort-select {
  width: 128px;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.result-count {
  font-size: 12px;
  color: var(--muted);
}

/* 状态区 */
.state-section {
  padding: 12px 0 24px;
}
.state-block {
  border: 1px dashed var(--line-strong, var(--line));
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}
.state-block p {
  margin: 0 0 6px;
}
.state-title {
  font-size: 15px;
  font-weight: 650;
  color: var(--text);
}
.state-actions {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.ghost-btn {
  height: 34px;
  padding: 0 14px;
  border: 1px solid var(--line-strong, var(--line));
  border-radius: 9px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
}
.ghost-btn:hover:not(:disabled) {
  border-color: var(--text);
}
.ghost-btn.primary {
  background: var(--text);
  border-color: var(--text);
  color: var(--bg);
  font-weight: 650;
}
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 媒体网格 */
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
  padding: 4px 0 28px;
}
.media-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color var(--transition, 180ms ease), background-color var(--transition, 180ms ease);
}
.media-card:hover {
  border-color: var(--line-strong, var(--line));
  background: var(--surface-2, var(--surface));
}
.card-thumb {
  position: relative;
  aspect-ratio: 16 / 10;
  background: var(--surface-2, #f1f1ee);
  overflow: hidden;
}
.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
}
.thumb-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(23, 23, 23, 0.55);
  opacity: 0;
  transition: opacity var(--transition, 180ms ease);
}
.media-card:hover .thumb-overlay {
  opacity: 1;
}
.card-copy {
  padding: 10px 12px 12px;
}
.card-title {
  display: block;
  font-size: 13px;
  font-weight: 650;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-meta {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
}

/* 分页 */
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 4px 0 28px;
}
.pager-info {
  font-size: 12px;
  color: var(--muted);
}

/* 灯箱 */
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
  background: var(--code, #151614);
  min-width: 0;
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
  color: #fff;
  text-align: center;
}
.lightbox-info {
  flex: 1;
  max-width: 380px;
  padding: 22px;
  overflow-y: auto;
}
.lightbox-info h3 {
  font-size: 16px;
  margin: 0 0 10px;
  color: var(--text);
}
.lightbox-description {
  font-size: 13px;
  line-height: 1.7;
  color: var(--muted);
  margin: 0 0 16px;
}
.details-grid {
  display: grid;
  gap: 0;
  border-top: 1px solid var(--line);
}
.detail-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  color: var(--text);
}
.detail-label {
  color: var(--muted);
  font-size: 12px;
}
.tags-section {
  margin-top: 16px;
}
.tags-section .detail-label {
  display: block;
  margin-bottom: 8px;
}
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag-chip {
  padding: 3px 9px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-2, var(--surface));
  font-size: 11px;
  color: var(--muted);
}
.lightbox-actions {
  display: flex;
  justify-content: flex-end;
}

/* 响应式 */
@media (max-width: 720px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .search-input {
    width: 100%;
  }
  .toolbar-actions {
    justify-content: space-between;
  }
  .lightbox-content {
    flex-direction: column;
    height: auto;
  }
  .lightbox-media {
    height: 40vh;
  }
  .lightbox-info {
    max-width: none;
  }
}
</style>
