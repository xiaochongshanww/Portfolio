<template>
  <div class="modern-filter-bar">
    <div class="filter-container">
      <div class="filter-left">
        <div class="filter-group">
          <div class="filter-item">
            <el-select v-model="status" placeholder="状态筛选" clearable class="modern-select" @change="emit('change')">
              <el-option label="全部状态" value="" />
              <el-option label="草稿" value="draft" />
              <el-option label="待审核" value="pending" />
              <el-option label="已发布" value="published" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </div>

          <div class="filter-item">
            <el-select v-model="categoryId" placeholder="分类筛选" clearable class="modern-select" @change="emit('change')">
              <el-option label="全部分类" value="" />
              <el-option 
                v-for="cat in categories" 
                :key="cat.id" 
                :label="cat.name" 
                :value="cat.id" 
              />
            </el-select>
          </div>

          <div v-if="isAdmin" class="filter-item">
            <el-select 
              v-model="authorId" 
              placeholder="作者筛选" 
              clearable 
              class="modern-select"
              @change="emit('change')"
            >
              <el-option label="全部作者" value="" />
              <el-option 
                v-for="author in authors" 
                :key="author.id" 
                :label="author.nickname || author.email" 
                :value="author.id" 
              />
            </el-select>
          </div>

          <div class="filter-item search-item">
            <el-input
              v-model="search"
              placeholder="搜索文章标题..."
              clearable
              class="modern-search-input"
              @clear="emit('change')"
              @keyup.enter="emit('change')"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
        </div>
      </div>

      <div class="filter-right">
        <button :disabled="loading" class="refresh-btn" @click="emit('refresh')">
          <el-icon size="16" :class="{ 'is-loading': loading }"><Refresh /></el-icon>
          <span>刷新</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Search, Refresh } from '@element-plus/icons-vue';

defineProps({
  categories: {
    /** @type {import('vue').PropType<any[]>} */
    type: Array,
    default: () => []
  },
  authors: {
    /** @type {import('vue').PropType<any[]>} */
    type: Array,
    default: () => []
  },
  isAdmin: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
});

const status = defineModel('status', { type: String, default: '' });
const categoryId = defineModel('categoryId', { type: String, default: '' });
const authorId = defineModel('authorId', { type: String, default: '' });
const search = defineModel('search', { type: String, default: '' });

const emit = defineEmits(['change', 'refresh']);
</script>

<style scoped>
/* 筛选栏样式 */
.modern-filter-bar {
  margin-bottom: 1.5rem;
  position: relative;
}

.filter-container {
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.9) 0%, 
      rgba(248, 250, 252, 0.8) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.05),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-left {
  flex: 1;
}

.filter-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
}

.filter-item {
  position: relative;
}

.modern-select {
  width: 160px;
}

.search-item {
  min-width: 240px;
  flex: 1;
}

.modern-search-input {
  width: 100%;
}

.filter-right {
  margin-left: 1rem;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.05));
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  color: #8b5cf6;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.refresh-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.1));
  border-color: rgba(139, 92, 246, 0.3);
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.2);
}

.refresh-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-btn .is-loading {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .filter-container {
    flex-direction: column;
    gap: 1rem;
  }
  
  .filter-group {
    width: 100%;
    justify-content: flex-start;
  }
  
  .filter-item {
    flex: 1;
    min-width: 140px;
  }
  
  .search-item {
    min-width: 200px;
  }
  
  .filter-right {
    margin-left: 0;
    align-self: flex-end;
  }
}

@media (max-width: 768px) {
  .filter-container {
    padding: 1rem;
  }
  
  .filter-group {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .filter-item {
    width: 100%;
  }
  
  .modern-select,
  .modern-search-input {
    width: 100%;
  }
  
  .filter-right {
    align-self: stretch;
  }
  
  .refresh-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
