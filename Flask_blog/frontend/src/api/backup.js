import api from '@/apiClient'

export const backupApi = {
  // 获取备份统计信息
  getStatistics() {
    return api.get('/backup/statistics')
  },

  // 获取备份配置
  getBackupConfigs() {
    return api.get('/backup/config')
  },

  // 获取备份记录列表
  getBackupRecords(params = {}) {
    return api.get('/backup/records', { params })
  },

  // 获取单个备份记录详情
  getBackupRecord(backupId) {
    return api.get(`/backup/${backupId}`)
  },

  // 创建备份
  createBackup(data) {
    return api.post('/backup/create', data)
  },

  // 取消备份任务
  cancelBackup(backupId) {
    return api.post(`/backup/${backupId}/cancel`)
  },

  // 删除备份
  deleteBackup(backupId) {
    return api.delete(`/backup/${backupId}`)
  },

  // 下载备份文件
  async downloadBackup(backupId) {
    try {
      const response = await api.get(`/backup/${backupId}/download`, {
        responseType: 'blob'
      })
      
      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // 从响应头获取文件名，如果没有则使用默认名称
      const contentDisposition = response.headers['content-disposition']
      let filename = `backup_${backupId}.tar.gz`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '')
        }
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      
      // 清理
      window.URL.revokeObjectURL(url)
      document.body.removeChild(link)
      
      return { success: true, filename }
    } catch (error) {
      console.error('下载备份失败:', error)
      throw error
    }
  },

  // 恢复备份
  restoreBackup(backupId, options = {}) {
    return api.post(`/backup/${backupId}/restore`, options)
  },

  // 获取备份任务列表
  getBackupTasks(params = {}) {
    return api.get('/backup/tasks', { params })
  },

  // 创建备份任务
  createBackupTask(data) {
    return api.post('/backup/tasks', data)
  },

  // 更新备份任务
  updateBackupTask(taskId, data) {
    return api.put(`/backup/tasks/${taskId}`, data)
  },

  // 删除备份任务
  deleteBackupTask(taskId) {
    return api.delete(`/backup/tasks/${taskId}`)
  },

  // 启用/禁用备份任务
  toggleBackupTask(taskId, enabled) {
    return api.patch(`/backup/tasks/${taskId}/toggle`, { enabled })
  },

  // 手动执行备份任务
  executeBackupTask(taskId) {
    return api.post(`/backup/tasks/${taskId}/execute`)
  },

  // 获取恢复记录列表
  getRestoreRecords(params = {}) {
    return api.get('/backup/restores', { params })
  },

  // 获取恢复记录详情（用于实时进度监控）
  getRestoreProgress(restoreId) {
    return api.get(`/backup/restores/${restoreId}/detail`)
  },

  // 取消恢复任务
  cancelRestore(restoreId) {
    return api.post(`/backup/restores/${restoreId}/cancel`)
  },

  // 清理卡住的恢复任务
  cleanupStuckRestores() {
    return api.post('/backup/restores/cleanup')
  },

  // 获取备份配置项
  getBackupConfig() {
    return api.get('/backup/config')
  },

  // 更新备份配置
  updateBackupConfig(configs) {
    return api.put('/backup/config', { configs })
  }
}

export default backupApi