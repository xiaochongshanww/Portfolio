<template>
  <div class="tags-page-test p-8">
    <h1 class="text-2xl mb-4">TagsPage 样式测试</h1>
    
    <!-- 复制TagsPage的统计面板 -->
    <div class="modern-stats-grid mb-8">
      <div class="stat-card stat-card-blue">
        <div class="stat-icon-wrapper">
          <el-icon size="24"><Document /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-number">5</div>
          <div class="stat-label">总标签数</div>
        </div>
      </div>
    </div>

    <!-- 复制TagsPage的视图切换器 -->
    <div class="modern-view-switcher mb-8">
      <div class="view-switcher-container">
        <button 
          v-for="view in viewModes" 
          :key="view.value"
          @click="currentView = view.value"
          :class="[
            'view-switcher-btn',
            currentView === view.value ? 'active' : ''
          ]"
        >
          <div class="btn-icon-wrapper">
            <el-icon size="18"><component :is="view.icon" /></el-icon>
          </div>
          <span class="btn-label">{{ view.label }}</span>
        </button>
      </div>
    </div>

    <!-- 简化版的卡片测试 -->
    <div class="modern-tag-card mb-8">
      <div class="card-header">
        <div class="tag-icon">
          <el-icon size="20"><Document /></el-icon>
        </div>
        <div class="article-count">3</div>
      </div>
      <div class="card-content">
        <h3 class="tag-title">#测试标签</h3>
      </div>
      <div class="card-footer">
        <span class="explore-text">浏览文章</span>
        <div class="arrow-icon">
          <el-icon size="16"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 测试标签云计数样式 -->
    <div class="mb-4">
      <h3 class="text-lg mb-2">标签云计数测试:</h3>
      <button class="tag-cloud-item">
        #测试标签
        <span class="tag-count">(5)</span>
      </button>
      <button class="tag-cloud-item mt-2">
        #另一个标签
        <span class="tag-count">(12)</span>
      </button>
    </div>

    <!-- 测试不同的CSS组合 -->
    <div class="mb-4">
      <h3 class="text-lg mb-2">直接图标测试:</h3>
      <el-icon size="24" style="color: red;"><Document /></el-icon>
      <el-icon size="24" style="color: blue;"><Reading /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Document, Reading, ArrowRight, Grid, List, Compass } from '@element-plus/icons-vue'

const viewModes = [
  { label: '标签云', value: 'cloud', icon: Compass },
  { label: '网格', value: 'grid', icon: Grid },
  { label: '列表', value: 'list', icon: List }
]

const currentView = ref('cloud')
</script>

<style scoped>
.tags-page-test {
  background: 
    radial-gradient(circle at 20% 50%, rgba(59, 130, 246, 0.03) 0%, transparent 40%),
    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.03) 0%, transparent 40%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 30%, #ffffff 70%, #fafbfe 100%);
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

/* 复制关键样式 */
.modern-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  padding: 2rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.stat-card-blue {
  --stat-gradient: linear-gradient(135deg, #3b82f6, #1d4ed8);
}

.stat-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: var(--stat-gradient);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 800;
  color: #3b82f6;
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
}

.modern-view-switcher {
  display: flex;
  justify-content: center;
}

.view-switcher-container {
  background: rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  padding: 8px;
  display: flex;
  gap: 4px;
}

.view-switcher-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 16px;
  background: transparent;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
}

.view-switcher-btn.active {
  color: white;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
}

.btn-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
}

.btn-label {
  font-weight: 600;
}

.modern-tag-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  padding: 28px;
  max-width: 300px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tag-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.article-count {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(6, 182, 212, 0.05));
  color: #8b5cf6;
  border: 1px solid rgba(139, 92, 246, 0.15);
  padding: 6px 16px;
  border-radius: 24px;
  font-size: 0.8rem;
  font-weight: 700;
}

.card-content {
  margin-bottom: 20px;
}

.tag-title {
  font-size: 1.3rem;
  font-weight: 800;
  color: #1e293b;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
}

.explore-text {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
}

.arrow-icon {
  color: #94a3b8;
  padding: 8px;
  border-radius: 12px;
  background: rgba(148, 163, 184, 0.1);
}

/* 标签云相关样式 */
.tag-cloud-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 30px;
  cursor: pointer;
  font-weight: 600;
  text-decoration: none;
  margin: 4px;
}

.tag-count {
  font-size: 0.75rem;
  opacity: 0.8;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: 4px;
  font-weight: 600;
}
</style>