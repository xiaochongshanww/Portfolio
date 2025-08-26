<template>
  <div class="categories-page">
    <div class="max-w-4xl mx-auto py-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-4">所有分类</h1>
        <p class="text-gray-600 max-w-2xl mx-auto">
          探索博客的所有文章分类，找到您感兴趣的内容主题
        </p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="category in categories" :key="category.id" 
             class="modern-category-card group">
          <RouterLink :to="`/category/${category.id}`" class="card-link">
            <!-- 卡片头部 -->
            <div class="card-header">
              <div class="category-icon">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                </svg>
              </div>
              <div class="article-count">
                {{ category.article_count || 0 }}
              </div>
            </div>
            
            <!-- 卡片内容 -->
            <div class="card-content">
              <h3 class="category-title">{{ category.name }}</h3>
              <p class="category-description">{{ category.description || '探索这个分类下的精彩内容' }}</p>
            </div>
            
            <!-- 卡片底部 -->
            <div class="card-footer">
              <span class="explore-text">探索内容</span>
              <div class="arrow-icon">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path>
                </svg>
              </div>
            </div>
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '../apiClient';
import { setMeta } from '../composables/useMeta';

const categories = ref([]);
const loading = ref(false);

async function loadCategories() {
  loading.value = true;
  try {
    const response = await apiClient.get('/taxonomy', { baseURL: '/public/v1' });
    categories.value = response.data.data?.categories || [];
    console.log('✅ 分类加载成功，数量:', categories.value.length);
    
    // 设置SEO元数据
    setMeta({
      title: '所有分类 - 探索精彩内容',
      description: '浏览博客的所有文章分类，找到您感兴趣的内容主题，探索更多精彩文章',
      url: window.location.href
    });
  } catch (error) {
    console.error('加载分类失败:', error);
  } finally {
    loading.value = false;
  }
}

onMounted(loadCategories);
</script>

<style scoped>
.categories-page {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #ffffff 100%);
  min-height: 100vh;
  padding: 2rem 1rem;
}

/* ===== 现代化分类卡片样式 ===== */
.modern-category-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 20px;
  padding: 24px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.modern-category-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6, #6366f1, #8b5cf6);
  transform: scaleX(0);
  transition: transform 0.3s ease;
  transform-origin: left;
}

.modern-category-card:hover::before {
  transform: scaleX(1);
}

.modern-category-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 40px rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(255, 255, 255, 0.95);
}

.card-link {
  display: block;
  text-decoration: none;
  color: inherit;
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.category-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.modern-category-card:hover .category-icon {
  transform: rotate(10deg) scale(1.1);
  background: linear-gradient(135deg, #1d4ed8 0%, #4f46e5 100%);
}

.article-count {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.modern-category-card:hover .article-count {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
  transform: scale(1.05);
}

.card-content {
  margin-bottom: 20px;
}

.category-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
  line-height: 1.3;
  transition: color 0.3s ease;
}

.modern-category-card:hover .category-title {
  color: #3b82f6;
}

.category-description {
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
}

.explore-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: #64748b;
  transition: color 0.3s ease;
}

.modern-category-card:hover .explore-text {
  color: #3b82f6;
}

.arrow-icon {
  color: #94a3b8;
  transition: all 0.3s ease;
  transform: translateX(0);
}

.modern-category-card:hover .arrow-icon {
  color: #3b82f6;
  transform: translateX(4px);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .modern-category-card {
    padding: 20px;
    border-radius: 16px;
  }
  
  .category-icon {
    width: 36px;
    height: 36px;
  }
  
  .category-title {
    font-size: 1.125rem;
  }
}

@media (max-width: 640px) {
  .categories-page {
    padding: 1rem;
  }
  
  .modern-category-card {
    padding: 16px;
  }
  
  .card-header {
    margin-bottom: 12px;
  }
  
  .card-content {
    margin-bottom: 16px;
  }
}
</style>