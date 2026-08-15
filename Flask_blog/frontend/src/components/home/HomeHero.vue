<template>
  <section class="hero-section bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-12 px-6 rounded-xl relative overflow-hidden mb-6">
    <!-- 背景装饰 -->
    <div class="absolute inset-0 opacity-10">
      <div class="absolute top-10 left-10 w-20 h-20 bg-blue-400 rounded-full blur-xl" />
      <div class="absolute top-20 right-20 w-16 h-16 bg-purple-400 rounded-full blur-lg" />
      <div class="absolute bottom-10 left-1/3 w-12 h-12 bg-indigo-400 rounded-full blur-lg" />
    </div>
    
    <div class="relative z-10 text-center max-w-3xl mx-auto">
      <h1 class="text-3xl md:text-5xl font-bold text-gray-800 mb-4 leading-tight">
        发现与创作
      </h1>
      <p class="text-base md:text-lg text-gray-600 mb-6 leading-relaxed">
        探索优质内容，分享独特见解，与志同道合的人一起成长
      </p>
      
      <!-- 搜索框 -->
      <div class="max-w-md mx-auto mb-6">
        <div class="relative">
          <el-input 
            v-model="searchInput" 
            placeholder="搜索文章、标签或作者..." 
            clearable 
            size="large"
            class="search-input"
            @keyup.enter="$emit('search')"
          >
            <template #prefix>
              <el-icon class="text-gray-400"><Search /></el-icon>
            </template>
            <template #append>
              <el-button :loading="loading" type="primary" size="large" @click="$emit('search')">
                搜索
              </el-button>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 快速筛选标签 -->
      <div class="flex flex-wrap justify-center gap-3 mb-6 quick-filter-container">
        <button
          v-for="c in categories.slice(0, 6)" 
          :key="c.id" 
          :class="[
            'modern-category-btn',
            selectedCategory === String(c.id) ? 'modern-category-btn-active' : 'modern-category-btn-default'
          ]"
          @click="$emit('category-click', c.id)"
        >
          <span class="category-name">{{ c.name }}</span>
          <el-icon v-if="selectedCategory === String(c.id)" size="14" class="close-icon">
            <Close />
          </el-icon>
        </button>
        
        <!-- 查看全部分类按钮 -->
        <router-link 
          to="/categories" 
          class="modern-view-all-btn"
        >
          <el-icon size="16" class="view-all-icon"><More /></el-icon>
          <span>浏览全部</span>
        </router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { Search, Close, More } from '@element-plus/icons-vue';

const props = defineProps({
  searchInput: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  categories: {
    type: /** @type {import('vue').PropType<import('@/types').Category[]>} */ (Array),
    default: () => []
  },
  selectedCategory: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['search', 'category-click', 'update:searchInput']);

const searchInput = computed({
  get: () => props.searchInput,
  set: (value) => emit('update:searchInput', value)
});
</script>

<style scoped>
/* ===== 现代化分类按钮样式 ===== */
.quick-filter-container {
  align-items: center;
  row-gap: 12px;
}

.modern-category-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 25px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.modern-category-btn-default {
  background: rgba(255, 255, 255, 0.8);
  color: #6b7280;
  border: 1px solid rgba(209, 213, 219, 0.6);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.modern-category-btn-default:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(59, 130, 246, 0.15);
}

.modern-category-btn-active {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border: 1px solid transparent;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.modern-category-btn-active:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.close-icon {
  margin-left: 4px;
  opacity: 0.8;
}

.modern-view-all-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 25px;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.9);
  color: #6366f1;
  border: 1px dashed rgba(99, 102, 241, 0.4);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.modern-view-all-btn:hover {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.6);
  border-style: solid;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.2);
  color: #4f46e5;
}

.view-all-icon {
  transition: transform 0.2s ease;
}

.modern-view-all-btn:hover .view-all-icon {
  transform: rotate(90deg);
}

/* 响应式优化 */
@media (max-width: 640px) {
  .quick-filter-container {
    gap: 8px;
  }
  
  .modern-category-btn,
  .modern-view-all-btn {
    padding: 8px 14px;
    font-size: 13px;
    border-radius: 20px;
  }
}

/* 搜索框主容器样式 */
.search-input {
  --el-border-radius-base: 12px;
}

.search-input :deep(.el-input) {
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

/* 搜索输入框样式 - 完全重写确保一致性 */
.search-input :deep(.el-input-group) {
  display: flex;
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 12px 0 0 12px !important;
  border: 2px solid #e5e7eb !important;
  border-right: none !important;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: #3b82f6 !important;
  border-right: none !important;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #3b82f6 !important;
  border-right: none !important;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 0 0 3px rgb(59 130 246 / 0.1);
}

.search-input :deep(.el-input-group__append) {
  border-radius: 0 12px 12px 0 !important;
  border: 2px solid #3b82f6 !important;
  border-left: none !important;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  transition: all 0.3s ease;
}

.search-input :deep(.el-input-group__append .el-button) {
  border: none !important;
  border-radius: 0 10px 10px 0 !important;
  background: #3b82f6 !important;
  color: white !important;
  font-weight: 500;
  padding: 0 20px;
  height: 100%;
}

.search-input :deep(.el-input-group__append .el-button:hover) {
  background: #2563eb !important;
}

/* 修复焦点状态下的边框连接 */
.search-input :deep(.el-input__wrapper.is-focus) + .el-input-group__append {
  border-color: #3b82f6 !important;
}

@media (max-width: 768px) {
  .hero-section {
    padding: 2rem 1rem;
    margin: 0 0 2rem 0;
  }
}

@media (max-width: 480px) {
  .hero-section {
    padding: 1.5rem 0.5rem;
  }
}
</style>
