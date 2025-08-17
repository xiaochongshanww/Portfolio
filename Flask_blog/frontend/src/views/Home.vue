<template>
  <div class="home-view space-y-6">
    <!-- Hero Section -->
    <section class="hero-section bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-12 px-6 rounded-xl relative overflow-hidden">
      <!-- 背景装饰 -->
      <div class="absolute inset-0 opacity-10">
        <div class="absolute top-10 left-10 w-20 h-20 bg-blue-400 rounded-full blur-xl"></div>
        <div class="absolute top-20 right-20 w-16 h-16 bg-purple-400 rounded-full blur-lg"></div>
        <div class="absolute bottom-10 left-1/3 w-12 h-12 bg-indigo-400 rounded-full blur-lg"></div>
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
              @keyup.enter="applySearch"
              class="search-input"
            >
              <template #prefix>
                <el-icon class="text-gray-400"><Search /></el-icon>
              </template>
              <template #append>
                <el-button :loading="loading" @click="applySearch" type="primary" size="large">
                  搜索
                </el-button>
              </template>
            </el-input>
          </div>
        </div>

        <!-- 快速筛选标签 -->
        <div class="flex flex-wrap justify-center gap-2 mb-4">
          <el-tag 
            v-for="c in categories.slice(0, 6)" 
            :key="c.id" 
            :type="selectedCategory === String(c.id) ? 'primary' : 'info'" 
            class="cursor-pointer hover:scale-105 transition-transform"
            @click="clickCategory(c.id)"
            size="large"
          >
            {{ c.name }}
          </el-tag>
        </div>
      </div>
    </section>

    <!-- 主要内容区域 -->
    <div ref="contentWrapper" class="main-content-wrapper">
      <main class="article-section">
        <!-- 文章列表控制器 -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 bg-white rounded-lg p-4 shadow-sm gap-4">
          <div class="flex flex-col sm:flex-row sm:items-center gap-4">
            <h2 class="text-xl font-semibold text-gray-800">文章列表</h2>
            <el-segmented v-model="listType" :options="[
              { label: '最新发布', value: 'latest' },
              { label: '热门推荐', value: 'hot' }
            ]" @change="onListTypeChange" />
          </div>
          <div class="flex items-center justify-between sm:justify-end gap-2 text-sm text-gray-500">
            <span>共 {{ meta.total || 0 }} 篇文章</span>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading && !articles.length" class="space-y-6">
          <div v-for="n in 3" :key="n" class="bg-white rounded-xl overflow-hidden shadow-sm">
            <div class="md:flex">
              <div class="md:w-80 md:flex-shrink-0">
                <div class="h-48 md:h-56 bg-gray-200 animate-pulse"></div>
              </div>
              <div class="p-6 flex-1">
                <el-skeleton :rows="4" animated />
              </div>
            </div>
          </div>
        </div>

        <!-- 错误状态 -->
        <el-alert v-if="error" :title="error" type="error" show-icon class="mt-4" />
        
        <!-- 空状态 -->
        <el-empty v-if="!loading && !error && !articles.length" class="mt-8 py-12">
          <template #description>
            <p class="text-gray-500">{{ searchInput || selectedCategory || selectedTag ? '没有找到相关文章' : '暂无文章' }}</p>
          </template>
          <el-button type="primary" @click="clearAll" v-if="searchInput || selectedCategory || selectedTag">
            清空筛选
          </el-button>
        </el-empty>

        <!-- 文章列表 -->
        <div v-else class="space-y-6">
          <article 
            v-for="a in articles" 
            :key="a.id" 
            class="article-card bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 group"
          >
            <div class="md:flex">
              <!-- 封面图片 -->
              <div class="md:w-80 md:flex-shrink-0 relative overflow-hidden">
                <RouterLink :to="'/article/' + a.slug">
                  <div class="aspect-video md:aspect-[4/3] bg-gray-100 relative">
                    <img 
                      v-if="a.featured_image" 
                      :src="a.featured_image" 
                      :alt="a.title" 
                      class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                    <div v-else class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 text-gray-400">
                      <el-icon size="48"><Picture /></el-icon>
                    </div>
                  </div>
                </RouterLink>
                <!-- 分类标签 -->
                <div v-if="a.category" class="absolute top-3 left-3">
                  <el-tag :type="getCategoryColor(a.category)" size="small" class="shadow-sm">
                    {{ a.category }}
                  </el-tag>
                </div>
              </div>

              <!-- 内容区域 -->
              <div class="p-6 flex-1 flex flex-col">
                <div class="flex-1">
                  <!-- 标题 -->
                  <RouterLink 
                    :to="'/article/' + a.slug"
                    class="block group-hover:text-blue-600 transition-colors duration-200"
                  >
                    <h3 class="text-xl font-bold text-gray-900 leading-tight mb-3 line-clamp-2">
                      {{ a.title }}
                    </h3>
                  </RouterLink>

                  <!-- 摘要 -->
                  <p class="text-gray-600 leading-relaxed mb-4 line-clamp-3">
                    {{ a.summary || '暂无摘要...' }}
                  </p>

                  <!-- 标签 -->
                  <div v-if="Array.isArray(a.tags) && a.tags.length" class="flex items-center gap-2 flex-wrap mb-4">
                    <el-tag 
                      v-for="t in a.tags.slice(0, 3)" 
                      :key="t" 
                      size="small" 
                      class="cursor-pointer hover:bg-gray-200 transition-colors"
                      @click="clickTag(t)"
                    >
                      #{{ t }}
                    </el-tag>
                    <span v-if="a.tags.length > 3" class="text-xs text-gray-400">+{{ a.tags.length - 3 }}</span>
                  </div>
                </div>

                <!-- 底部信息 -->
                <div class="flex items-center justify-between pt-4 border-t border-gray-100">
                  <!-- 作者信息 -->
                  <div class="flex items-center gap-3">
                    <template v-if="a.author && a.author.id">
                      <RouterLink :to="`/author/${a.author.id}`" class="flex items-center gap-2 hover:text-blue-600 transition-colors">
                        <div class="w-8 h-8 rounded-full overflow-hidden bg-gradient-to-br from-gray-200 to-gray-300 flex-shrink-0">
                          <img 
                            v-if="a.author.avatar"
                            :src="a.author.avatar" 
                            :alt="a.author.name" 
                            class="w-full h-full object-cover"
                            @error="(e: Event) => handleAuthorAvatarError(e, a.author)"
                          />
                          <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-400 to-purple-500">
                            <el-icon size="12" class="text-white"><User /></el-icon>
                          </div>
                        </div>
                        <div class="text-sm">
                          <div class="font-medium text-gray-900">{{ a.author.name || '匿名作者' }}</div>
                          <div class="text-gray-500">{{ formatDate(a.published_at) }}</div>
                        </div>
                      </RouterLink>
                    </template>
                    <template v-else>
                      <div class="flex items-center gap-2">
                        <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                          <el-icon size="16" class="text-gray-400"><User /></el-icon>
                        </div>
                        <div class="text-sm">
                          <div class="font-medium text-gray-900">匿名作者</div>
                          <div class="text-gray-500">{{ formatDate(a.published_at) }}</div>
                        </div>
                      </div>
                    </template>
                  </div>

                  <!-- 互动按钮 -->
                  <div class="flex items-center gap-4 text-gray-500">
                    <span v-if="a.views_count != null" class="flex items-center gap-1 text-sm">
                      <el-icon><View /></el-icon>
                      {{ formatNumber(a.views_count) }}
                    </span>
                    <button 
                      @click="toggleLike(a)"
                      :class="[
                        'flex items-center gap-1 text-sm transition-colors hover:text-red-500',
                        a.is_liked ? 'text-red-500' : ''
                      ]"
                      :disabled="likingIds.includes(a.id)"
                    >
                      <el-icon>
                        <component :is="a.is_liked ? 'StarFilled' : 'Star'" />
                      </el-icon>
                      {{ formatNumber(a.likes_count || 0) }}
                    </button>
                    <button 
                      @click="toggleBookmark(a)"
                      :class="[
                        'flex items-center gap-1 text-sm transition-colors hover:text-blue-500',
                        a.is_bookmarked ? 'text-blue-500' : ''
                      ]"
                      :disabled="bookmarkingIds.includes(a.id)"
                    >
                      <el-icon>
                        <component :is="a.is_bookmarked ? 'FolderChecked' : 'FolderAdd'" />
                      </el-icon>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div v-if="meta.total > 0" class="mt-6 flex justify-center">
          <el-pagination
            background
            layout="prev, pager, next, sizes, total"
            :page-sizes="[10,20,50]"
            :total="meta.total || 0"
            :current-page="meta.page"
            :page-size="meta.page_size"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </main>
      
      <!-- 桌面端侧边栏 -->
      <aside v-if="canShowSidebar" class="sidebar-section">
        <DesktopSidebar 
          :categories="categories"
          :tags="tags"
          :hot-articles="hot"
          :latest-articles="latest"
          :hot-loading="hotLoading"
          :latest-loading="sideLoading"
          :selected-category="selectedCategory"
          :selected-tag="selectedTag"
          @category-click="clickCategory"
          @tag-click="clickTag"
        />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, inject, Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { 
  Star, StarFilled, FolderAdd, FolderChecked, Search, Picture, User, View
} from '@element-plus/icons-vue';
import { usePagedQuery } from '../composables/usePagedQuery';
import { useResponsiveLayout } from '../composables/useResponsiveLayout';
import apiClient from '../apiClient';
import { ElMessage } from 'element-plus';
import DesktopSidebar from '../components/sidebar/DesktopSidebar.vue';

