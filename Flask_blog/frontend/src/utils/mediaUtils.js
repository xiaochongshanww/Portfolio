/** 媒体库工具函数 */

/**
 * @param {string | undefined} mediaType
 * @returns {string}
 */
export function getMediaIcon(mediaType) {
  /** @type {Record<string, string>} */
  const map = { image: 'Picture', video: 'VideoPlay', audio: 'Headphones', document: 'Document', other: 'Files' }
  return map[mediaType || ''] || 'Files'
}

/**
 * @param {number | undefined} bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * @param {string | undefined} mediaType
 * @returns {string}
 */
export function getMediaTypeName(mediaType) {
  /** @type {Record<string, string>} */
  const map = { image: '图片', video: '视频', audio: '音频', document: '文档', other: '其他' }
  return map[mediaType || ''] || '未知'
}

/**
 * @param {string | undefined | unknown} visibility
 * @returns {{ name: string, color: 'info' | 'success' | 'primary' | 'warning' | 'danger', icon: string }}
 */
export function getVisibilityInfo(visibility) {
  /** @type {Record<string, { name: string, color: 'info' | 'success' | 'primary' | 'warning' | 'danger', icon: string }>} */
  const map = {
    private: { name: '私有', color: 'info', icon: 'Lock' },
    shared: { name: '共享', color: 'warning', icon: 'Share' },
    public: { name: '公开', color: 'success', icon: 'View' },
  }
  const key = typeof visibility === 'string' ? visibility : ''
  return map[key] || { name: '未知', color: 'info', icon: 'Question' }
}
