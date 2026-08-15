<template>
  <div class="home-view space-y-6">
    <!-- Hero Section -->
    <HomeHero
      v-model:search-input="searchInput"
      :loading="loading"
      :categories="categories"
      :selected-category="selectedCategory"
      @search="applySearch"
      @category-click="clickCategory"
    />

    <!-- 主要内容区域 -->
    <div ref="contentWrapper" class="main-content-wrapper">
      <main class="article-section-container">
        <!-- 文章内容区域包装器 - 确保内容和分页的正确定位 -->
        <div class="article-content-wrapper">
          <!-- 文章列表控制器 -->
          <div class="flex flex-col sm:flex-row sm:items-center mb-10 bg-white rounded-lg p-6 shadow-sm gap-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-4">
              <h2 class="text-xl font-semibold text-gray-800">文章列表</h2>
              <el-segmented
                v-model="listType" :options="[
                  { label: '最新发布', value: 'latest' },
                  { label: '热门推荐', value: 'hot' }
                ]" size="large" @change="onListTypeChange"
              />
              
              <!-- 热门推荐状态提示 -->
              <el-tooltip
                v-if="listType === 'hot'" 
                content="基于文章浏览量和互动数据的智能推荐" 
                placement="top"
              >
                <el-tag type="info" size="small" effect="plain">
                  <el-icon><TrendCharts /></el-icon>
                  智能推荐
                </el-tag>
              </el-tooltip>
            </div>
          </div>

          <!-- 加载状态 -->
          <div v-if="loading && !articles.length" class="space-y-6">
            <div v-for="n in 3" :key="n" class="bg-white rounded-xl overflow-hidden shadow-sm">
              <div class="md:flex">
                <div class="md:w-80 md:flex-shrink-0">
                  <div class="h-48 md:h-56 bg-gray-200 animate-pulse" />
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
            <el-button v-if="searchInput || selectedCategory || selectedTag" type="primary" @click="clearAll">
              清空筛选
            </el-button>
          </el-empty>

          <!-- 文章列表 -->
          <div v-else class="article-grid space-y-8 md:space-y-0 article-list-container">
            <ArticleCard
              v-for="a in articles"
              :key="a.id"
              :article="a"
              @category-click="clickCategory"
              @tag-click="clickTag"
            />
          </div>
        </div>

        <!-- 翻页组件独立容器 - 确保始终在底部且与内容分离 -->
        <HomePagination
          v-if="meta.total > 0"
          :total="meta.total"
          :page="meta.page"
          :page-size="meta.page_size"
          @page-change="onPageChange"
          @size-change="onSizeChange"
        />
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
import { ref, reactive, computed, watch, onMounted, onActivated, inject, Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';
import { TrendCharts } from '@element-plus/icons-vue';
import { usePagedQuery } from '../composables/usePagedQuery';
import { useResponsiveLayout } from '../composables/useResponsiveLayout';
import { ElMessage, ElTooltip } from 'element-plus';
import DesktopSidebar from '../components/sidebar/DesktopSidebar.vue';
import HomeHero from '../components/home/HomeHero.vue';
import ArticleCard from '../components/home/ArticleCard.vue';
import HomePagination from '../components/home/HomePagination.vue';
import { API as UnifiedAPI } from '../api';

// API 接口定义（统一走 @/api 出口）
const API = {
    SearchService: {
        search: (params: Record<string, any>) => UnifiedAPI.search(params)
    },
    ArticlesService: {
        listArticles: (params: Record<string, any>) => UnifiedAPI.getPublicArticles(params),
        getApiV1ArticlesPublicHot: (page: number, page_size: number, window_hours: number) => 
          UnifiedAPI.getHotArticles({ page, page_size, window_hours }),
        approveArticle: (articleId: number) => UnifiedAPI.approveArticle(articleId)
    },
    TaxonomyService: {
        getTaxonomy: () => UnifiedAPI.getPublicTaxonomy(),
        listCategories: () => UnifiedAPI.getRootCategories(),
        listTags: () => UnifiedAPI.getRootTags()
    }
}

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
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

// 分页查询
const { loading, error, data, pageSize, goPage, setPageSize } = usePagedQuery<any>({
  initialPageSize: 10,
  async fetcher(params){
    const { page, page_size } = params;
    const q = route.query.q as string || '';
    const category_id = route.query.category_id as string || '';
    const tag = route.query.tag as string || '';
    
    // 明确标注 resp 的类型以避免 TypeScript 推断为 unknown
    let resp: import('axios').AxiosResponse<any> | any;
    if (q) {
      resp = await API.SearchService.search({ 
        q, page, page_size, 
        category_id: category_id || undefined, 
        tag: tag || undefined 
      });
    } else if (listType.value === 'hot') {
      try {
        // 首先尝试调用热门推荐API，设置较短的超时时间
        console.log("尝试调用热门推荐API"); 
        resp = await Promise.race([
          API.ArticlesService.getApiV1ArticlesPublicHot(page, page_size, 72),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('API timeout')), 5000)
          )
        ]);
        console.log("热门推荐API调用成功:", resp.data.data);
      } catch (hotError) {
        console.warn('热门推荐API调用失败，回退到最新文章:', hotError);
        // 降级方案：使用最新文章但按浏览量排序
        resp = await API.ArticlesService.listArticles({ 
          page, page_size, 
          sort: 'views_desc',  // 按浏览量降序排序
          category_id: category_id || undefined, 
          tag: tag || undefined 
        });
        // 添加提示信息
        if (resp.data?.data?.list) {
          resp.data.data.isHotFallback = true;
        }
        
        // 调试降级响应
        if (process.env.NODE_ENV === 'development') {
          console.log('===== 热门推荐降级响应 =====');
          console.log('降级响应数据:', resp.data.data);
          console.log('文章数量:', resp.data.data?.list?.length);
          console.log('页面大小:', resp.data.data?.page_size);
          console.log('=========================');
        }
      }
    } else {
      console.log("调用最新文章API");
      resp = await API.ArticlesService.listArticles({ 
        page, page_size, 
        category_id: category_id || undefined, 
        tag: tag || undefined 
      });
    }
    
    // 如果是热门推荐降级，显示提示信息
    if (resp.data?.data?.isHotFallback && listType.value === 'hot') {
      ElMessage.info({
        message: '热门推荐暂不可用，已为您显示最受欢迎的文章',
        duration: 3000,
        showClose: true
      });
    }
    
    return resp.data.data;
  }
});