// API 接口定义
const API = {
    SearchService: {
        search: (params: Record<string, any>) => apiClient.get('/search/', { params })
    },
    ArticlesService: {
        listArticles: (params: Record<string, any>) => apiClient.get('/articles/public/', { params }),
        getApiV1ArticlesPublicHot: (page: number, page_size: number, window_hours: number) => 
          apiClient.get('/articles/public/hot', { params: { page, page_size, window_hours }}),
        toggleLike: (articleId: number) => apiClient.post(`/articles/${articleId}/like`),
        toggleBookmark: (articleId: number) => apiClient.post(`/articles/${articleId}/bookmark`)
    },
    TaxonomyService: {
        listCategories: () => apiClient.get('/taxonomy/categories/'),
        listTags: () => apiClient.get('/taxonomy/tags/')
    }
}

const route = useRoute();
const router = useRouter();
const sidebarData = inject<Ref<Record<string, any>> | undefined>('sidebarData');

// 容器元素引用
const contentWrapper = ref(null);

// 响应式布局 - 传入容器元素用于动态计算
const { isMobile, canShowSidebar, windowWidth, containerWidth, requiredWidth, debugInfo } = useResponsiveLayout(contentWrapper);

// 响应式数据
const searchInput = ref<string>((route.query.q as string) || '');
const selectedCategory = ref<string | '' >((route.query.category_id as string) || '');
const selectedTag = ref<string | '' >((route.query.tag as string) || '');
const listType = ref<'latest' | 'hot'>('latest');
const categories = ref<any[]>([]);
const tags = ref<any[]>([]);
const latest = ref<any[]>([]);
const sideLoading = ref(false);
const hot = ref<any[]>([]);
const hotLoading = ref(false);
const likingIds = ref<number[]>([]);
const bookmarkingIds = ref<number[]>([]);

