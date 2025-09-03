import apiClient from '@/apiClient'

export const mediaApi = {
  // ================================
  // 媒体文件管理
  // ================================

  /**
   * 获取媒体文件列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.size - 每页数量
   * @param {string} params.type - 媒体类型 (image/video/document/audio)
   * @param {number} params.folder_id - 文件夹ID
   * @param {string} params.keyword - 搜索关键词
   * @param {string} params.visibility - 可见性 (private/shared/public)
   */
  getMediaList(params = {}) {
    return apiClient.get('/media', { params })
  },

  /**
   * 获取媒体文件详情
   * @param {number} mediaId - 媒体ID
   */
  getMediaDetail(mediaId) {
    return apiClient.get(`/media/${mediaId}`)
  },

  /**
   * 上传媒体文件
   * @param {FormData} formData - 包含文件和元数据的FormData
   */
  uploadMedia(formData) {
    return apiClient.post('/media/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000 // 60秒超时
    })
  },

  /**
   * 更新媒体元数据
   * @param {number} mediaId - 媒体ID
   * @param {Object} data - 更新数据
   */
  updateMedia(mediaId, data) {
    return apiClient.put(`/media/${mediaId}`, data)
  },

  /**
   * 删除媒体文件
   * @param {number} mediaId - 媒体ID
   */
  deleteMedia(mediaId) {
    return apiClient.delete(`/media/${mediaId}`)
  },

  /**
   * 下载媒体文件
   * @param {number} mediaId - 媒体ID
   */
  downloadMedia(mediaId) {
    return apiClient.get(`/media/${mediaId}/download`, {
      responseType: 'blob'
    })
  },

  // ================================
  // 文件夹管理
  // ================================

  /**
   * 获取文件夹列表
   * @param {number} parentId - 父文件夹ID，0表示根目录
   */
  getFolders(parentId = null) {
    const params = {}
    if (parentId !== null) {
      params.parent_id = parentId
    }
    return apiClient.get('/media/folders', { params })
  },

  /**
   * 创建文件夹
   * @param {Object} data - 文件夹数据
   */
  createFolder(data) {
    return apiClient.post('/media/folders', data)
  },

  /**
   * 更新文件夹
   * @param {number} folderId - 文件夹ID
   * @param {Object} data - 更新数据
   */
  updateFolder(folderId, data) {
    return apiClient.put(`/media/folders/${folderId}`, data)
  },

  /**
   * 删除文件夹
   * @param {number} folderId - 文件夹ID
   */
  deleteFolder(folderId) {
    return apiClient.delete(`/media/folders/${folderId}`)
  },

  // ================================
  // 高级功能
  // ================================

  /**
   * 获取媒体库统计信息
   */
  getStats() {
    return apiClient.get('/media/stats')
  },

  /**
   * 高级搜索
   * @param {Object} searchParams - 搜索参数
   */
  searchMedia(searchParams) {
    return apiClient.post('/media/search', searchParams)
  },

  // ================================
  // 辅助方法
  // ================================

  /**
   * 获取媒体类型的图标
   * @param {string} mediaType - 媒体类型
   * @param {string} mimeType - MIME类型
   */
  getMediaIcon(mediaType, mimeType) {
    const iconMap = {
      image: 'Picture',
      video: 'VideoPlay',
      audio: 'Headphones',
      document: 'Document',
      other: 'Files'
    }
    return iconMap[mediaType] || 'Files'
  },

  /**
   * 格式化文件大小
   * @param {number} bytes - 字节数
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  },

  /**
   * 获取媒体类型的中文名称
   * @param {string} mediaType - 媒体类型
   */
  getMediaTypeName(mediaType) {
    const nameMap = {
      image: '图片',
      video: '视频', 
      audio: '音频',
      document: '文档',
      other: '其他'
    }
    return nameMap[mediaType] || '未知'
  },

  /**
   * 获取可见性的中文名称和颜色
   * @param {string} visibility - 可见性
   */
  getVisibilityInfo(visibility) {
    const infoMap = {
      private: { name: '私有', color: 'info', icon: 'Lock' },
      shared: { name: '共享', color: 'warning', icon: 'Share' },
      public: { name: '公开', color: 'success', icon: 'View' }
    }
    return infoMap[visibility] || { name: '未知', color: 'info', icon: 'Question' }
  }
}

export default mediaApi