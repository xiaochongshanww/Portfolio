<template>
  <div class="hot-articles-page">
    <div class="max-w-4xl mx-auto py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-8">热门文章</h1>
      <div v-if="loading" class="space-y-6">
        <div v-for="n in 5" :key="n" class="bg-white rounded-lg shadow-sm p-6">
          <div class="animate-pulse">
            <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div class="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
      <div v-else class="space-y-6">
        <article v-for="article in articles" :key="article.id" 
                 class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <RouterLink :to="`/article/${article.slug}`" class="block">
            <h2 class="text-xl font-semibold text-gray-900 mb-2 hover:text-blue-600 transition-colors">
              {{ article.title }}
            </h2>
            <p class="text-gray-600 mb-4">{{ article.summary || '暂无摘要' }}</p>
            <div class="flex items-center justify-between text-sm text-gray-500">
              <span>{{ article.author?.name || '匿名作者' }}</span>
              <div class="flex items-center gap-4">
                <span>{{ article.views_count || 0 }} 次阅读</span>
                <span>{{ article.likes_count || 0 }} 个赞</span>
                <span v-if="article.score">热度: {{ article.score }}</span>
              </div>
            </div>
          </RouterLink>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import apiClient from '../apiClient';

const articles = ref([]);
const loading = ref(false);

async function loadHotArticles() {
  loading.value = true;
  try {
    const response = await apiClient.get('/articles/public/hot', {
      params: { page: 1, page_size: 20, window_hours: 72 }
    });
    articles.value = response.data.data?.list || [];
  } catch (error) {
    console.error('加载热门文章失败:', error);
  } finally {
    loading.value = false;
  }
}

onMounted(loadHotArticles);
</script>