const articles = computed(() => {
  const articleList = data.value?.list || [];
  if (process.env.NODE_ENV === 'development') {
    console.log('当前文章列表长度:', articleList.length);
  }
  return articleList;
});
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
  // 如果点击的是当前已选中的分类，则取消选择
  if (selectedCategory.value === String(id)) {
    selectedCategory.value = ''; // 取消选择
  } else {
    selectedCategory.value = String(id); 
  }
  applyFilters(); 
}

function clearCategory() { 
  selectedCategory.value = ''; 
  applyFilters(); 
}

function clickTag(slug: string) { 
  // 如果点击的是当前已选中的标签，则取消选择
  if (selectedTag.value === slug) {
    selectedTag.value = ''; // 取消选择
  } else {
    selectedTag.value = slug; 
  }
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
  if (process.env.NODE_ENV === 'development') {
    console.log('分页大小变更:', size);
  }
  setPageSize(size);
  router.push({ query: buildQuery({ page: 1 }) });
}

function onListTypeChange(newType: 'latest' | 'hot') {
  listType.value = newType;
  goPage(1); // 重新加载数据
}

// 数据加载
async function loadTaxonomy() {
  console.log('🏷️  开始加载分类和标签...');
  try {
    // 使用统一的taxonomy API
    const taxonomyRes = await Promise.race([
      API.TaxonomyService.getTaxonomy(),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Taxonomy API timeout')), 10000)
      )
    ]) as import('axios').AxiosResponse<any>;
    
    const taxonomyData = taxonomyRes.data.data;
    categories.value = taxonomyData.categories || [];
    tags.value = taxonomyData.tags || [];
    console.log('✅ 分类和标签加载成功，分类:', categories.value.length, '标签:', tags.value.length);
    
    // 更新侧边栏数据
    if (sidebarData) {
      sidebarData.value.categories = categories.value;
      sidebarData.value.tags = tags.value;
    }
  } catch (e) {
    console.error('加载分类标签失败:', e);
    // 降级方案：使用模拟数据
    const mockCategories = [
      { id: 1, name: 'Vue.js', slug: 'vue' },
      { id: 2, name: 'React', slug: 'react' },
      { id: 3, name: 'JavaScript', slug: 'javascript' },
      { id: 4, name: 'TypeScript', slug: 'typescript' },
      { id: 5, name: 'CSS', slug: 'css' },
      { id: 6, name: '前端工程化', slug: 'frontend-engineering' },
      { id: 7, name: '性能优化', slug: 'performance' },
      { id: 8, name: 'Node.js', slug: 'nodejs' }
    ];
    
    const mockTags = [
      { id: 1, slug: 'hooks', name: 'Hooks' },
      { id: 2, slug: 'async', name: 'Async' },
      { id: 3, slug: 'optimization', name: 'Optimization' },
      { id: 4, slug: 'components', name: 'Components' },
      { id: 5, slug: 'state-management', name: 'State Management' },
      { id: 6, slug: 'testing', name: 'Testing' },
      { id: 7, slug: 'webpack', name: 'Webpack' },
      { id: 8, slug: 'babel', name: 'Babel' },
      { id: 9, slug: 'eslint', name: 'ESLint' },
      { id: 10, slug: 'vite', name: 'Vite' },
      { id: 11, slug: 'responsive', name: 'Responsive' },
      { id: 12, slug: 'animations', name: 'Animations' }
    ];
    
    categories.value = mockCategories;
    tags.value = mockTags;
    console.log('📝 设置分类标签降级数据，分类:', mockCategories.length, '标签:', mockTags.length);
    
    // 更新侧边栏数据
    if (sidebarData) {
      sidebarData.value.categories = mockCategories;
      sidebarData.value.tags = mockTags;
    }
    
    // 显示友好提示
    ElMessage.info({
      message: '数据加载中，当前显示演示内容',
      duration: 3000,
      showClose: true
    });
  }
}

