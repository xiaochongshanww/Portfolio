<template>
  <div class="media-management">
    <AdminPageHeader title="媒体库" description="管理图片、文档和文章附件。">
      <button type="button" class="primary-btn" @click="showUploadDialog = true">上传文件</button>
    </AdminPageHeader>

    <!-- Summary Strip(05 §19 媒体语义) -->
    <AdminSummaryStrip
      v-if="stats"
      :items="[
        { label: '媒体文件', value: stats.total_count ?? 0, note: '全部资源' },
        { label: '总大小', value: formatFileSize(stats.total_size || 0), note: '当前总量' },
        { label: '当前文件夹', value: currentFolder ? currentFolder.name || '—' : '根目录', note: '浏览位置' },
        { label: '已选择', value: selectedMedia.length, note: '点击卡片选择' },
      ]"
    />

    <!-- Toolbar(05 §19):面包屑 + 类型/可见性筛选 + 视图切换 + 搜索 -->
    <AdminToolbar
      v-model:search="searchKeyword"
      search-placeholder="搜索文件名"
      :result-count="error ? null : pagination.total"
      @refresh="refreshAll"
    >
      <template #filters>
        <select v-model="filters.type" class="adm-select" aria-label="按类型筛选">
          <option value="">全部类型</option>
          <option value="image">图片</option>
          <option value="video">视频</option>
          <option value="audio">音频</option>
          <option value="document">文档</option>
        </select>
        <select v-model="filters.visibility" class="adm-select" aria-label="按可见性筛选">
          <option value="">全部可见性</option>
          <option value="private">私有</option>
          <option value="shared">共享</option>
          <option value="public">公开</option>
        </select>
        <button
          type="button"
          class="ghost-btn"
          :class="{ 'view-active': viewMode === 'grid' }"
          aria-label="网格视图"
          @click="viewMode = 'grid'"
        >▦</button>
        <button
          type="button"
          class="ghost-btn"
          :class="{ 'view-active': viewMode === 'list' }"
          aria-label="列表视图"
          @click="viewMode = 'list'"
        >☰</button>
        <button type="button" class="ghost-btn" @click="showCreateFolderDialog = true">＋ 文件夹</button>
      </template>
      <template #right>
        <nav v-if="breadcrumbs.length || currentFolder" class="crumb" aria-label="文件夹路径">
          <a href="#" @click.prevent="navigateToFolder(null)">根目录</a>
          <template v-for="f in breadcrumbs" :key="f.id">
            <span class="crumb-sep">/</span>
            <a href="#" @click.prevent="navigateToFolder(f.id)">{{ f.name }}</a>
          </template>
          <template v-if="currentFolder">
            <span class="crumb-sep">/</span>
            <b>{{ currentFolder.name }}</b>
          </template>
        </nav>
      </template>
    </AdminToolbar>

    <section class="table-card content-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="媒体列表加载失败"
        compact
        @reload="refreshAll"
      />
      <AdminStateBlock
        v-else-if="!loading && !mediaList.length && !folders.length"
        kind="empty"
        title="暂无媒体文件"
        description="上传第一个文件开始使用媒体库。"
        compact
      >
        <button type="button" class="primary-btn" @click="showUploadDialog = true">上传文件</button>
      </AdminStateBlock>

      <template v-else>
        <!-- 文件夹行(Grid 卡上移一层的轻量呈现) -->
        <div v-if="folders.length" class="folder-strip">
          <div
            v-for="folder in folders"
            :key="'folder-' + folder.id"
            class="folder-chip"
            @dblclick="navigateToFolder(folder.id)"
          >
            <span class="folder-ico">▧</span>
            <span class="folder-meta">
              <b>{{ folder.name }}</b>
              <small>{{ folder.media_count }} 个文件</small>
            </span>
            <el-dropdown trigger="click" placement="bottom-end" :width="150">
              <button type="button" class="more-btn" :aria-label="`文件夹操作:${folder.name}`">···</button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleFolderAction({ action: 'edit', folder })">重命名</el-dropdown-item>
                  <el-dropdown-item divided danger @click="handleFolderAction({ action: 'delete', folder })">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- Grid 视图(05 §19 默认) -->
        <div v-if="viewMode === 'grid' && mediaList.length" class="media-grid">
          <div
            v-for="media in mediaList"
            :key="'media-' + media.id"
            class="media-card"
            :class="{ selected: selectedMedia.includes(media.id) }"
            @click="selectMedia(media)"
          >
            <div class="media-thumb">
              <img
                v-if="media.media_type === 'image'"
                :src="media.url"
                :alt="media.alt_text || media.original_name"
                loading="lazy"
              >
              <span v-else class="thumb-icon">{{ getMediaIcon(media.media_type) }}</span>
            </div>
            <div class="media-copy">
              <b :title="media.original_name">{{ media.original_name }}</b>
              <span>{{ formatFileSize(media.file_size) }}</span>
            </div>
            <el-dropdown trigger="click" placement="bottom-end" :width="160">
              <button type="button" class="more-btn card-more" :aria-label="`文件操作:${media.original_name}`">···</button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="viewMediaDetail(media)">查看详情</el-dropdown-item>
                  <el-dropdown-item @click="editMedia(media)">编辑信息</el-dropdown-item>
                  <el-dropdown-item @click="downloadMedia(media)">下载</el-dropdown-item>
                  <el-dropdown-item divided danger @click="handleMediaAction({ action: 'delete', media })">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- List 视图(05 §19:大量文件时) -->
        <div v-if="viewMode === 'list' && mediaList.length" class="table-wrap">
          <el-table :data="mediaList" row-key="id" class="adm-table" @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="42" />
            <el-table-column label="预览" width="64">
              <template #default="{ row }">
                <img
                  v-if="row.media_type === 'image'"
                  :src="row.url"
                  :alt="row.alt_text || row.original_name"
                  loading="lazy"
                  class="thumb-mini"
                >
                <span v-else class="thumb-icon-sm">{{ getMediaIcon(row.media_type) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="文件名" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="cell-strong">{{ row.original_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="90">
              <template #default="{ row }">{{ getMediaTypeName(row.media_type) }}</template>
            </el-table-column>
            <el-table-column label="大小" width="100">
              <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column label="可见性" width="90">
              <template #default="{ row }">{{ getVisibilityInfo(row.visibility).name }}</template>
            </el-table-column>
            <el-table-column label="上传时间" width="110">
              <template #default="{ row }">{{ shortDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column width="70" fixed="right" align="right">
              <template #default="{ row }">
                <el-dropdown trigger="click" placement="bottom-end" :width="160">
                  <button type="button" class="more-btn" :aria-label="`文件操作:${row.original_name}`">···</button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="viewMediaDetail(row)">查看详情</el-dropdown-item>
                      <el-dropdown-item @click="editMedia(row)">编辑信息</el-dropdown-item>
                      <el-dropdown-item @click="downloadMedia(row)">下载</el-dropdown-item>
                      <el-dropdown-item divided danger @click="handleMediaAction({ action: 'delete', media: row })">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="pagination.total > pagination.size" class="table-footer">
          <span>共 {{ pagination.total }} 个文件</span>
          <el-pagination
            layout="prev, pager, next"
            :total="pagination.total"
            :current-page="pagination.page"
            :page-size="pagination.size"
            :pager-count="5"
            small
            @current-change="handlePageChange"
          />
        </div>
      </template>
    </section>

    <!-- 上传对话框 -->
    <MediaUploadDialog
      v-model:visible="showUploadDialog"
      :current-folder-id="currentFolderId ?? undefined"
      @uploaded="handleFileUploaded"
    />

    <!-- 创建文件夹对话框 -->
    <FolderCreateDialog
      v-model:visible="showCreateFolderDialog"
      :parent-folder-id="currentFolderId ?? undefined"
      @created="handleFolderCreated"
    />

    <!-- 媒体详情对话框 -->
    <MediaDetailDialog
      v-model:visible="showDetailDialog"
      :media="selectedMediaForDetail ?? undefined"
      @updated="handleMediaUpdated"
      @deleted="handleMediaDeleted"
    />

    <!-- 编辑媒体对话框 -->
    <MediaEditDialog
      v-model:visible="showEditDialog"
      :media="selectedMediaForEdit ?? undefined"
      @updated="handleMediaUpdated"
    />
  </div>
</template>

<script>
/**
 * 媒体库(05 §19 Media Grid Pattern):默认 Grid,大量文件可切 Table。
 * 文件夹导航/四个子对话框/全部业务动作保留。
 */
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { API } from '../../api'
import { formatFileSize, getMediaTypeName, getVisibilityInfo, getMediaIcon } from '../../utils/mediaUtils'
import MediaUploadDialog from '../../components/media/MediaUploadDialog.vue'
import FolderCreateDialog from '../../components/media/FolderCreateDialog.vue'
import MediaDetailDialog from '../../components/media/MediaDetailDialog.vue'
import MediaEditDialog from '../../components/media/MediaEditDialog.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue'
import AdminToolbar from '../../components/admin/AdminToolbar.vue'
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue'

export default {
  name: 'MediaManagement',
  components: {
    MediaUploadDialog,
    FolderCreateDialog,
    MediaDetailDialog,
    MediaEditDialog,
    AdminPageHeader,
    AdminSummaryStrip,
    AdminToolbar,
    AdminStateBlock,
  },
  setup() {
    const loading = ref(false)
    const error = ref(false)
    const viewMode = ref('grid')
    const searchKeyword = ref('')
    /** @type {import('vue').Ref<number | null>} */
    const currentFolderId = ref(null)
    /** @type {import('vue').Ref<any>} */
    const currentFolder = ref(null)
    /** @type {import('vue').Ref<Array<{ id?: number, name?: string }>>} */
    const breadcrumbs = ref([])
    /** @type {import('vue').Ref<any[]>} */
    const mediaList = ref([])
    /** @type {import('vue').Ref<any[]>} */
    const folders = ref([])
    /** @type {import('vue').Ref<number[]>} */
    const selectedMedia = ref([])
    /** @type {import('vue').Ref<any>} */
    const stats = ref(null)

    const pagination = reactive({ page: 1, size: 20, total: 0 })
    const filters = reactive({ type: '', visibility: '' })

    const showUploadDialog = ref(false)
    const showCreateFolderDialog = ref(false)
    const showDetailDialog = ref(false)
    const showEditDialog = ref(false)
    /** @type {import('vue').Ref<any>} */
    const selectedMediaForDetail = ref(null)
    /** @type {import('vue').Ref<any>} */
    const selectedMediaForEdit = ref(null)

    /** @param {string | undefined} dateStr */
    const shortDate = (dateStr) => {
      if (!dateStr) return '—'
      const d = new Date(dateStr)
      if (Number.isNaN(d.getTime())) return '—'
      const pad = (/** @type {number} */ n) => String(n).padStart(2, '0')
      return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())}`
    }

    const loadMediaList = async () => {
      loading.value = true
      error.value = false
      try {
        const params = {
          page: pagination.page,
          size: pagination.size,
          folder_id: currentFolderId.value || 0,
          keyword: searchKeyword.value,
          ...filters,
        }
        const response = await API.getMediaList(params)
        let actualData = response.data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        if (actualData.items) mediaList.value = actualData.items
        else if (actualData.media) mediaList.value = actualData.media
        else mediaList.value = []
        pagination.total = actualData.total || 0
      } catch (e) {
        error.value = true
      } finally {
        loading.value = false
      }
    }

    const loadFolders = async () => {
      try {
        const response = await API.getFolders(currentFolderId.value || 0)
        let actualData = response.data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        folders.value = actualData || []
      } catch (e) {
        folders.value = []
      }
    }

    const loadStats = async () => {
      try {
        const response = await API.getMediaStats()
        let actualData = response.data
        if (response.data && response.data.code === 0 && response.data.data) {
          actualData = response.data.data
        }
        stats.value = actualData
      } catch (e) {
        stats.value = null
      }
    }

    const refreshAll = () => {
      loadMediaList()
      loadFolders()
      loadStats()
    }

    /** @param {number | null | undefined} folderId */
    const navigateToFolder = async (folderId) => {
      currentFolderId.value = folderId ?? null
      pagination.page = 1
      selectedMedia.value = []
      if (folderId) {
        const hit = folders.value.find((f) => f.id === folderId)
        currentFolder.value = hit || null
      } else {
        currentFolder.value = null
      }
      loadMediaList()
      loadFolders()
    }

    /** @param {any} media */
    const selectMedia = (media) => {
      const index = selectedMedia.value.indexOf(media.id)
      if (index > -1) selectedMedia.value.splice(index, 1)
      else selectedMedia.value.push(media.id)
    }

    /** @param {any[]} selection */
    const handleSelectionChange = (selection) => {
      selectedMedia.value = selection.map((/** @type {any} */ s) => s.id)
    }

    const handleFileUploaded = () => {
      ElMessage.success('上传成功')
      refreshAll()
    }
    const handleFolderCreated = () => {
      ElMessage.success('文件夹已创建')
      loadFolders()
    }
    const handleMediaUpdated = () => {
      ElMessage.success('已更新')
      refreshAll()
    }
    const handleMediaDeleted = () => {
      ElMessage.success('已删除')
      refreshAll()
    }

    /** @param {{ action: string, folder: any }} payload */
    const handleFolderAction = async ({ action, folder }) => {
      if (action === 'delete') {
        try {
          await ElMessageBox.confirm(
            `删除文件夹「${folder.name}」?其中的文件将移动到上级目录。`,
            '删除文件夹',
            { type: 'warning', confirmButtonText: '删除文件夹', cancelButtonText: '取消' },
          )
          await API.deleteMediaFolder(folder.id)
          ElMessage.success('文件夹已删除')
          if (currentFolderId.value === folder.id) navigateToFolder(null)
          else loadFolders()
        } catch (e) {
          if (e !== 'cancel') ElMessage.error('删除失败')
        }
      }
    }

    /** @param {{ action: string, media: any }} payload */
    const handleMediaAction = async ({ action, media }) => {
      if (action === 'view') viewMediaDetail(media)
      else if (action === 'edit') editMedia(media)
      else if (action === 'download') downloadMedia(media)
      else if (action === 'delete') {
        try {
          await ElMessageBox.confirm(
            `删除文件「${media.original_name}」?删除后不可恢复。`,
            '删除文件',
            { type: 'warning', confirmButtonText: '删除文件', cancelButtonText: '取消' },
          )
          await API.deleteMedia(media.id)
          ElMessage.success('删除成功')
          refreshAll()
        } catch (e) {
          if (e !== 'cancel') ElMessage.error('删除失败')
        }
      }
    }

    /** @param {any} media */
    const viewMediaDetail = (media) => {
      selectedMediaForDetail.value = media
      showDetailDialog.value = true
    }

    /** @param {any} media */
    const editMedia = (media) => {
      selectedMediaForEdit.value = media
      showEditDialog.value = true
    }

    /** @param {any} media */
    const downloadMedia = async (media) => {
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
      } catch (e) {
        ElMessage.error('下载失败')
      }
    }

    /** @param {number} page */
    const handlePageChange = (page) => {
      pagination.page = page
      loadMediaList()
    }

    watch([filters, searchKeyword], () => {
      pagination.page = 1
      loadMediaList()
    }, { deep: true })

    onMounted(() => {
      refreshAll()
    })

    return {
      loading,
      error,
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
      shortDate,
      refreshAll,
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
      handlePageChange,
    }
  },
}
</script>

<style scoped>
.media-management {
  width: 100%;
}
.media-management :deep(.admin-toolbar) {
  border-bottom: 0;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--adm-primary);
  border-radius: 9px;
  background: var(--adm-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.primary-btn:hover {
  opacity: 0.92;
}

.adm-select {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  outline: none;
}
.adm-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}
.ghost-btn {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  cursor: pointer;
}
.ghost-btn:hover,
.ghost-btn.view-active {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}
.ghost-btn.view-active {
  background: var(--adm-surface-subtle);
}

.crumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--adm-muted);
  white-space: nowrap;
}
.crumb a:hover {
  color: var(--adm-text);
}
.crumb b {
  color: var(--adm-text-2);
  font-weight: 600;
}

.table-card {
  border: 1px solid var(--adm-border);
  border-radius: 0 0 var(--adm-r-container) var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
}
.content-card {
  padding: 14px;
}

/* 文件夹条 */
.folder-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.folder-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  background: var(--adm-surface);
  cursor: pointer;
}
.folder-chip:hover {
  border-color: var(--adm-border-strong);
}
.folder-ico {
  font-size: 18px;
  color: var(--adm-muted);
}
.folder-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.folder-meta b {
  font-size: 12px;
  color: var(--adm-text);
}
.folder-meta small {
  font-size: 10px;
  color: var(--adm-muted);
}

/* Grid 视图(原型 mediaBox 三卡) */
.media-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.media-card {
  position: relative;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
  cursor: pointer;
  transition: border-color var(--transition, 0.18s ease);
}
.media-card:hover,
.media-card.selected {
  border-color: var(--adm-primary);
}
.media-card.selected::after {
  content: '✓';
  position: absolute;
  right: 8px;
  top: 8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--adm-primary);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 11px;
}
.media-thumb {
  height: 130px;
  background: #eef2f7;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.media-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-icon {
  font-size: 34px;
  color: var(--adm-muted);
}
.media-copy {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 36px;
}
.media-copy b {
  font-size: 12px;
  color: var(--adm-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.media-copy span {
  font-size: 11px;
  color: var(--adm-muted);
}
.card-more {
  position: absolute;
  right: 8px;
  bottom: 10px;
}

/* List 视图 */
.table-wrap {
  overflow: auto;
}
.thumb-mini {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 6px;
  display: block;
}
.thumb-icon-sm {
  display: inline-grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 6px;
  background: #eef2f7;
  color: var(--adm-muted);
}
.cell-strong {
  font-size: 12px;
  color: var(--adm-text);
}

.more-btn {
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-muted);
  font-size: 12px;
  letter-spacing: 1px;
  cursor: pointer;
}
.more-btn:hover {
  color: var(--adm-text-2);
  border-color: var(--adm-border-strong);
}

.table-footer {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 4px 2px;
  color: var(--adm-muted);
  font-size: 11px;
}

@media (max-width: 950px) {
  .media-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 719.98px) {
  .media-grid {
    grid-template-columns: 1fr;
  }
}
</style>
