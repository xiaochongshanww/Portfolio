/** 媒体库工具函数 */

export function getMediaIcon(mediaType) {
  const map = { image: 'Picture', video: 'VideoPlay', audio: 'Headphones', document: 'Document', other: 'Files' }
  return map[mediaType] || 'Files'
}

export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function getMediaTypeName(mediaType) {
  const map = { image: '图片', video: '视频', audio: '音频', document: '文档', other: '其他' }
  return map[mediaType] || '未知'
}

export function getVisibilityInfo(visibility) {
  const map = {
    private: { name: '私有', color: 'info', icon: 'Lock' },
    shared: { name: '共享', color: 'warning', icon: 'Share' },
    public: { name: '公开', color: 'success', icon: 'View' },
  }
  return map[visibility] || { name: '未知', color: 'info', icon: 'Question' }
}