async function loadLatest() {
  console.log('📰 开始加载最新文章...');
  sideLoading.value = true;
  try {
    // 添加超时控制 - 增加到10秒给API更多时间响应
    const r = await Promise.race([
      API.ArticlesService.listArticles({ page: 1, page_size: 5 }),
      new Promise<never>((_, reject) => 
        setTimeout(() => reject(new Error('API timeout')), 10000)
      )
    ]) as import('axios').AxiosResponse<any>;
    latest.value = r.data.data?.list || [];
    console.log('✅ 最新文章加载成功，数量:', latest.value.length);
  } catch (e) {
    console.error('❌ 加载最新文章失败:', e);
    // 降级方案：使用模拟数据展示界面
    console.log('⚠️ 最新文章API调用失败，使用降级数据');
    latest.value = [
      {
        id: 1,
        title: '如何优化Vue.js应用的性能',
        slug: 'vue-performance-optimization',
        summary: '通过多种技术手段提升Vue应用响应速度...',
        published_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2小时前
        category: 'Vue.js'
      },
      {
        id: 2,
        title: 'JavaScript异步编程最佳实践',
        slug: 'js-async-best-practices',
        summary: '掌握Promise、async/await的高级用法...',
        published_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(), // 6小时前
        category: 'JavaScript'
      },
      {
        id: 3,
        title: 'CSS Grid布局完全指南',
        slug: 'css-grid-complete-guide',
        summary: '从基础到高级，全面掌握CSS Grid布局...',
        published_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1天前
        category: 'CSS'
      }
    ];
    console.log('📝 设置最新文章降级数据，数量:', latest.value.length);
  } finally { 
    sideLoading.value = false; 
  }
}

async function loadHot() {
  console.log('🔥 开始加载热门文章...');
  hotLoading.value = true;
  try {
    // 添加超时控制 - 增加到10秒给API更多时间响应
    const r = await Promise.race([
      API.ArticlesService.getApiV1ArticlesPublicHot(1, 5, 48),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('API timeout')), 10000)
      )
    ]) as import('axios').AxiosResponse<any>;
    hot.value = r.data.data?.list || [];
    console.log('✅ 热门文章加载成功，数量:', hot.value.length);
    
    // 更新侧边栏数据
    if (sidebarData) {
      sidebarData.value.hotArticles = r.data.data?.list || [];
    }
  } catch (e) {
    console.error('加载热门文章失败:', e);
    // 降级方案：尝试使用最新文章作为热门文章的替代
    try {
      const fallbackResp = await API.ArticlesService.listArticles({ 
        page: 1, 
        page_size: 5, 
        sort: 'published_at:desc'  // 按发布时间降序
      });
      const fallbackArticles = fallbackResp.data.data?.list || [];
      
      // 如果获取到了最新文章，将其作为热门文章的降级数据
      if (fallbackArticles.length > 0) {
        // 为降级数据添加模拟的浏览量和点赞数
        const mockHotArticles = fallbackArticles.map((article: any, index: number) => ({
          ...article,
          views_count: Math.max(article.views_count || 0, 100 - index * 20), // 模拟递减的浏览量
          likes_count: Math.max(article.likes_count || 0, 10 - index * 2), // 模拟递减的点赞数
        }));
        
        hot.value = mockHotArticles;
        
        // 更新侧边栏数据
        if (sidebarData) {
          sidebarData.value.hotArticles = mockHotArticles;
        }
        
        console.log('使用最新文章作为热门文章降级数据');
        return;
      }
    } catch (fallbackError) {
      console.error('降级数据获取也失败:', fallbackError);
    }
    
    // 最终降级：完全没有数据时显示空数组
    console.log('⚠️ 热门文章和降级数据都获取失败，设置为空数组');
    hot.value = [];
    if (sidebarData) {
      sidebarData.value.hotArticles = [];
    }
  } finally { 
    hotLoading.value = false; 
  }
}

