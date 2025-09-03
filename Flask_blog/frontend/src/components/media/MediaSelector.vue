<template>
  <el-dialog
    v-model="dialogVisible"
    title="选择媒体文件"
    width="1000px"
    class="media-selector-dialog"
    @close="handleClose"
  >
    <div class="selector-content">
      <!-- 工具栏 -->
      <div class="selector-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文件名..."
            style="width: 250px"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select 
            v-model="filterType" 
            placeholder="文件类型"
            style="width: 120px"
            @change="handleFilterChange"
          >
            <el-option label="全部" value="" />
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
            <el-option label="音频" value="audio" />
            <el-option label="文档" value="document" />
          </el-select>
        </div>
        
        <div class="toolbar-right">
          <el-button @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传新文件
          </el-button>
          
          <el-button-group>
            <el-button 
              :type="viewMode === 'grid' ? 'primary' : 'default'"
              @click="viewMode = 'grid'"
            >
              <el-icon><Grid /></el-icon>
            </el-button>
            <el-button 
              :type="viewMode === 'list' ? 'primary' : 'default'"
              @click="viewMode = 'list'"
            >
              <el-icon><List /></el-icon>
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- 面包屑导航 -->
      <div v-if="folderPath.length > 0" class="breadcrumb-nav">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <a @click="navigateToFolder(null)">根目录</a>
          </el-breadcrumb-item>
          <el-breadcrumb-item 
            v-for="(folder, index) in folderPath" 
            :key="folder.id"
          >
            <a 
              v-if="index < folderPath.length - 1"
              @click="navigateToFolder(folder.id)"
            >
              {{ folder.name }}
            </a>
            <span v-else>{{ folder.name }}</span>
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <!-- 媒体列表 -->
      <div class="selector-body" v-loading="loading">
        <!-- 文件夹列表 -->
        <div v-if="folderList.length > 0" class="folders-section">
          <div v-if="viewMode === 'grid'" class="folders-grid">
            <div 
              v-for="folder in folderList" 
              :key="'folder-' + folder.id"
              class="folder-item"
              @dblclick="navigateToFolder(folder.id)"
            >
              <div class="folder-icon">
                <el-icon size="32"><Folder /></el-icon>
              </div>
              <div class="folder-info">
                <div class="folder-name">{{ folder.name }}</div>
                <div class="folder-meta">{{ folder.media_count || 0 }} 个文件</div>
              </div>
            </div>
          </div>
          
          <div v-else class="folders-list">
            <div 
              v-for="folder in folderList" 
              :key="'folder-' + folder.id"
              class="folder-row"
              @dblclick="navigateToFolder(folder.id)"
            >
              <div class="folder-icon">
                <el-icon><Folder /></el-icon>
              </div>
              <div class="folder-name">{{ folder.name }}</div>
              <div class="folder-meta">{{ folder.media_count || 0 }} 个文件</div>
            </div>
          </div>
        </div>

        <!-- 媒体文件列表 -->
        <div class="media-section">
          <!-- 网格视图 -->
          <div v-if="viewMode === 'grid'" class="media-grid">
            <div 
              v-for="media in mediaList" 
              :key="'media-' + media.id"
              class="media-item"
              :class="{ 'selected': isSelected(media) }"
              @click="toggleSelection(media)"
              @dblclick="confirmSelection"
            >
              <div class="media-preview">
                <img 
                  v-if="media.media_type === 'image'" 
                  :src="getPreviewUrl(media)"
                  :alt="media.alt_text"
                  @error="handleImageError"
                />
                <div v-else class="media-placeholder">
                  <el-icon size="32" :component="getMediaIcon(media.media_type)" />
                </div>
              </div>
              
              <div class="media-info">
                <div class="media-name" :title="media.title || media.original_name">
                  {{ media.title || media.original_name }}
                </div>
                <div class="media-meta">
                  {{ formatFileSize(media.file_size) }}
                  <span v-if="media.width && media.height">
                    • {{ media.width }}×{{ media.height }}
                  </span>
                </div>
              </div>
              
              <!-- 选中状态指示器 -->
              <div v-if="isSelected(media)" class="selection-indicator">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>

          <!-- 列表视图 -->
          <div v-else class="media-list">
            <el-table 
              :data="mediaList"
              @row-click="toggleSelection"
              @row-dblclick="confirmSelection"
              row-class-name="media-row"
              :row-style="getRowStyle"
            >
              <el-table-column width="60" align="center">
                <template #default="{ row }">
                  <div class="table-preview">
                    <img 
                      v-if="row.media_type === 'image'"
                      :src="getPreviewUrl(row)"
                      :alt="row.alt_text"
                      @error="handleImageError"
                    />
                    <el-icon v-else size="24" :component="getMediaIcon(row.media_type)" />
                  </div>
                </template>
              </el-table-column>
              
              <el-table-column prop="title" label="标题" min-width="200">
                <template #default="{ row }">
                  <div class="table-title">
                    <div class="title-text">{{ row.title || row.original_name }}</div>
                    <div class="title-meta">{{ formatDate(row.created_at) }}</div>
                  </div>
                </template>
              </el-table-column>
              
              <el-table-column prop="media_type" label="类型" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ getMediaTypeName(row.media_type) }}</el-tag>
                </template>
              </el-table-column>
              
              <el-table-column prop="file_size" label="大小" width="100">
                <template #default="{ row }">
                  {{ formatFileSize(row.file_size) }}
                </template>
              </el-table-column>
              
              <el-table-column label="尺寸" width="120">
                <template #default="{ row }">
                  <span v-if="row.width && row.height">{{ row.width }}×{{ row.height }}</span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!loading && mediaList.length === 0 && folderList.length === 0" class="empty-state">
          <el-empty description="暂无媒体文件">
            <el-button type="primary" @click="showUploadDialog = true">
              上传第一个文件
            </el-button>
          </el-empty>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination-section">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 对话框底部 -->
    <template #footer>
      <div class="selector-footer">
        <div class="selection-info">
          <span v-if="multiple">
            已选择 {{ selectedMedia.length }} 个文件
          </span>
          <span v-else-if="selectedMedia.length > 0">
            已选择：{{ selectedMedia[0].title || selectedMedia[0].original_name }}
          </span>
        </div>
        
        <div class="footer-actions">
          <el-button @click="handleClose">取消</el-button>
          <el-button 
            type="primary" 
            :disabled="selectedMedia.length === 0"
            @click="confirmSelection"
          >
            确定选择
          </el-button>
        </div>
      </div>
    </template>

    <!-- 上传对话框 -->
    <MediaUploadDialog 
      v-model:visible="showUploadDialog"
      :currentFolderId="currentFolderId"
      @uploaded="handleUploaded"
    />
  </el-dialog>
