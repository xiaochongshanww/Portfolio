<template>
  <div class="category-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">分类管理</h1>
        <p class="page-description">管理文章分类，构建清晰的内容结构</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新建分类
        </el-button>
      </div>
    </div>

    <!-- 开发中提示 -->
    <div class="development-notice">
      <el-alert
        title="功能开发中"
        description="分类管理功能正在开发中，敬请期待！"
        type="info"
        :closable="false"
        show-icon
      />
      
      <div class="feature-preview">
        <h3>即将上线的功能：</h3>
        <ul>
          <li>📁 创建和编辑分类</li>
          <li>🌳 支持多级分类结构</li>
          <li>🔄 分类排序和重新组织</li>
          <li>📊 查看每个分类的文章数量</li>
          <li>🎨 分类图标和颜色设置</li>
          <li>🔍 分类搜索和筛选</li>
          <li>📋 批量操作和管理</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

function showCreateDialog() {
  ElMessage.info('新建分类功能开发中');
}
</script>

<style scoped>
.category-management {
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

.header-actions {
  display: flex;
  gap: 12px;
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
}
</style>