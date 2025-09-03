<template>
  <div class="media-management">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">媒体库管理</h1>
        <p class="page-description">管理和组织您的媒体文件</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
        <el-button @click="showCreateFolderDialog = true">
          <el-icon><FolderAdd /></el-icon>
          新建文件夹
        </el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <!-- 面包屑导航 -->
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <el-button text @click="navigateToFolder(null)">
              <el-icon><House /></el-icon>
              根目录
            </el-button>
          </el-breadcrumb-item>
          <el-breadcrumb-item 
            v-for="folder in breadcrumbs" 
            :key="folder.id"
            @click="navigateToFolder(folder.id)"
          >
            <el-button text>{{ folder.name }}</el-button>
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      
      <div class="toolbar-right">
        <!-- 视图切换 -->
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button label="grid">
            <el-icon><Grid /></el-icon>
            网格
          </el-radio-button>
          <el-radio-button label="list">
            <el-icon><List /></el-icon>
            列表
          </el-radio-button>
        </el-radio-group>
        
        <!-- 筛选 -->
        <el-select v-model="filters.type" placeholder="类型" clearable style="width: 120px">
          <el-option label="图片" value="image" />
          <el-option label="视频" value="video" />
          <el-option label="音频" value="audio" />
          <el-option label="文档" value="document" />
        </el-select>
        
        <el-select v-model="filters.visibility" placeholder="可见性" clearable style="width: 120px">
          <el-option label="私有" value="private" />
          <el-option label="共享" value="shared" />
          <el-option label="公开" value="public" />
        </el-select>
        
        <!-- 搜索 -->
        <el-input
          v-model="searchKeyword"
          placeholder="搜索文件..."
          style="width: 200px"
          @keyup.enter="loadMediaList"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="stats-bar" v-if="stats">
      <div class="stat-item">
        <span class="stat-label">总文件数：</span>
        <span class="stat-value">{{ stats.total_count }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">总大小：</span>
        <span class="stat-value">{{ formatFileSize(stats.total_size) }}</span>
      </div>
      <div class="stat-item" v-if="currentFolder">
        <span class="stat-label">当前文件夹：</span>
        <span class="stat-value">{{ currentFolder.name }}</span>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 文件夹列表 -->
      <div class="folders-section" v-if="folders.length > 0">
        <div class="section-title">文件夹</div>
        <div class="folders-grid">
          <div 
            v-for="folder in folders" 
            :key="'folder-' + folder.id"
            class="folder-item"
            @dblclick="navigateToFolder(folder.id)"
          >
            <div class="folder-icon">
              <el-icon size="48"><Folder /></el-icon>
            </div>
            <div class="folder-name">{{ folder.name }}</div>
            <div class="folder-info">
              {{ folder.media_count }} 个文件
            </div>
            <div class="folder-actions">
              <el-dropdown @command="handleFolderAction">
                <el-button text>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'edit', folder }">重命名</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', folder }" class="danger">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div class="visibility-badge">
              <el-tag :type="getVisibilityInfo(folder.visibility).color" size="small">
                {{ getVisibilityInfo(folder.visibility).name }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 媒体文件列表 -->
      <div class="media-section">
        <div class="section-title" v-if="folders.length > 0">媒体文件</div>
        
        <!-- 网格视图 -->
        <div v-if="viewMode === 'grid'" class="media-grid">
          <div 
            v-for="media in mediaList" 
            :key="'media-' + media.id"
            class="media-item"
            @click="selectMedia(media)"
            :class="{ selected: selectedMedia.includes(media.id) }"
          >
            <div class="media-preview">
              <img v-if="media.media_type === 'image'" :src="media.url" :alt="media.alt_text" />
              <div v-else class="media-placeholder">
                <el-icon size="48" :component="getMediaIcon(media.media_type)" />
              </div>
            </div>
            <div class="media-info">
              <div class="media-title" :title="media.original_name">{{ media.original_name }}</div>
              <div class="media-meta">
                {{ formatFileSize(media.file_size) }} • {{ formatDate(media.created_at) }}
              </div>
              <div class="media-tags">
                <el-tag 
                  v-for="tag in media.tags.slice(0, 2)" 
                  :key="tag"
                  size="small"
                  class="tag-item"
                >
                  {{ tag }}
                </el-tag>
                <span v-if="media.tags.length > 2" class="more-tags">+{{ media.tags.length - 2 }}</span>
              </div>
            </div>
            <div class="media-actions">
              <el-dropdown @command="handleMediaAction">
                <el-button text>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'view', media }">查看详情</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'edit', media }">编辑信息</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'download', media }">下载</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', media }" class="danger">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div class="visibility-badge">
              <el-tag :type="getVisibilityInfo(media.visibility).color" size="small">
                {{ getVisibilityInfo(media.visibility).name }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 列表视图 -->
        <div v-else class="media-table">
          <el-table :data="mediaList" @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="55" />
            <el-table-column label="预览" width="80">
              <template #default="{ row }">
                <div class="table-preview">
                  <img v-if="row.media_type === 'image'" :src="row.url" />
                  <el-icon v-else size="32" :component="getMediaIcon(row.media_type)" />
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="original_name" label="文件名" />
            <el-table-column prop="media_type" label="类型" width="80">
              <template #default="{ row }">
                {{ getMediaTypeName(row.media_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="file_size" label="大小" width="100">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="visibility" label="可见性" width="80">
              <template #default="{ row }">
                <el-tag :type="getVisibilityInfo(row.visibility).color" size="small">
                  {{ getVisibilityInfo(row.visibility).name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text @click="viewMediaDetail(row)">详情</el-button>
                <el-button text @click="editMedia(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 分页 -->
        <div class="pagination-wrapper" v-if="pagination.total > 0">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :total="pagination.total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadMediaList"
            @current-change="loadMediaList"
          />
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && mediaList.length === 0 && folders.length === 0"
      description="暂无媒体文件"
    >
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        上传第一个文件
      </el-button>
    </el-empty>

    <!-- 上传对话框 -->
    <MediaUploadDialog 
      v-model:visible="showUploadDialog"
      :currentFolderId="currentFolderId"
      @uploaded="handleFileUploaded"
    />

    <!-- 创建文件夹对话框 -->
    <FolderCreateDialog
      v-model:visible="showCreateFolderDialog"
      :parentFolderId="currentFolderId"
      @created="handleFolderCreated"
    />

    <!-- 媒体详情对话框 -->
    <MediaDetailDialog
      v-model:visible="showDetailDialog"
      :media="selectedMediaForDetail"
      @updated="handleMediaUpdated"
      @deleted="handleMediaDeleted"
    />

    <!-- 编辑媒体对话框 -->
    <MediaEditDialog
      v-model:visible="showEditDialog"
      :media="selectedMediaForEdit"
      @updated="handleMediaUpdated"
    />
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import mediaApi from '@/api/media'
import MediaUploadDialog from '@/components/media/MediaUploadDialog.vue'
import FolderCreateDialog from '@/components/media/FolderCreateDialog.vue'
import MediaDetailDialog from '@/components/media/MediaDetailDialog.vue'
import MediaEditDialog from '@/components/media/MediaEditDialog.vue'

export default {
  name: 'MediaManagement',
  components: {
    MediaUploadDialog,
    FolderCreateDialog,
    MediaDetailDialog,
    MediaEditDialog
  },
  setup() {
    const loading = ref(false)
    const viewMode = ref('grid')
    const searchKeyword = ref('')
    const currentFolderId = ref(null)
    const currentFolder = ref(null)
    const breadcrumbs = ref([])
    
    const mediaList = ref([])
    const folders = ref([])
    const selectedMedia = ref([])
    const stats = ref(null)
    
    const pagination = reactive({
      page: 1,
      size: 20,
      total: 0
    })
    
    const filters = reactive({
      type: '',
      visibility: ''
    })
    
    // 对话框状态
    const showUploadDialog = ref(false)
    const showCreateFolderDialog = ref(false)
    const showDetailDialog = ref(false)
    const showEditDialog = ref(false)
    const selectedMediaForDetail = ref(null)
    const selectedMediaForEdit = ref(null)

    // 从 API 客户端获取辅助方法
    const { formatFileSize, getMediaTypeName, getVisibilityInfo, getMediaIcon } = mediaApi

    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleString('zh-CN')
    }

    // 加载媒体列表
    const loadMediaList = async () => {
      loading.value = true
      try {
        const params = {
          page: pagination.page,
          size: pagination.size,
          folder_id: currentFolderId.value || 0,
          keyword: searchKeyword.value,
          ...filters
        }
        
        const response = await mediaApi.getMediaList(params)
        
        // 处理嵌套响应格式
        let actualData = response.data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        
        // 优先使用items字段，备用media字段
        if (actualData.items) {
          mediaList.value = actualData.items
        } else if (actualData.media) {
          mediaList.value = actualData.media
        } else {
          mediaList.value = []
        }
        
        pagination.total = actualData.total || 0
      } catch (error) {
        console.error('加载媒体列表失败:', error)
        ElMessage.error('加载媒体列表失败')
      } finally {
        loading.value = false
      }
    }

    // 加载文件夹列表
    const loadFolders = async () => {
      try {
        const response = await mediaApi.getFolders(currentFolderId.value || 0)
        
        // 处理嵌套响应格式
        let actualData = response.data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        
        folders.value = actualData || []
      } catch (error) {
        console.error('加载文件夹失败:', error)
      }
    }

    // 加载统计信息
    const loadStats = async () => {
      try {
        const response = await mediaApi.getStats()
        
        // 处理嵌套响应格式
        let actualData = response.data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        
        stats.value = actualData
      } catch (error) {
        console.error('加载统计信息失败:', error)
      }
    }

    // 导航到文件夹
    const navigateToFolder = async (folderId) => {
      currentFolderId.value = folderId
      pagination.page = 1
      selectedMedia.value = []
      
      // 更新面包屑
      if (folderId) {
        try {
          // TODO: 实现获取文件夹路径的 API
          // const path = await mediaApi.getFolderPath(folderId)
          // breadcrumbs.value = path
        } catch (error) {
          console.error('获取文件夹路径失败:', error)
        }
      } else {
        breadcrumbs.value = []
        currentFolder.value = null
      }
      
      await Promise.all([loadMediaList(), loadFolders()])
    }

    // 选择媒体
    const selectMedia = (media) => {
      const index = selectedMedia.value.indexOf(media.id)
      if (index > -1) {
        selectedMedia.value.splice(index, 1)
      } else {
        selectedMedia.value.push(media.id)
      }
    }

    // 处理表格选择变化
    const handleSelectionChange = (selection) => {
      selectedMedia.value = selection.map(item => item.id)
    }

    // 处理文件上传完成
    const handleFileUploaded = () => {
      loadMediaList()
      loadStats()
      ElMessage.success('文件上传成功')
    }

    // 处理文件夹创建
    const handleFolderCreated = () => {
      loadFolders()
      ElMessage.success('文件夹创建成功')
    }

    // 处理媒体更新
    const handleMediaUpdated = () => {
      loadMediaList()
      ElMessage.success('媒体信息更新成功')
    }

    // 处理媒体删除
    const handleMediaDeleted = () => {
      loadMediaList()
      loadStats()
      ElMessage.success('媒体文件删除成功')
    }

    // 文件夹操作处理
    const handleFolderAction = async ({ action, folder }) => {
      if (action === 'edit') {
        // TODO: 实现文件夹编辑
        ElMessage.info('文件夹编辑功能开发中')
      } else if (action === 'delete') {
        try {
          await ElMessageBox.confirm(
            `确定要删除文件夹"${folder.name}"吗？此操作不可恢复。`,
            '确认删除',
            { type: 'warning' }
          )
          
          await mediaApi.deleteFolder(folder.id)
          await loadFolders()
          ElMessage.success('文件夹删除成功')
        } catch (error) {
          if (error !== 'cancel') {
            console.error('删除文件夹失败:', error)
            ElMessage.error('删除文件夹失败')
          }
        }
      }
    }

    // 媒体操作处理
    const handleMediaAction = async ({ action, media }) => {
      if (action === 'view') {
        viewMediaDetail(media)
      } else if (action === 'edit') {
        editMedia(media)
      } else if (action === 'download') {
        downloadMedia(media)
      } else if (action === 'delete') {
        deleteMedia(media)
      }
    }

    // 查看媒体详情
    const viewMediaDetail = (media) => {
      selectedMediaForDetail.value = media
      showDetailDialog.value = true
    }

    // 编辑媒体
    const editMedia = (media) => {
      selectedMediaForEdit.value = media
      showEditDialog.value = true
    }

    // 下载媒体
    const downloadMedia = async (media) => {
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

    // 删除媒体
    const deleteMedia = async (media) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除"${media.original_name}"吗？此操作不可恢复。`,
          '确认删除',
          { type: 'warning' }
        )
        
        await mediaApi.deleteMedia(media.id)
        await loadMediaList()
        await loadStats()
        ElMessage.success('删除成功')
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除失败:', error)
          ElMessage.error('删除失败')
        }
      }
    }

    // 监听筛选条件变化
    watch([filters, searchKeyword], () => {
      pagination.page = 1
      loadMediaList()
    }, { deep: true })

    // 初始化
    onMounted(() => {
      Promise.all([
        loadMediaList(),
        loadFolders(),
        loadStats()
      ])
    })

    return {
      loading,
      viewMode,
      searchKeyword,
      currentFolderId,
      currentFolder,
      breadcrumbs,
      mediaList,
      folders,
      selectedMedia,
      stats,
      pagination,
      filters,
      showUploadDialog,
      showCreateFolderDialog,
      showDetailDialog,
      showEditDialog,
      selectedMediaForDetail,
      selectedMediaForEdit,
      formatFileSize,
      getMediaTypeName,
      getVisibilityInfo,
      getMediaIcon,
      formatDate,
      loadMediaList,
      navigateToFolder,
      selectMedia,
      handleSelectionChange,
      handleFileUploaded,
      handleFolderCreated,
      handleMediaUpdated,
      handleMediaDeleted,
      handleFolderAction,
      handleMediaAction,
      viewMediaDetail,
      editMedia,
      downloadMedia,
      deleteMedia
    }
  }
}
</script>

<style scoped>
.media-management {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left .page-title {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-left .page-description {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stats-bar {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  background: #f0f2f5;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}

.stat-item .stat-label {
  color: #606266;
}

.stat-item .stat-value {
  color: #303133;
  font-weight: 500;
}

.content-area {
  flex: 1;
  overflow: auto;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e4e7ed;
}

.folders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.folder-item {
  position: relative;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.folder-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.folder-icon {
  color: #409eff;
  margin-bottom: 8px;
}

.folder-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.folder-info {
  font-size: 12px;
  color: #909399;
}

.folder-actions {
  position: absolute;
  top: 8px;
  right: 8px;
}

.visibility-badge {
  position: absolute;
  top: 8px;
  left: 8px;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.media-item {
  position: relative;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.media-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.media-item.selected {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.media-preview {
  width: 100%;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.media-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-placeholder {
  color: #c0c4cc;
}

.media-info {
  padding: 12px;
}

.media-title {
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
  margin-bottom: 8px;
}

.media-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-item {
  font-size: 10px;
}

.more-tags {
  font-size: 10px;
  color: #909399;
}

.media-actions {
  position: absolute;
  top: 8px;
  right: 8px;
}

.table-preview {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f7fa;
}

.table-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e4e7ed;
}

.danger {
  color: #f56c6c !important;
}
</style>