</template>

<script>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import mediaApi from '@/api/media'
import MediaUploadDialog from './MediaUploadDialog.vue'

export default {
  name: 'MediaSelector',
  components: {
    MediaUploadDialog
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    multiple: {
      type: Boolean,
      default: false
    },
    accept: {
      type: String,
      default: 'image/*'
    },
    maxSelection: {
      type: Number,
      default: 10
    }
  },
  emits: ['update:visible', 'selected'],
  setup(props, { emit }) {
    const loading = ref(false)
    const mediaList = ref([])
    const folderList = ref([])
    const selectedMedia = ref([])
    const currentFolderId = ref(null)
    const folderPath = ref([])
    const showUploadDialog = ref(false)
    
    // 搜索和筛选
    const searchQuery = ref('')
    const filterType = ref('')
    const viewMode = ref('grid')
    
    // 分页
    const currentPage = ref(1)
    const pageSize = ref(20)
    const total = ref(0)

    const dialogVisible = computed({
      get: () => props.visible,
      set: (value) => emit('update:visible', value)
    })

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

    // 获取预览URL
    const getPreviewUrl = (media) => {
      if (media.variants?.variants?.find(v => v.label === 'thumb')) {
        return media.variants.variants.find(v => v.label === 'thumb').url
      }
      return media.url
    }

    // 检查是否已选择
    const isSelected = (media) => {
      return selectedMedia.value.some(selected => selected.id === media.id)
    }

    // 切换选择状态
    const toggleSelection = (media) => {
      if (!props.multiple) {
        selectedMedia.value = [media]
        return
      }

      const index = selectedMedia.value.findIndex(selected => selected.id === media.id)
      if (index >= 0) {
        selectedMedia.value.splice(index, 1)
      } else {
        if (selectedMedia.value.length < props.maxSelection) {
          selectedMedia.value.push(media)
        } else {
          ElMessage.warning(`最多只能选择 ${props.maxSelection} 个文件`)
        }
      }
    }

    // 确认选择
    const confirmSelection = () => {
      if (selectedMedia.value.length === 0) {
        ElMessage.warning('请先选择文件')
        return
      }
      
      emit('selected', props.multiple ? selectedMedia.value : selectedMedia.value[0])
      handleClose()
    }

    // 导航到文件夹
    const navigateToFolder = (folderId) => {
      currentFolderId.value = folderId
      currentPage.value = 1
      loadMediaData()
      loadFolderPath()
    }

    // 加载媒体数据
    const loadMediaData = async () => {
      try {
        loading.value = true
        
        const params = {
          page: currentPage.value,
          size: pageSize.value,
          folder_id: currentFolderId.value,
          keyword: searchQuery.value,
          type: filterType.value
        }

        const [mediaResponse, foldersResponse] = await Promise.all([
          mediaApi.getMediaList(params),
          mediaApi.getFolders(currentFolderId.value)
        ])

        // 处理嵌套响应格式
        let mediaData = mediaResponse.data
        if (mediaResponse.data && mediaResponse.data.code === 0 && mediaResponse.data.data) {
          mediaData = mediaResponse.data.data
        }
        
        mediaList.value = mediaData.items || mediaData.media || []
        total.value = mediaData.total || 0
        
        // 处理文件夹数据
        let folderData = foldersResponse.data
        if (foldersResponse.data && foldersResponse.data.code === 0 && foldersResponse.data.data) {
          folderData = foldersResponse.data.data
        }
        folderList.value = folderData || []
        

      } catch (error) {
        console.error('加载媒体数据失败:', error)
        ElMessage.error('加载媒体文件失败')
      } finally {
        loading.value = false
      }
    }

    // 加载文件夹路径 - 临时简化实现，不显示路径
    const loadFolderPath = async () => {
      if (!currentFolderId.value) {
        folderPath.value = []
        return
      }
      
      // 暂时简化：只显示根目录到当前文件夹
      folderPath.value = [{ id: currentFolderId.value, name: '当前文件夹' }]
    }

    // 搜索处理
    const handleSearch = () => {
      currentPage.value = 1
      loadMediaData()
    }

    // 筛选处理
    const handleFilterChange = () => {
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

    // 表格行样式
    const getRowStyle = ({ row }) => {
      return {
        cursor: 'pointer',
        backgroundColor: isSelected(row) ? '#f0f9ff' : ''
      }
    }

    // 处理图片加载错误
    const handleImageError = (event) => {
      event.target.style.display = 'none'
    }

    // 处理上传成功
    const handleUploaded = () => {
      loadMediaData()
    }

    // 关闭对话框
    const handleClose = () => {
      selectedMedia.value = []
      searchQuery.value = ''
      filterType.value = ''
      currentFolderId.value = null
      folderPath.value = []
      currentPage.value = 1
      dialogVisible.value = false
    }

    // 监听对话框显示状态
    watch(() => props.visible, (visible) => {
      if (visible) {
        loadMediaData()
      }
    })

    return {
      loading,
      mediaList,
      folderList,
      selectedMedia,
      currentFolderId,
      folderPath,
      searchQuery,
      filterType,
      viewMode,
      currentPage,
      pageSize,
      total,
      showUploadDialog,
      dialogVisible,
      formatFileSize,
      getMediaTypeName,
      getMediaIcon,
      formatDate,
      getPreviewUrl,
      isSelected,
      toggleSelection,
      confirmSelection,
      navigateToFolder,
      handleSearch,
      handleFilterChange,
      handlePageChange,
      handleSizeChange,
      getRowStyle,
      handleImageError,
      handleUploaded,
      handleClose
    }
  }
}
</script>

<style scoped>
.media-selector-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.selector-content {
  height: 600px;
  display: flex;
  flex-direction: column;
}

.selector-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafbfc;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.breadcrumb-nav {
  padding: 12px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.breadcrumb-nav a {
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
}

.breadcrumb-nav a:hover {
  text-decoration: underline;
}

.selector-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
}

.folders-section {
  margin-bottom: 24px;
}

.folders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.folder-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.folder-item:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.folder-icon {
  margin-bottom: 8px;
  color: #ffd04b;
}

.folder-info {
  text-align: center;
}

.folder-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  word-break: break-word;
}