// 生命周期
onMounted(async () => {
  console.log('🔄 Home组件mounted，开始加载数据...');
  console.log('📍 当前查询参数:', route.query);
  console.log('📍 当前URL:', window.location.href);
  
  // 检查是否有刷新标记（支持URL参数和路由参数）
  const urlParams = new URLSearchParams(window.location.search);
  const hasRefreshInUrl = urlParams.has('_refresh');
  const hasRefreshInRoute = !!route.query._refresh;
  
  if (hasRefreshInUrl || hasRefreshInRoute) {
    console.log('🔄 Mount时检测到刷新标记，强制重新加载', { 
      urlParam: hasRefreshInUrl, 
      routeParam: hasRefreshInRoute 
    });
    
    // 清空现有数据，强制重新加载
    latest.value = [];
    hot.value = [];
    categories.value = [];
    tags.value = [];
    
    console.log('🧹 已清空侧边栏数据，准备重新加载');
  }
  
  // 如果URL中没有page_size参数，设置默认值
  if (!route.query.page_size && !route.query._refresh) {
    router.replace({ 
      query: { ...route.query, page_size: '10' }
    });
    return;
  }
  
  await Promise.all([
    loadTaxonomy(),
    loadLatest(),
    loadHot()
  ]);
  
  console.log('✅ Home组件数据加载完成');
  
  // 如果有刷新标记，清除它（重用上面声明的urlParams变量）
  if (route.query._refresh || urlParams.has('_refresh')) {
    console.log('🧹 清除刷新标记');
    setTimeout(() => {
      // 清理URL参数
      if (urlParams.has('_refresh')) {
        urlParams.delete('_refresh');
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.history.replaceState({}, '', newUrl);
        console.log('🧹 已清理URL中的刷新参数');
      }
      
      // 清理路由参数
      if (route.query._refresh) {
        router.replace({ 
          query: { ...route.query, _refresh: undefined }
        });
        console.log('🧹 已清理路由中的刷新参数');
      }
    }, 100);
  }
});

// 组件激活时的处理（用于缓存组件）
onActivated(() => {
  console.log('🔄 Home组件被激活 (onActivated)');
  
  // 检查是否需要重新加载侧边栏数据
  const currentPath = route.path;
  console.log('📍 当前路径:', currentPath);
  
  if (currentPath === '/' || currentPath === '/home') {
    // 强制刷新侧边栏数据
    console.log('🔄 组件激活时强制刷新侧边栏数据...');
    
    // 清空并重新加载
    latest.value = [];
    hot.value = [];
    categories.value = [];
    tags.value = [];
    
    Promise.all([
      loadLatest(),
      loadHot(),
      loadTaxonomy()
    ]).then(() => {
      console.log('✅ 组件激活时侧边栏数据重新加载完成');
    });
  }
});

// 监听路由变化
watch(() => route.query, (newQuery, oldQuery) => {
  // 检查是否有刷新标记
  if (newQuery._refresh && !oldQuery._refresh) {
    console.log('🔄 检测到刷新标记，强制重新加载侧边栏数据');
    
    // 清空并重新加载侧边栏数据
    latest.value = [];
    hot.value = [];
    categories.value = [];
    tags.value = [];
    
    Promise.all([
      loadLatest(),
      loadHot(),
      loadTaxonomy()
    ]).then(() => {
      console.log('✅ 刷新标记触发的数据重新加载完成');
    });
  }
  
  goPage(Number(newQuery.page) || 1);
}, { deep: true });