// 分页查询
const { loading, error, data, pageSize, goPage, setPageSize } = usePagedQuery<any>({
  initialPageSize: 20,
  async fetcher(params){
    const { page, page_size } = params;
    const q = route.query.q as string || '';
    const category_id = route.query.category_id as string || '';
    const tag = route.query.tag as string || '';
    
    let resp;
    if (q) {
      resp = await API.SearchService.search({ 
        q, page, page_size, 
        category_id: category_id || undefined, 
        tag: tag || undefined 
      });
    } else if (listType.value === 'hot') {
      resp = await API.ArticlesService.getApiV1ArticlesPublicHot(page, page_size, 72);
    } else {
      resp = await API.ArticlesService.listArticles({ 
        page, page_size, 
        category_id: category_id || undefined, 
        tag: tag || undefined 
      });
    }
    return resp.data.data;
  }
});

const articles = computed(() => data.value?.list || []);
const meta = computed(() => ({
  total: data.value?.total ?? null,
  page: data.value?.page ?? 1,
  page_size: data.value?.page_size ?? pageSize.value,
}));

// 工具函数
function buildQuery(newQuery: Record<string, any>) {
  const q: any = { ...route.query, ...newQuery };
  Object.keys(q).forEach(k => { if (q[k] === '' || q[k] == null) delete q[k]; });
  return q;
}

