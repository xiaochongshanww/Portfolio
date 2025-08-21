<template>
  <div class="categories-page">
    <div class="max-w-4xl mx-auto py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-8">文章分类</h1>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="category in categories" :key="category.id" 
             class="category-card bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <RouterLink :to="`/category/${category.id}`" class="block">
            <h3 class="text-xl font-semibold text-gray-900 mb-2">{{ category.name }}</h3>
            <p class="text-gray-600 text-sm">{{ category.description || '暂无描述' }}</p>
            <div class="mt-4 text-blue-600 text-sm font-medium">
              查看文章 →
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

const categories = ref([]);
const loading = ref(false);

async function loadCategories() {
  loading.value = true;
  try {
    const response = await apiClient.get('/taxonomy/categories/');
    categories.value = response.data.data || [];
  } catch (error) {
    console.error('加载分类失败:', error);
  } finally {
    loading.value = false;
  }
}

onMounted(loadCategories);
</script>

<style scoped>
.category-card:hover {
  transform: translateY(-2px);
  transition: all 0.2s ease;
}
</style>