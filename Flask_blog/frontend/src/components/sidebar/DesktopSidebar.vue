<template>
  <aside class="desktop-sidebar w-full max-w-xs mx-auto md:mx-0 sticky top-24" style="padding-top: 24px;">
    <!-- 博主简介卡片 -->
    <AuthorCard />
    
    <!-- 探索发现卡片 -->
    <CategoriesCard 
      :categories="categories"
      :tags="tags"
      :selected-category="selectedCategory"
      :selected-tag="selectedTag"
      @category-click="$emit('category-click', $event)"
      @tag-click="$emit('tag-click', $event)"
    />
    
    <!-- 热门文章卡片 -->
    <HotArticlesCard 
      :articles="hotArticles"
      :loading="hotLoading"
    />
    
    <!-- 最新文章卡片 -->
    <LatestArticlesCard 
      :articles="latestArticles"
      :loading="latestLoading"
    />
  </aside>
</template>

<script setup>
import AuthorCard from './AuthorCard.vue'
import CategoriesCard from './CategoriesCard.vue'
import HotArticlesCard from './HotArticlesCard.vue'
import LatestArticlesCard from './LatestArticlesCard.vue'

// Props
const props = defineProps({
  categories: {
    type: Array,
    default: () => []
  },
  tags: {
    type: Array,
    default: () => []
  },
  hotArticles: {
    type: Array,
    default: () => []
  },
  latestArticles: {
    type: Array,
    default: () => []
  },
  hotLoading: {
    type: Boolean,
    default: false
  },
  latestLoading: {
    type: Boolean,
    default: false
  },
  selectedCategory: {
    type: String,
    default: ''
  },
  selectedTag: {
    type: String,
    default: ''
  }
})

// 移除了测试数据，使用真实的API数据或降级数据

// 调试信息（可在生产环境移除）
if (process.env.NODE_ENV === 'development') {
  console.log('DesktopSidebar - Props received:', {
    hotArticles: props.hotArticles,
    hotArticlesLength: props.hotArticles?.length,
    latestArticles: props.latestArticles,
    latestArticlesLength: props.latestArticles?.length,
    hotLoading: props.hotLoading,
    latestLoading: props.latestLoading
  });
}

// Events
defineEmits(['category-click', 'tag-click'])
</script>

<style scoped>
.desktop-sidebar {
  /* 固定宽度，移除高度限制和滚动条 */
  width: 100%;
  position: sticky;
  top: 2rem; /* 与页面顶部保持间距 */
}

/* 样式由父组件动态控制显示隐藏，移除固定断点 */
</style>