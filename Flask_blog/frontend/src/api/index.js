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
  getCategories(params) {
    return apiClient.get('/taxonomy/categories/', { params })
  },
  createCategory(data) {
    return apiClient.post('/taxonomy/categories/', data)
  },
  updateCategory(id, data) {
    return apiClient.patch(`/taxonomy/categories/${id}`, data)
  },
  deleteCategory(id) {
    return apiClient.delete(`/taxonomy/categories/${id}`)
  },

  getTags(params) {
    return apiClient.get('/taxonomy/tags/', { params })
  },
  createTag(data) {
    return apiClient.post('/taxonomy/tags/', data)
  },
  updateTag(id, data) {
    return apiClient.patch(`/taxonomy/tags/${id}`, data)
  },
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
  getMediaList(params) {
    return apiClient.get('/media', { params })
  },
  getMediaDetail(id) {
    return apiClient.get(`/media/${id}`)
  },
  uploadMedia(formData) {
    return apiClient.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },
  updateMedia(id, data) {
    return apiClient.put(`/media/${id}`, data)
  },
  deleteMedia(id) {
    return apiClient.delete(`/media/${id}`)
  },
  downloadMedia(id) {
    return apiClient.get(`/media/${id}/download`, { responseType: 'blob' })
  },
  getMediaFolders(params) {
    return apiClient.get('/media/folders', { params })
  },
  createMediaFolder(data) {
    return apiClient.post('/media/folders', data)
  },
  updateMediaFolder(id, data) {
    return apiClient.put(`/media/folders/${id}`, data)
  },
  deleteMediaFolder(id) {
    return apiClient.delete(`/media/folders/${id}`)
  },
  getMediaStats() {
    return apiClient.get('/media/stats')
  },
  searchMedia(params) {
    return apiClient.post('/media/search', params)
  },

  // ── 备份 ───────────────────────────────────────────
  getBackupRecords(params) {
    return apiClient.get('/backup/records', { params })
  },
  getBackupRecord(id) {
    return apiClient.get(`/backup/${id}`)
  },
  createBackup(data) {
    return apiClient.post('/backup/create', data || {})
  },
  cancelBackup(id) {
    return apiClient.post(`/backup/${id}/cancel`)
  },
  deleteBackup(id) {
    return apiClient.delete(`/backup/${id}`)
  },
  downloadBackup(id) {
    return apiClient.get(`/backup/${id}/download`, { responseType: 'blob' })
  },
  restoreBackup(id, options) {
    return apiClient.post(`/backup/${id}/restore`, options || {})
  },
  getBackupConfig() {
    return apiClient.get('/backup/config')
  },
  updateBackupConfig(data) {
    return apiClient.put('/backup/config', data)
  },
  getBackupStatistics() {
    return apiClient.get('/backup/statistics')
  },
  cleanupBackups() {
    return apiClient.post('/backup/cleanup')
  },
  getBackupTasks(params) {
    return apiClient.get('/backup/tasks', { params })
  },
  getRestoreRecords(params) {
    return apiClient.get('/backup/restores', { params })
  },
  getRestoreProgress(id) {
    return apiClient.get(`/backup/restores/${id}`)
  },
  cancelRestore(id) {
    return apiClient.post(`/backup/restores/${id}/cancel`)
  },

  // ── 设置 ───────────────────────────────────────────
  getSettings(section) {
    return apiClient.get(`/settings/${section}`)
  },
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
  getSecurityEvents(params) {
    return apiClient.get('/security/events/recent', { params })
  },
  getThreatTrends() {
    return apiClient.get('/security/threat-trends')
  },
  blockIp(data) {
    return apiClient.post('/security/block-ip', data)
  },

  // ── 日志 ───────────────────────────────────────────
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
  trackVisit(data) {
    return apiClient.post('/metrics/track', data)
  },
}

// ── 导出 ──────────────────────────────────────────────

export const API = { ...GeneratedAPI, ...HandwrittenAPI }
export default API