// 监听路由路径变化，当用户返回首页时重新加载侧边栏数据
watch(() => route.path, (newPath, oldPath) => {
  console.log('🔄 路由路径变化检测', { from: oldPath, to: newPath, isHome: newPath === '/' || newPath === '/home' });
  
  if (newPath === '/' || newPath === '/home') {
    console.log('🏠 返回主页，重新加载侧边栏数据', { from: oldPath, to: newPath });
    
    // 如果是从其他页面返回主页，强制重新加载侧边栏数据
    if (oldPath && oldPath !== newPath) {
      console.log('🔄 强制刷新侧边栏数据...');
      // 清空现有数据，强制重新加载
      latest.value = [];
      hot.value = [];
      categories.value = [];
      tags.value = [];
      
      // 重新加载所有侧边栏数据
      Promise.all([
        loadLatest(),
        loadHot(),
        loadTaxonomy()
      ]).then(() => {
        console.log('✅ 侧边栏数据重新加载完成');
      });
    } else {
      // 初次进入主页，只加载缺失的数据
      if (latest.value.length === 0) {
        loadLatest();
      }
      if (hot.value.length === 0) {
        loadHot();
      }
      if (categories.value.length === 0 || tags.value.length === 0) {
        loadTaxonomy();
      }
    }
  }
}, { immediate: false });

// 监听列表类型变化
watch(listType, () => {
  goPage(1);
});

// 监听用户认证状态变化，当登录/退出时刷新侧边栏数据
watch(() => userStore.isAuthenticated, (newAuth, oldAuth) => {
  // 只有当认证状态真正发生变化时才刷新
  if (newAuth !== oldAuth && oldAuth !== undefined) {
    console.log('🔐 用户认证状态变化:', { from: oldAuth, to: newAuth });
    
    // 清空并重新加载侧边栏数据
    console.log('🔄 认证状态变化，强制刷新侧边栏数据');
    latest.value = [];
    hot.value = [];
    categories.value = [];
    tags.value = [];
    
    Promise.all([
      loadLatest(),
      loadHot(),
      loadTaxonomy()
    ]).then(() => {
      console.log('✅ 认证状态变化触发的数据重新加载完成');
    });
  }
}, { immediate: false });
</script>

<style scoped>
.article-list-container { margin-top: 2.5rem; }

/* 新的 Flexbox 布局样式 */
.main-content-wrapper {
  display: flex;
  gap: 30px;
  padding: 0; /* 移除内边距，让内容更贴近页面边缘 */
  width: 100%; /* 确保容器占满可用宽度 */
  margin-top: 2rem; /* 添加顶部间距，与搜索栏分离 */
  box-sizing: border-box; /* 包含padding在宽度计算内 */
}

.article-section-container {
  flex: 1;
  min-width: 0; /* 允许压缩，重要！ */
  min-height: 80vh; /* 确保有足够高度让翻页组件靠近底部 */
  display: flex;
  flex-direction: column;
}

.article-content-wrapper {
  flex: 1;
  min-height: 0; /* 允许内容区域自适应高度 */
}

.sidebar-section {
  width: 320px;
  flex-shrink: 0;
}

/* 文章列表切换按钮样式优化 */
.el-segmented {
  height: 48px !important; /* 增加按钮组高度 */
}

.el-segmented :deep(.el-segmented__item) {
  height: 44px !important; /* 增加单个按钮高度 */
  line-height: 44px !important; /* 调整行高确保文字居中 */
  padding: 0 24px !important; /* 增加水平内边距 */
  font-size: 0.95rem !important; /* 稍微增加字体大小 */
  font-weight: 500 !important; /* 增加字体重量 */
}

.el-segmented :deep(.el-segmented__item-selected) {
  height: 44px !important;
  line-height: 44px !important;
}

/* 响应式网格布局 */
.article-grid {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  margin-top: 2.5rem !important; /* 强制应用顶部间距，与控制器分离 */
}

@media (min-width: 768px) {
  .article-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 2rem;
    width: 100%;
  }
}

@media (max-width: 768px) {
  /* 移动端文章列表控制器 */
  .flex.flex-col.sm\:flex-row {
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .bg-white.rounded-xl.shadow-sm {
    padding: 1rem;
  }
}
</style>