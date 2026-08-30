/**
 * 统一 API 出口。
 *
 * 所有后端 API 调用统一通过 `import { API } from '@/api'` 访问。
 * 用法: API.ArticlesService.listArticles({ page: 1 })
 *       API.BackupService.createBackup()
 */


import { OpenAPI } from '../generated'
import * as Services from '../generated'
import { bindGeneratedClient, createServices } from './generatedClientAdapter'
import apiClient from '@/apiClient'

bindGeneratedClient(OpenAPI)
const GeneratedAPI = createServices(Services)


// ─── 手写补充：generated 未覆盖的接口 ─────────────────────

const HandwrittenAPI = {

  // ── 分类 / 标签 ─────────────────────────────────────
  /** @param {any} params */
  getCategories(params) {
    return apiClient.get('/taxonomy/categories/', { params })
  },
  /** @param {any} data */
  createCategory(data) {
    return apiClient.post('/taxonomy/categories/', data)
  },
  /** @param {number} id @param {any} data */
  updateCategory(id, data) {
    return apiClient.patch(`/taxonomy/categories/${id}`, data)
  },
  /** @param {number} id */
  deleteCategory(id) {
    return apiClient.delete(`/taxonomy/categories/${id}`)
  },

  /** @param {any} params */
  getTags(params) {
    return apiClient.get('/taxonomy/tags/', { params })
  },
  /** @param {any} data */
  createTag(data) {
    return apiClient.post('/taxonomy/tags/', data)
  },
  /** @param {number} id @param {any} data */
  updateTag(id, data) {
    return apiClient.patch(`/taxonomy/tags/${id}`, data)
  },
  /** @param {number} id */
  deleteTag(id) {
    return apiClient.delete(`/taxonomy/tags/${id}`)
  },

  getPublicCategories() {
    return apiClient.get('/taxonomy/categories/public')
  },
  getPublicTags() {
    return apiClient.get('/taxonomy/tags/public')
  },
  getTaxonomyStats() {
    return apiClient.get('/taxonomy/stats')
  },

  // ── 媒体库 ─────────────────────────────────────────
  /** @param {any} params */
  getMediaList(params) {
    return apiClient.get('/media', { params })
  },
  /** @param {number} id */
  getMediaDetail(id) {
    return apiClient.get(`/media/${id}`)
  },
  /** @param {FormData} formData */
  uploadMedia(formData) {
    return apiClient.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },
  /** @param {number} id @param {any} data */
  updateMedia(id, data) {
    return apiClient.put(`/media/${id}`, data)
  },
  /** @param {number} id */
  deleteMedia(id) {
    return apiClient.delete(`/media/${id}`)
  },
  /** @param {number} id */
  downloadMedia(id) {
    return apiClient.get(`/media/${id}/download`, { responseType: 'blob' })
  },
  /** @param {any} params */
  getMediaFolders(params) {
    return apiClient.get('/media/folders', { params })
  },
  /** @param {number|undefined} parentId */
  getFolders(parentId) {
    return apiClient.get('/media/folders', { params: parentId != null ? { parent_id: parentId } : {} })
  },
  /** @param {any} data */
  createMediaFolder(data) {
    return apiClient.post('/media/folders', data)
  },
  /** @param {number} id @param {any} data */
  updateMediaFolder(id, data) {
    return apiClient.put(`/media/folders/${id}`, data)
  },
  /** @param {number} id */
  deleteMediaFolder(id) {
    return apiClient.delete(`/media/folders/${id}`)
  },
  getMediaStats() {
    return apiClient.get('/media/stats')
  },
  /** @param {any} params */
  searchMedia(params) {
    return apiClient.post('/media/search', params)
  },

  // ── 备份 ───────────────────────────────────────────
  /** @param {any} params */
  getBackupRecords(params) {
    return apiClient.get('/backup/records', { params })
  },
  /** @param {number} id */
  getBackupRecord(id) {
    return apiClient.get(`/backup/${id}`)
  },
  /** @param {any} data */
  createBackup(data) {
    return apiClient.post('/backup/create', data || {})
  },
  /** @param {number} id */
  cancelBackup(id) {
    return apiClient.post(`/backup/${id}/cancel`)
  },
  /** @param {number} id */
  deleteBackup(id) {
    return apiClient.delete(`/backup/${id}`)
  },
  /** @param {number} id */
  downloadBackup(id) {
    return apiClient.get(`/backup/${id}/download`, { responseType: 'blob' })
  },
  /** @param {number} id @param {any} options */
  restoreBackup(id, options) {
    return apiClient.post(`/backup/${id}/restore`, options || {})
  },
  getBackupConfig() {
    return apiClient.get('/backup/config')
  },
  /** @param {any} data */
  updateBackupConfig(data) {
    return apiClient.put('/backup/config', data)
  },
  getBackupStatistics() {
    return apiClient.get('/backup/statistics')
  },
  cleanupBackups() {
    return apiClient.post('/backup/cleanup')
  },
  /** @param {any} params */
  getBackupTasks(params) {
    return apiClient.get('/backup/tasks', { params })
  },
  /** @param {any} params */
  getRestoreRecords(params) {
    return apiClient.get('/backup/restores', { params })
  },
  /** @param {number} id */
  getRestoreProgress(id) {
    return apiClient.get(`/backup/restores/${id}`)
  },
  /** @param {number} id */
  cancelRestore(id) {
    return apiClient.post(`/backup/restores/${id}/cancel`)
  },
  cleanupStuckRestores() {
    return apiClient.post('/backup/restores/cleanup')
  },

  // ── 设置 ───────────────────────────────────────────
  /** @param {string} section */
  getSettings(section) {
    return apiClient.get(`/settings/${section}`)
  },
  /** @param {string} section @param {any} data */
  updateSettings(section, data) {
    return apiClient.put(`/settings/${section}`, data)
  },
  getAllSettings() {
    return apiClient.get('/settings/all')
  },
  getSystemInfo() {
    return apiClient.post('/settings/system/info')
  },
  clearCache() {
    return apiClient.post('/settings/system/clear-cache')
  },
  generateSitemap() {
    return apiClient.post('/settings/system/generate-sitemap')
  },

  // ── 安全 ───────────────────────────────────────────
  getSecurityStats() {
    return apiClient.get('/security/stats')
  },
  getSystemHealth() {
    return apiClient.get('/security/system-health')
  },
  /** @param {any} params */
  getSecurityEvents(params) {
    return apiClient.get('/security/events/recent', { params })
  },
  /** @param {any} params */
  getThreatTrends(params) {
    return apiClient.get('/security/threat-trends', { params })
  },
  /** @param {any} data */
  blockIp(data) {
    return apiClient.post('/security/block-ip', data)
  },

  // ── 日志 ───────────────────────────────────────────
  /** @param {any} data */
  queryLogs(data) {
    return apiClient.post('/admin/logs/query', data)
  },
  getLogSources() {
    return apiClient.get('/admin/logs/sources')
  },
  getLogStats() {
    return apiClient.get('/admin/logs/stats')
  },
  getLogConfig() {
    return apiClient.get('/admin/logs/config')
  },

  // ── 指标 ───────────────────────────────────────────
  getMetricsSummary() {
    return apiClient.get('/metrics/summary')
  },
  getVisitorStats() {
    return apiClient.get('/metrics/visitors')
  },
  getMetricsTest() {
    return apiClient.get('/metrics/test')
  },
  /** @param {any} data */
  trackVisit(data) {
    return apiClient.post('/metrics/track', data)
  },

  // ── 文章 / 工作流 ─────────────────────────────────
  /** @param {any} params */
  getArticles(params) {
    return apiClient.get('/articles/', { params })
  },
  /** @param {number} id */
  getArticle(id) {
    return apiClient.get(`/articles/${id}`)
  },
  /** @param {number} id @param {any} data */
  updateArticle(id, data) {
    return apiClient.put(`/articles/${id}`, data)
  },
  /** @param {number} id */
  deleteArticle(id) {
    return apiClient.delete(`/articles/${id}`)
  },
  /** @param {any} params */
  getPublicArticles(params) {
    return apiClient.get('/articles/public/', { params })
  },
  /** @param {string} url @param {any} params */
  getPublicArticlesRaw(url, params) {
    return apiClient.get(url, { params })
  },
  /** @param {string} slug */
  getArticleBySlug(slug) {
    return apiClient.get(`/articles/public/slug/${slug}`)
  },
  /** @param {any} params */
  getHotArticles(params) {
    return apiClient.get('/articles/public/hot', { params })
  },
  /** @param {number} articleId */
  getAuditLogs(articleId) {
    return apiClient.get(`/articles/${articleId}/audit_logs`)
  },
  /** @param {number} id */
  submitArticle(id) {
    return apiClient.post(`/articles/${id}/submit`)
  },
  /** @param {number} id */
  approveArticle(id) {
    return apiClient.post(`/articles/${id}/approve`)
  },
  /** @param {number} id @param {any} data */
  rejectArticle(id, data) {
    return apiClient.post(`/articles/${id}/reject`, data || {})
  },
  /** @param {number} id */
  unpublishArticle(id) {
    return apiClient.post(`/articles/${id}/unpublish`)
  },
  /** @param {number} id @param {any} data */
  scheduleArticle(id, data) {
    return apiClient.post(`/articles/${id}/schedule`, data || {})
  },
  /** @param {number} id */
  unscheduleArticle(id) {
    return apiClient.post(`/articles/${id}/unschedule`)
  },
  /** @param {number} id */
  likeArticle(id) {
    return apiClient.post(`/articles/${id}/like`)
  },
  /** @param {number} id */
  bookmarkArticle(id) {
    return apiClient.post(`/articles/${id}/bookmark`)
  },
  /** @param {number} id @param {any} params */
  getArticleVersions(id, params) {
    return apiClient.get(`/articles/${id}/versions`, { params })
  },
  /** @param {number} id @param {any} data */
  createArticleVersion(id, data) {
    return apiClient.post(`/articles/${id}/versions`, data || {})
  },
  /** @param {number} id @param {number} versionNo */
  rollbackVersion(id, versionNo) {
    return apiClient.post(`/articles/${id}/versions/${versionNo}/rollback`)
  },
  /** @param {number} id @param {number} versionNo @param {number} targetNo */
  diffVersions(id, versionNo, targetNo) {
    return apiClient.get(`/articles/${id}/versions/${versionNo}/diff?target=${targetNo}`)
  },

  // ── 用户 / 认证 ───────────────────────────────────
  getCurrentUser() {
    return apiClient.get('/users/me')
  },
  /** @param {any} data */
  login(data) {
    return apiClient.post('/auth/login', data)
  },
  /** @param {any} data */
  register(data) {
    return apiClient.post('/auth/register', data)
  },
  logout() {
    return apiClient.post('/auth/logout')
  },
  /** @param {any} data */
  changePassword(data) {
    return apiClient.post('/auth/change_password', data)
  },
  /** @param {any} params */
  getUsers(params) {
    return apiClient.get('/users/', { params })
  },
  /** @param {number} id @param {any} data */
  updateUserRole(id, data) {
    return apiClient.patch(`/users/${id}/role`, data)
  },
  /** @param {number} id @param {any} data */
  updateUser(id, data) {
    return apiClient.patch(`/users/${id}`, data)
  },
  /** @param {number} id */
  resetUserPassword(id) {
    return apiClient.post(`/users/${id}/reset-password`)
  },
  /** @param {number} id */
  deleteUser(id) {
    return apiClient.delete(`/users/${id}`)
  },
  /** @param {number} id */
  getPublicUserStats(id) {
    return apiClient.get(`/users/public/${id}/stats`)
  },

  // ── 评论 / 搜索 ───────────────────────────────────
  /** @param {number} articleId */
  getArticleComments(articleId) {
    return apiClient.get(`/comments/article/${articleId}`)
  },
  /** @param {any} data */
  createComment(data) {
    return apiClient.post('/comments/', data)
  },
  /** @param {any} params */
  getPendingComments(params) {
    return apiClient.get('/comments/pending', { params })
  },
  /** @param {number} id @param {any} data */
  moderateComment(id, data) {
    return apiClient.post(`/comments/moderate/${id}`, data)
  },
  /** @param {any} params */
  search(params) {
    return apiClient.get('/search/', { params })
  },

  // ── 分类 / 标签（公共入口）────────────────────────
  /** @param {any} params */
  getRootCategories(params) {
    return apiClient.get('/categories/', { params })
  },
  /** @param {any} params */
  getRootTags(params) {
    return apiClient.get('/tags/', { params })
  },
  getPublicTaxonomy() {
    return apiClient.get('/taxonomy', { baseURL: '/public/v1' })
  },
  // ── 项目(impl-P2 分组 A)─────────────────────────
  getPublicProjects() {
    return apiClient.get('/projects/')
  },
  /** @param {string} slug */
  getPublicProjectBySlug(slug) {
    return apiClient.get(`/projects/${encodeURIComponent(slug)}`)
  },
  // 管理端(需 editor/admin)
  adminListProjects() {
    return apiClient.get('/projects/admin/list')
  },
  /** @param {any} data */
  createProject(data) {
    return apiClient.post('/projects/', data)
  },
  /** @param {number} id @param {any} data */
  updateProject(id, data) {
    return apiClient.put(`/projects/${id}`, data)
  },
  /** @param {number} id */
  deleteProject(id) {
    return apiClient.delete(`/projects/${id}`)
  },
  /** @param {FormData} formData */
  uploadImage(formData) {
    return apiClient.post('/uploads/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  /** @param {string} path @param {any} params */
  getPublicV1(path, params) {
    return apiClient.get(`/public/v1${path}`, { params })
  },

  // ── 评论管理（admin）─────────────────────────────
  /** @param {any} params */
  getAdminComments(params) {
    return apiClient.get('/comments/admin/list', { params })
  },
  getCommentStats() {
    return apiClient.get('/comments/admin/stats')
  },
  /** @param {any} data */
  moderateCommentBatch(data) {
    return apiClient.post('/comments/moderate/batch', data)
  },

  // ── 安全监控 ──────────────────────────────────────
  /** @param {number} id @param {any} data */
  handleSecurityEvent(id, data) {
    return apiClient.post(`/security/events/${id}/handle`, data)
  },
  /** @param {any} params */
  getAccessStatsToday(params) {
    return apiClient.get('/security/access-stats/today', { params })
  },

  // ── 日志管理 ──────────────────────────────────────
  getLogUsers() {
    return apiClient.get('/admin/logs/users')
  },
  /** @param {any} params */
  exportLogs(params) {
    return apiClient.get('/admin/logs/export', { params })
  },
  /** @param {any} data */
  cleanupLogs(data) {
    return apiClient.post('/admin/logs/cleanup', data)
  },

  // ── 搜索同义词 ────────────────────────────────────
  getSearchSynonyms() {
    return apiClient.get('/search/synonyms/')
  },
  /** @param {any} data */
  createSearchSynonym(data) {
    return apiClient.post('/search/synonyms/', data)
  },
  /** @param {string} term */
  deleteSearchSynonym(term) {
    return apiClient.delete(`/search/synonyms/${encodeURIComponent(term)}`)
  },
}

// ── 导出 ──────────────────────────────────────────────

export const API = { ...GeneratedAPI, ...HandwrittenAPI }
export default API