function formatDate(s?: string) { 
  if (!s) return ''; 
  try { 
    return new Date(s).toLocaleDateString('zh-CN');
  } catch { 
    return ''; 
  } 
}

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return String(num);
}

function getCategoryColor(category: string): string {
  const colors = ['', 'success', 'warning', 'danger', 'info'];
  const hash = category.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

function handleImageError(e: Event) {
  const img = e.target as HTMLImageElement;
  img.src = '/assets/default-avatar.png';
}

function handleAuthorAvatarError(e: Event, author: any) {
  const img = e.target as HTMLImageElement;
  // 隐藏图片，让父容器的默认样式显示
  img.style.display = 'none';
  // 清空头像URL，让模板显示默认图标
  author.avatar = null;
}

// 事件处理
function applySearch() { 
  router.push({ query: buildQuery({ q: searchInput.value, page: 1 }) }); 
}

function applyFilters() {
  router.push({ 
    query: buildQuery({ 
      page: 1, 
      category_id: selectedCategory.value || undefined, 
      tag: selectedTag.value || undefined 
    }) 
  });
}

function clickCategory(id: any) { 
  selectedCategory.value = String(id); 
  applyFilters(); 
}

function clearCategory() { 
  selectedCategory.value = ''; 
  applyFilters(); 
}

function clickTag(slug: string) { 
  selectedTag.value = slug; 
  applyFilters(); 
}

function clearAll() {
  searchInput.value = ''; 
  selectedCategory.value = ''; 
  selectedTag.value = '';
  router.push({ query: {} });
}

function onPageChange(p: number) {
  router.push({ query: buildQuery({ page: p }) });
}

function onSizeChange(size: number) {
  setPageSize(size);
  router.push({ query: buildQuery({ page: 1 }) });
}

function onListTypeChange(newType: 'latest' | 'hot') {
  listType.value = newType;
  goPage(1); // 重新加载数据
}

// 点赞功能
async function toggleLike(article: any) {
  if (likingIds.value.includes(article.id)) return;
  
  likingIds.value.push(article.id);
  const wasLiked = article.is_liked;
  const originalCount = article.likes_count || 0;
  
  // 乐观更新
  article.is_liked = !wasLiked;
  article.likes_count = wasLiked ? originalCount - 1 : originalCount + 1;
  
  try {
    await API.ArticlesService.toggleLike(article.id);
    ElMessage.success(article.is_liked ? '点赞成功' : '取消点赞');
  } catch (error) {
    // 回滚
    article.is_liked = wasLiked;
    article.likes_count = originalCount;
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    likingIds.value = likingIds.value.filter(id => id !== article.id);
  }
}

// 收藏功能
async function toggleBookmark(article: any) {
  if (bookmarkingIds.value.includes(article.id)) return;
  
  bookmarkingIds.value.push(article.id);
  const wasBookmarked = article.is_bookmarked;
  
  // 乐观更新
  article.is_bookmarked = !wasBookmarked;
  
  try {
    await API.ArticlesService.toggleBookmark(article.id);
    ElMessage.success(article.is_bookmarked ? '收藏成功' : '取消收藏');
  } catch (error) {
    // 回滚
    article.is_bookmarked = wasBookmarked;
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    bookmarkingIds.value = bookmarkingIds.value.filter(id => id !== article.id);
  }
}

// 数据加载
async function loadTaxonomy() {
  try {
    const [cRes, tRes] = await Promise.all([
      API.TaxonomyService.listCategories(),
      API.TaxonomyService.listTags()
    ]);
    categories.value = cRes.data.data;
    tags.value = tRes.data.data;
    
    // 更新侧边栏数据
    if (sidebarData) {
      sidebarData.value.categories = cRes.data.data;
      sidebarData.value.tags = tRes.data.data;
    }
  } catch (e) {
    console.error('加载分类标签失败:', e);
  }
}

async function loadLatest() {
  sideLoading.value = true;
  try {
    const r = await API.ArticlesService.listArticles({ page: 1, page_size: 5 });
    latest.value = r.data.data?.list || [];
  } catch (e) {
    console.error('加载最新文章失败:', e);
  } finally { 
    sideLoading.value = false; 
  }
}

async function loadHot() {
  hotLoading.value = true;
  try {
    const r = await API.ArticlesService.getApiV1ArticlesPublicHot(1, 5, 48);
    hot.value = r.data.data?.list || [];
    
    // 更新侧边栏数据
    if (sidebarData) {
      sidebarData.value.hotArticles = r.data.data?.list || [];
    }
  } catch (e) {
    console.error('加载热门文章失败:', e);
  } finally { 
    hotLoading.value = false; 
  }
}

// 生命周期
onMounted(() => {
  loadTaxonomy();
  loadLatest();
  loadHot();
});

// 监听路由变化
watch(() => route.query, () => {
  goPage(Number(route.query.page) || 1);
}, { deep: true });

// 监听列表类型变化
watch(listType, () => {
  goPage(1);
});
</script>

<style scoped>
/* 新的 Flexbox 布局样式 */
.main-content-wrapper {
  display: flex;
  gap: 30px;
  padding: 0; /* 移除内边距，让内容更贴近页面边缘 */
  width: 100%; /* 确保容器占满可用宽度 */
  margin-top: 2rem; /* 添加顶部间距，与搜索栏分离 */
  box-sizing: border-box; /* 包含padding在宽度计算内 */
}

.article-section {
  flex: 1;
  min-width: 0; /* 允许压缩，重要！ */
}

.sidebar-section {
  width: 320px;
  flex-shrink: 0;
}

/* 布局样式由JS动态控制，移除固定断点媒体查询 */

.search-input :deep(.el-input__inner) {
  border-radius: 12px;
  padding: 12px 16px;
}

.article-card:hover {
  transform: translateY(-2px);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 头像容错样式 */
.avatar-fallback {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .hero-section {
    padding: 2rem 1rem;
    margin: 0 0 2rem 0;
  }
  
  .article-card .md\:flex {
    flex-direction: column;
  }
  
  .article-card .md\:w-80 {
    width: 100%;
  }
  
  
  /* 移动端文章列表控制器 */
  .flex.flex-col.sm\:flex-row {
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .hero-section {
    padding: 1.5rem 0.5rem;
  }
  
  .bg-white.rounded-xl.shadow-sm {
    padding: 1rem;
  }
}

@media (max-width: 1024px) {
  /* 调整容器间距 */
  .el-row {
    --el-row-gutter: 16px;
  }
}
</style>