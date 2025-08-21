<template>
  <div class="comment-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">评论管理</h1>
        <p class="page-description">审核和管理用户评论，维护社区讨论质量</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-label">待审核</span>
          <span class="stat-value pending">{{ stats.pending }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">今日评论</span>
          <span class="stat-value">{{ stats.today }}</span>
        </div>
      </div>
    </div>

    <!-- 开发中提示 -->
    <div class="development-notice">
      <el-alert
        title="功能开发中"
        description="评论管理功能正在开发中，敬请期待！"
        type="info"
        :closable="false"
        show-icon
      />
      
      <div class="feature-preview">
        <h3>即将上线的功能：</h3>
        <ul>
          <li>📝 评论列表查看和搜索</li>
          <li>✅ 评论审核（通过/拒绝）</li>
          <li>🚫 批量删除垃圾评论</li>
          <li>👤 评论者信息管理</li>
          <li>🔍 敏感词检测和过滤</li>
          <li>📊 评论统计和分析</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue';

// 模拟统计数据
const stats = reactive({
  pending: 0,
  today: 0
});
</script>

<style scoped>
.comment-management {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.header-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.stat-value.pending {
  color: #f59e0b;
}

.development-notice {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 24px;
}

.feature-preview {
  margin-top: 20px;
}

.feature-preview h3 {
  margin: 0 0 16px 0;
  color: #1f2937;
  font-size: 18px;
}

.feature-preview ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-preview li {
  padding: 8px 0;
  color: #4b5563;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-stats {
    align-self: stretch;
    justify-content: space-around;
  }
}
</style>