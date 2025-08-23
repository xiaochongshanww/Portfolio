<template>
  <div class="home-view space-y-6">
    <!-- Hero Section -->
    <section class="hero-section bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-12 px-6 rounded-xl relative overflow-hidden mb-6">
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
        <div class="flex flex-wrap justify-center gap-3 mb-6 quick-filter-container">
          <button
            v-for="c in categories.slice(0, 6)" 
            :key="c.id" 
            @click="clickCategory(c.id)"
            :class="[
              'modern-category-btn',
              selectedCategory === String(c.id) ? 'modern-category-btn-active' : 'modern-category-btn-default'
            ]"
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

    <!-- 主要内容区域 -->
    <div ref="contentWrapper" class="main-content-wrapper">
      <main class="article-section-container">
        <!-- 文章内容区域包装器 - 确保内容和分页的正确定位 -->
        <div class="article-content-wrapper">
          <!-- 文章列表控制器 -->
          <div class="flex flex-col sm:flex-row sm:items-center mb-10 bg-white rounded-lg p-6 shadow-sm gap-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-4">
              <h2 class="text-xl font-semibold text-gray-800">文章列表</h2>
              <el-segmented v-model="listType" :options="[
                { label: '最新发布', value: 'latest' },
                { label: '热门推荐', value: 'hot' }
              ]" @change="onListTypeChange" size="large" />
              
              <!-- 热门推荐状态提示 -->
              <el-tooltip v-if="listType === 'hot'" 
                content="基于文章浏览量和互动数据的智能推荐" 
                placement="top">
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
          <div v-else class="article-grid space-y-8 md:space-y-0" style="margin-top: 2.5rem;">
            <article 
              v-for="a in articles" 
              :key="a.id" 
              class="article-card bg-slate-50 rounded-3xl shadow-sm hover:shadow-xl transition-all duration-300 group"
              style="background-color: rgb(248 250 252); padding: 24px;"
            >
              <!-- 封面图片（顶部） - 优化的嵌入样式 -->
              <div class="cover-image-container">
                <RouterLink :to="'/article/' + a.slug">
                  <div class="aspect-[16/9] bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 relative cover-image-wrapper">
                    <CoverImage 
                      :src="a.featured_image || getDefaultCoverImage(a)" 
                      :alt="a.title" 
                      container-class="absolute inset-0 overflow-hidden"
                      image-class="w-full h-full object-cover group-hover:scale-105 transition-all duration-500"
                      style="border-radius: 24px;"
                    />
                    <!-- 渐变遮罩 -->
                    <div class="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent" style="border-radius: 24px;"></div>
                  </div>
                </RouterLink>
              </div>

              <!-- 主要内容区域 -->
              <div>
                  <!-- 文章标题 -->
                  <RouterLink 
                    :to="'/article/' + a.slug"
                    class="block group-hover:text-blue-600 transition-colors duration-200 text-center"
                  >
                    <h3 class="text-xl font-bold text-gray-900 leading-tight mb-4 line-clamp-2 hover:text-blue-600 transition-colors">
                      {{ a.title }}
                    </h3>
                  </RouterLink>

                  <!-- 文章元信息 -->
                  <div class="post-meta text-sm text-gray-500 mb-4 text-center">
                    <!-- 第一行：基础信息 -->
                    <div class="flex items-center flex-wrap mb-1 justify-center">
                      <!-- 发布时间 -->
                      <div class="post-meta-item">
                        <i class="fa fa-clock-o" aria-hidden="true"></i>
                        {{ formatDate(a.published_at) }}
                      </div>
                      
                      <div class="post-meta-divider">|</div>
                      
                      <!-- 浏览次数 -->
                      <div v-if="a.views_count != null" class="post-meta-item">
                        <i class="fa fa-eye" aria-hidden="true"></i>
                        {{ formatNumber(a.views_count) }}
                      </div>
                      
                      <div v-if="a.views_count != null" class="post-meta-divider">|</div>
                      
                      <!-- 评论数 -->
                      <div class="post-meta-item">
                        <i class="fa fa-comments-o" aria-hidden="true"></i>
                        {{ a.comments_count || 0 }}
                      </div>
                      
                      <div class="post-meta-divider">|</div>
                      
                      <!-- 文章分类 -->
                      <div v-if="a.category" class="post-meta-item">
                        <i class="fa fa-bookmark-o" aria-hidden="true"></i>
                        <span class="text-blue-600 hover:text-blue-800 transition-colors cursor-pointer" @click="clickCategory(a.category_id)">
                          {{ a.category }}
                        </span>
                      </div>
                      
                      <div v-if="a.category" class="post-meta-divider">|</div>
                      
                      <!-- 最后编辑时间 -->
                      <div v-if="a.updated_at && a.updated_at !== a.published_at" class="post-meta-item">
                        <i class="fa fa-clock-o" aria-hidden="true"></i>
                        {{ formatDate(a.updated_at) }}
                      </div>
                      
                      <div v-if="a.updated_at && a.updated_at !== a.published_at" class="post-meta-divider">|</div>
                      
                      <!-- 文章作者 -->
                      <div class="post-meta-item">
                        <i class="fa fa-user-circle-o" aria-hidden="true"></i>
                        {{ a.author?.name || '匿名作者' }}
                      </div>
                    </div>
                    
                    <!-- 第二行：字数和阅读时间 -->
                    <div class="flex items-center justify-center">
                      <!-- 字数统计 -->
                      <div class="post-meta-item">
                        <i class="fa fa-file-word-o" aria-hidden="true"></i>
                        {{ calculateWordCount(a.content_md || a.summary || '') }} 字
                      </div>
                      
                      <div class="post-meta-divider">|</div>
                      
                      <!-- 预计阅读时间 -->
                      <div class="post-meta-item">
                        <i class="fa fa-hourglass-end" aria-hidden="true"></i>
                        {{ calculateReadTime(a.content_md || a.summary || '') }} 分钟
                      </div>
                    </div>
                  </div>

                  <!-- 文章摘要 -->
                  <p class="text-gray-600 leading-relaxed mb-4 line-clamp-3">
                    {{ getArticleSummary(a) }}
                  </p>

                  <!-- 底部操作区域 -->
                  <div class="flex flex-col gap-4">
                    <!-- 标签区域 -->
                    <div v-if="Array.isArray(a.tags) && a.tags.length" class="flex items-center gap-2 flex-wrap justify-center">
                      <el-tag 
                        v-for="t in a.tags.slice(0, 3)" 
                        :key="t" 
                        size="small" 
                        type="info"
                        class="cursor-pointer hover:bg-gray-200 transition-colors"
                        @click="clickTag(t)"
                      >
                        #{{ t }}
                      </el-tag>
                      <span v-if="a.tags.length > 3" class="text-xs text-gray-400">+{{ a.tags.length - 3 }}</span>
                    </div>
                    
                    <!-- 互动按钮 - 移除分割线和边距 -->
                    <div class="interaction-buttons-container">
                      <!-- 点赞按钮 -->
                      <button 
                        @click="toggleLike(a)"
                        :class="[
                          'interaction-btn',
                          a.is_liked ? 'liked' : ''
                        ]"
                        :disabled="likingIds.includes(a.id)"
                        :title="a.is_liked ? '取消点赞' : '点赞'"
                      >
                        <i :class="a.is_liked ? 'fa fa-heart' : 'fa fa-heart-o'" aria-hidden="true"></i>
                        <span>{{ formatNumber(a.likes_count || 0) }}</span>
                      </button>
                      
                      <!-- 收藏按钮 -->
                      <button 
                        @click="toggleBookmark(a)"
                        :class="[
                          'interaction-btn',
                          a.is_bookmarked ? 'bookmarked' : ''
                        ]"
                        :disabled="bookmarkingIds.includes(a.id)"
                        :title="a.is_bookmarked ? '取消收藏' : '收藏文章'"
                      >
                        <i :class="a.is_bookmarked ? 'fa fa-bookmark' : 'fa fa-bookmark-o'" aria-hidden="true"></i>
                        <span>收藏</span>
                      </button>
                    </div>
                  </div>
              </div>
            </article>
          </div>
        </div>

        <!-- 翻页组件独立容器 - 确保始终在底部且与内容分离 -->
        <div v-if="meta.total > 0" class="pagination-container">
          <el-pagination
            background
            layout="prev, pager, next, sizes, total"
            :page-sizes="[10,20,50]"
            :default-page-size="10"
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
          :hotArticles="hot"
          :latestArticles="latest"
          :hotLoading="hotLoading"
          :latestLoading="sideLoading"
          :selectedCategory="selectedCategory"
          :selectedTag="selectedTag"
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
import { 
  Star, StarFilled, FolderAdd, FolderChecked, Search, Picture, User, View,
  Bookmark, BookmarkFilled, Clock, ChatLineRound, Edit, Document, Timer, TrendCharts, More, Close
} from '@element-plus/icons-vue';
import { usePagedQuery } from '../composables/usePagedQuery';
import { useResponsiveLayout } from '../composables/useResponsiveLayout';
import apiClient from '../apiClient';
import { ElMessage, ElTooltip } from 'element-plus';
import DesktopSidebar from '../components/sidebar/DesktopSidebar.vue';
import CoverImage from '../components/CoverImage.vue';

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
        toggleBookmark: (articleId: number) => apiClient.post(`/articles/${articleId}/bookmark`),
        approveArticle: (articleId: number) => apiClient.post(`/articles/${articleId}/approve`)
    },
    TaxonomyService: {
        getTaxonomy: () => apiClient.get('/taxonomy', { baseURL: '/public/v1' }),
        listCategories: () => apiClient.get('/categories/'),
        listTags: () => apiClient.get('/tags/')
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
const likingIds = ref<number[]>([]);
const bookmarkingIds = ref<number[]>([]);

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

function formatDate(s?: string) { 
  if (!s) return ''; 
  try {
    // 修复时区问题：强制将后端时间作为UTC时间处理
    let dateString = s;
    // 如果时间字符串没有时区标识，添加Z表示UTC
    if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
      dateString += 'Z';
    }
    
    const date = new Date(dateString);
    const now = new Date();
    
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    // 相对时间显示
    if (diffMinutes < 1) return '刚刚';
    if (diffMinutes < 60) return `${diffMinutes}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}个月前`;
    
    // 超过一年显示具体日期
    return date.toLocaleDateString('zh-CN');
  } catch (error) { 
    console.warn('formatDate error:', error, 'input:', s);
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

// 计算文章字数
function calculateWordCount(content: string): number {
  if (!content) return 0;
  // 移除 Markdown 标记和 HTML 标签，然后计算字数
  const plainText = content
    .replace(/[#*_`~\[\]()]/g, '') // 移除常见 Markdown 标记
    .replace(/<[^>]*>/g, '') // 移除 HTML 标签
    .replace(/\s+/g, ' ') // 合并多个空白字符
    .trim();
  
  // 中文字符按1个字计算，英文按单词计算
  const chineseChars = (plainText.match(/[\u4e00-\u9fa5]/g) || []).length;
  const englishWords = (plainText.replace(/[\u4e00-\u9fa5]/g, '').match(/\b\w+\b/g) || []).length;
  
  return chineseChars + englishWords;
}

// 计算预计阅读时间（分钟）
function calculateReadTime(content: string): number {
  const wordCount = calculateWordCount(content);
  // 假设平均阅读速度：中文 300 字/分钟，英文 250 词/分钟
  const readTime = Math.max(1, Math.ceil(wordCount / 275));
  return readTime;
}

// 获取默认封面图片
function getDefaultCoverImage(article: any): string {
  // 根据文章分类生成不同的默认封面 (16:9 比例)
  const categoryImages: Record<string, string> = {
    'Python': 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=640&h=360&fit=crop&crop=center',
    '前端': 'https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=640&h=360&fit=crop&crop=center',
    '计算机网络': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=640&h=360&fit=crop&crop=center',
    '其他': 'https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=640&h=360&fit=crop&crop=center'
  };
  
  // 如果有分类且在映射中，返回对应图片
  if (article.category && categoryImages[article.category]) {
    return categoryImages[article.category];
  }
  
  // 根据文章ID生成不同主题的高质量封面图片
  const themeImages = [
    'https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=640&h=360&fit=crop&crop=center', // 现代办公
    'https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=640&h=360&fit=crop&crop=center', // 创意设计
    'https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=640&h=360&fit=crop&crop=center', // 技术创新
    'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=640&h=360&fit=crop&crop=center', // 团队协作
    'https://images.unsplash.com/photo-1551434678-e076c223a692?w=640&h=360&fit=crop&crop=center'  // 数据分析
  ];
  
  const index = (article.id || 0) % themeImages.length;
  return themeImages[index];
}

// 获取文章摘要
function getArticleSummary(article: any): string {
  // 优先使用填写的摘要
  if (article.summary && article.summary.trim()) {
    return article.summary;
  }
  
  // 其次使用后端提供的内容摘录
  if (article.content_excerpt && article.content_excerpt.trim()) {
    const plainText = article.content_excerpt
      .replace(/[#*_`~\[\]()]/g, '') // 移除 Markdown 标记
      .replace(/<[^>]*>/g, '') // 移除 HTML 标签
      .replace(/\s+/g, ' ') // 合并空白
      .trim();
    
    if (plainText.length > 150) {
      return plainText.substring(0, 150) + '...';
    }
    return plainText || '暂无摘要...';
  }
  
  // 最后使用完整content_md（如果有的话）
  if (article.content_md) {
    const plainText = article.content_md
      .replace(/[#*_`~\[\]()]/g, '') // 移除 Markdown 标记
      .replace(/<[^>]*>/g, '') // 移除 HTML 标签
      .replace(/\s+/g, ' ') // 合并空白
      .trim();
    
    if (plainText.length > 150) {
      return plainText.substring(0, 150) + '...';
    }
    return plainText;
  }
  
  return '暂无摘要...';
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
  console.log('🏷️  开始加载分类和标签...');
  try {
    // 使用统一的taxonomy API
    const taxonomyRes = await Promise.race([
      API.TaxonomyService.getTaxonomy(),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Taxonomy API timeout')), 10000)
      )
    ]);
    
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
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('API timeout')), 10000)
      )
    ]);
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
    ]);
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
        const mockHotArticles = fallbackArticles.map((article, index) => ({
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

/* 翻页组件独立容器 - 确保固定在底部并与内容分离 */
.pagination-container {
  margin-top: 4rem; /* 与内容区域保持固定间距 */
  margin-bottom: 2rem;
  padding-top: 2rem;
  padding-bottom: 1rem;
  display: flex;
  justify-content: center;
  border-top: 1px solid #f1f5f9; /* 添加分隔线 */
  background: rgba(255, 255, 255, 0.8); /* 轻微背景色区分 */
  backdrop-filter: blur(8px); /* 毛玻璃效果 */
  border-radius: 16px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05); /* 轻微阴影 */
}

.sidebar-section {
  width: 320px;
  flex-shrink: 0;
}

/* 快速筛选标签间距 */
.quick-filter-tags {
  gap: 8px;
  row-gap: 12px; /* 增加上下间距 */
}

.quick-filter-tag {
  transition: all 0.2s ease;
}

.quick-filter-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 布局样式由JS动态控制，移除固定断点媒体查询 */

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

/* 修复焦点状态下的边框连接 */
.search-input :deep(.el-input__wrapper.is-focus) + .el-input-group__append {
  border-color: #3b82f6 !important;
}

/* 文章元信息样式 */
.post-meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.875rem;
  color: #6b7280;
}

.post-meta-item i {
  font-size: 0.75rem;
  color: #9ca3af;
  width: 14px;
  text-align: center;
}

.post-meta-divider {
  margin: 0 8px;
  color: #d1d5db;
  font-weight: 300;
}

/* 交互按钮容器样式 */
.interaction-buttons-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px !important; /* 强制应用16px间距 */
}

/* 交互按钮样式 */
.interaction-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s ease;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.interaction-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-color: #cbd5e1;
}

.interaction-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.interaction-btn i {
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

/* 点赞状态 */
.interaction-btn.liked {
  background: linear-gradient(135deg, #fef2f2, #fecaca);
  border-color: #fca5a5;
  color: #dc2626;
}

.interaction-btn.liked:hover {
  background: linear-gradient(135deg, #fee2e2, #fca5a5);
  border-color: #f87171;
}

/* 收藏状态 */
.interaction-btn.bookmarked {
  background: linear-gradient(135deg, #eff6ff, #bfdbfe);
  border-color: #93c5fd;
  color: #2563eb;
}

.interaction-btn.bookmarked:hover {
  background: linear-gradient(135deg, #dbeafe, #93c5fd);
  border-color: #60a5fa;
}

/* 封面图片容器样式 - 现代化设计 */
.cover-image-container {
  margin: -24px -24px 24px -24px; /* 负边距让图片延伸到卡片边缘 */
  position: relative;
}

.cover-image-wrapper {
  border-radius: 24px; /* 与卡片圆角保持一致 (rounded-3xl = 24px) */
  overflow: hidden;
  box-shadow: 
    0 10px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1); /* 深度阴影效果 */
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.cover-image-wrapper:hover {
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.15),
    0 10px 10px -5px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px); /* 轻微上移效果 */
}

/* 文章卡片hover效果 */
.article-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border-radius: 24px !important; /* 强制应用圆角，与 rounded-3xl 一致 */
  overflow: hidden !important; /* 确保内容不会溢出圆角边界 */
}

.article-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
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

.article-card:hover .author-avatar-container {
  transform: scale(1.05);
  transition: transform 0.2s ease;
}

/* 强制控制作者头像尺寸 */
.author-avatar-container {
  width: 32px !important;
  height: 32px !important;
  min-width: 32px !important;
  min-height: 32px !important;
  max-width: 32px !important;
  max-height: 32px !important;
  border-radius: 50% !important;
  overflow: hidden !important;
  flex-shrink: 0 !important;
}

.author-avatar-container img {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  object-position: center !important;
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