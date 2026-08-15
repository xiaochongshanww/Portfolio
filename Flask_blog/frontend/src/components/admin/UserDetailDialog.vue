<template>
  <el-dialog
    :model-value="visible"
    :title="`用户详情 - ${user?.nickname || user?.email}`"
    width="600px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div v-if="user" class="user-detail">
      <div class="detail-section">
        <h4>基本信息</h4>
        <div class="detail-grid">
          <div class="detail-item">
            <span class="label">邮箱:</span>
            <span class="value">{{ user.email }}</span>
          </div>
          <div class="detail-item">
            <span class="label">昵称:</span>
            <span class="value">{{ user.nickname || '未设置' }}</span>
          </div>
          <div class="detail-item">
            <span class="label">角色:</span>
            <el-tag :type="getRoleType(user.role)">
              {{ getRoleText(user.role) }}
            </el-tag>
          </div>
          <div class="detail-item">
            <span class="label">注册时间:</span>
            <span class="value">{{ formatDate(user.created_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="user.bio" class="detail-section">
        <h4>个人简介</h4>
        <p class="bio-content">{{ user.bio }}</p>
      </div>

      <div v-if="user.social_links" class="detail-section">
        <h4>社交链接</h4>
        <div class="social-links">
          <pre class="social-json">{{ user.social_links }}</pre>
        </div>
      </div>

      <div class="detail-section">
        <h4>统计信息</h4>
        <div class="stats-grid">
          <div class="stat-box">
            <div class="stat-number">{{ user.article_count || 0 }}</div>
            <div class="stat-text">发布文章</div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  /** @type {any} */
  user: { type: Object, default: null }
});
defineEmits(['update:visible']);

/**
 * @param {string | undefined} role
 * @returns {'info' | 'success' | 'primary' | 'warning' | 'danger'}
 */
function getRoleType(role) {
  switch (role) {
    case 'admin': return 'danger';
    case 'editor': return 'warning';
    case 'author': return 'info';
    default: return 'info';
  }
}

/** @param {string | undefined} role */
function getRoleText(role) {
  switch (role) {
    case 'admin': return '管理员';
    case 'editor': return '编辑';
    case 'author': return '作者';
    default: return role;
  }
}

/** @param {string | number | Date} dateStr */
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('zh-CN');
}
</script>

<style scoped>
.user-detail .detail-section {
  margin-bottom: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
}
.user-detail .detail-section:last-child {
  border-bottom: none;
}
.user-detail h4 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #303133;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.detail-item .label {
  color: #909399;
  margin-right: 6px;
}
.bio-content {
  margin: 0;
  color: #606266;
  line-height: 1.6;
}
.social-json {
  margin: 0;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
.stats-grid {
  display: flex;
  gap: 16px;
}
.stat-box {
  text-align: center;
  padding: 12px 20px;
  background: #f5f7fa;
  border-radius: 6px;
}
.stat-number {
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
}
.stat-text {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