.folder-meta {
  font-size: 12px;
  color: #909399;
}

.folders-list {
  margin-bottom: 16px;
}

.folder-row {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.folder-row:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.folder-row .folder-icon {
  margin-right: 12px;
  color: #ffd04b;
}

.folder-row .folder-name {
  flex: 1;
  font-weight: 500;
  color: #303133;
}

.folder-row .folder-meta {
  font-size: 12px;
  color: #909399;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.media-item {
  position: relative;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
  background: #fff;
}

.media-item:hover {
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.media-item.selected {
  border-color: #409eff;
  background: #f0f9ff;
}

.media-preview {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  overflow: hidden;
}

.media-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-placeholder {
  color: #909399;
  text-align: center;
}

.media-info {
  padding: 12px;
}

.media-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.media-meta {
  font-size: 12px;
  color: #909399;
}

.selection-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
}

.media-list .table-preview {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
  background: #f8f9fa;
}

.media-list .table-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.table-title .title-text {
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.table-title .title-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.pagination-section {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  text-align: center;
}

.selector-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
}

.selection-info {
  font-size: 14px;
  color: #606266;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

/* 表格行选中状态 */
:deep(.media-row.selected) {
  background: #f0f9ff !important;
}

:deep(.media-row):hover {
  background: #f5f7fa !important;
}
</style>