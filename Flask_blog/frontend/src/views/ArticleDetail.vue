<template>
  <div class="article-detail-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="max-w-4xl mx-auto py-8">
      <div class="bg-white rounded-3xl shadow-sm p-8">
        <el-skeleton :rows="12" animated />
      </div>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="max-w-4xl mx-auto py-8">
      <div class="bg-white rounded-3xl shadow-sm p-8">
        <el-alert :title="error" type="error" show-icon :closable="false" />
      </div>
    </div>
    
    <!-- 文章内容 -->
    <div v-else-if="article" class="article-layout">
      <!-- 主要内容区 -->
      <main class="article-main">
        <article class="article-container">
          <!-- 文章头部 -->
          <header class="article-header">
            <!-- 管理状态（仅管理员可见） -->
            <div v-if="userStore.hasRole(['editor', 'admin'])" class="admin-status-bar">
              <el-tag :type="getStatusType(article.status)" size="small">
                {{ getStatusText(article.status) }}
              </el-tag>
            </div>
            
            <!-- 面包屑导航 -->
            <nav class="breadcrumb-nav" aria-label="面包屑导航">
              <router-link to="/" class="breadcrumb-link">首页</router-link>
              <span class="breadcrumb-separator">/</span>
              <span v-if="article.category" class="breadcrumb-item">{{ article.category }}</span>
              <span v-if="article.category" class="breadcrumb-separator">/</span>
              <span class="breadcrumb-current">{{ article.title }}</span>
            </nav>
            
            <!-- 文章标题 -->
            <h1 class="article-title">{{ article.title }}</h1>
            
            <!-- 文章元信息 -->
            <div class="article-meta">
              <div class="meta-primary">
                <!-- 作者信息 -->
                <div class="author-info">
                  <div class="author-avatar">
                    <img 
                      v-if="article.author?.avatar" 
                      :src="article.author.avatar" 
                      :alt="article.author.name"
                      class="avatar-img"
                      @error="handleAuthorAvatarError"
                    />
                    <div v-else class="avatar-fallback">
                      <i class="fa fa-user" aria-hidden="true"></i>
                    </div>
                  </div>
                  <div class="author-details">
                    <span class="author-name">{{ article.author?.name || '匿名作者' }}</span>
                    <time class="publish-date" :datetime="article.published_at || article.created_at">
                      {{ formatPublishDate(article.published_at || article.created_at) }}
                    </time>
                  </div>
                </div>
                
                <!-- 文章统计 -->
                <div class="article-stats">
                  <span class="stat-item">
                    <i class="fa fa-clock-o" aria-hidden="true"></i>
                    {{ calculateReadTime(article.content_html || '') }} 分钟阅读
                  </span>
                  <span class="stat-item">
                    <i class="fa fa-eye" aria-hidden="true"></i>
                    {{ formatNumber(article.views_count || 0) }} 次浏览
                  </span>
                  <span class="stat-item">
                    <i class="fa fa-heart-o" aria-hidden="true"></i>
                    {{ formatNumber(article.likes_count || 0) }} 点赞
                  </span>
                </div>
              </div>
              
              <!-- 标签 -->
              <div v-if="article.tags && article.tags.length" class="article-tags">
                <el-tag 
                  v-for="tag in article.tags" 
                  :key="tag" 
                  size="small" 
                  type="info"
                  class="tag-item"
                >
                  #{{ tag }}
                </el-tag>
              </div>
            </div>
          </header>

          <!-- 封面图片 -->
          <div v-if="article.featured_image" class="featured-image-container">
            <CoverImage 
              :src="article.featured_image" 
              :alt="article.title" 
              container-class="featured-image-wrapper"
              image-class="featured-image"
            />
          </div>

          <!-- 管理操作区（仅管理员可见） -->
          <div v-if="userStore.hasRole(['editor', 'admin']) && (nextList.length || canSchedule || canUnschedule || canUnpublish)" class="admin-actions">
            <div class="admin-actions-content">
              <span class="admin-actions-label">管理操作:</span>
              <div class="admin-actions-buttons">
                <el-button v-for="n in nextList" :key="n" @click="doTransition(n)" :disabled="acting || !canOperate(n)" size="small">{{ n }}</el-button>
                <el-button v-if="canSchedule" @click="schedule" :disabled="acting" size="small">定时发布</el-button>
                <el-button v-if="canUnschedule" @click="unschedule" :disabled="acting" size="small">取消定时</el-button>
                <el-button v-if="canUnpublish" @click="unpublish" :disabled="acting" size="small" type="warning">下线</el-button>
              </div>
            </div>
          </div>

          <!-- 文章正文 -->
          <div class="article-content">
            <ArticleContentRenderer 
              :content="article.content_html"
              :show-debug-info="false"
              @content-type-detected="handleContentTypeDetected"
              @content-rendered="handleContentRendered"
              @content-error="handleContentError"
              @content-click="handleContentClick"
            />
          </div>

          <!-- 文章底部交互区 -->
          <footer class="article-footer">
            <!-- 点赞收藏区 -->
            <div class="interaction-section">
              <div class="interaction-buttons">
                <button 
                  @click="toggleLike" 
                  :disabled="liking"
                  :class="['interaction-btn', 'like-btn', { 'liked': liked }]"
                >
                  <i :class="liked ? 'fa fa-heart' : 'fa fa-heart-o'" aria-hidden="true"></i>
                  <span>{{ liked ? '已点赞' : '点赞' }}</span>
                  <span class="count">({{ formatNumber(likeCount) }})</span>
                </button>
                
                <button 
                  @click="toggleBookmark" 
                  :disabled="bookmarking"
                  :class="['interaction-btn', 'bookmark-btn', { 'bookmarked': bookmarked }]"
                >
                  <i :class="bookmarked ? 'fa fa-bookmark' : 'fa fa-bookmark-o'" aria-hidden="true"></i>
                  <span>{{ bookmarked ? '已收藏' : '收藏' }}</span>
                </button>
                
                <button class="interaction-btn share-btn" @click="shareArticle">
                  <i class="fa fa-share-alt" aria-hidden="true"></i>
                  <span>分享</span>
                </button>
              </div>
            </div>
            
            <!-- 分隔线 -->
            <div class="section-divider"></div>
            
            <!-- 作者信息卡片 -->
            <div class="author-card">
              <div class="author-card-avatar">
                <img 
                  v-if="article.author?.avatar" 
                  :src="article.author.avatar" 
                  :alt="article.author.name"
                  class="author-card-img"
                />
                <div v-else class="author-card-fallback">
                  <i class="fa fa-user" aria-hidden="true"></i>
                </div>
              </div>
              <div class="author-card-info">
                <h3 class="author-card-name">{{ article.author?.name || '匿名作者' }}</h3>
                <p class="author-card-bio">{{ article.author?.bio || '这位作者很神秘，还没有添加个人简介。' }}</p>
              </div>
            </div>
          </footer>
        </article>
      </main>
      
      <!-- 侧边栏 -->
      <aside class="article-sidebar">
        <!-- 文章目录 -->
        <div class="sidebar-section toc-section">
          <h3 class="sidebar-title">目录</h3>
          <nav class="table-of-contents" v-if="tocItems.length">
            <ol class="toc-list">
              <li 
                v-for="item in tocItems" 
                :key="item.id"
                :class="['toc-item', `toc-level-${item.level}`, { 'active': activeHeading === item.id }]"
              >
                <a 
                  :href="`#${item.id}`" 
                  class="toc-link"
                  @click.prevent="scrollToHeading(item.id)"
                >
                  {{ item.text }}
                </a>
              </li>
            </ol>
          </nav>
          <p v-else class="toc-empty">暂无目录</p>
        </div>
        
        <!-- 阅读进度 -->
        <div class="sidebar-section progress-section">
          <h3 class="sidebar-title">阅读进度</h3>
          <div class="reading-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: readingProgress + '%' }"></div>
            </div>
            <span class="progress-text">{{ Math.round(readingProgress) }}%</span>
          </div>
        </div>
        
      </aside>
    </div>
    
    <!-- 评论区 -->
    <section v-if="article" class="comments-section">
      <div class="max-w-4xl mx-auto">
        <div class="comments-container">
          <h2 class="comments-title">评论区</h2>
          <CommentsThread :article-id="article.id" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useUserStore } from '../stores/user';
import { ElMessage, ElMessageBox } from 'element-plus';
import CommentsThread from '../components/CommentsThread.vue';
import CoverImage from '../components/CoverImage.vue';
import ArticleContentRenderer from '../components/ArticleContentRenderer.vue';
import { common, createLowlight } from 'lowlight';
import { 
  initTheme,
  updateGlobalCodeTheme
} from '../utils/codeTheme';
import apiClient from '../apiClient'; // Simplified

// 创建 lowlight 实例，与编辑器保持一致
const lowlight = createLowlight(common);

// API服务定义
const API = {
    ArticlesService: {
        getArticleBySlug: (slug) => apiClient.get(`/articles/public/slug/${slug}`),
        likeArticle: (id) => apiClient.post(`/articles/${id}/like`),
        bookmarkArticle: (id) => apiClient.post(`/articles/${id}/bookmark`),
        getVersions: (id) => apiClient.get(`/articles/${id}/versions`),
        createVersion: (id) => apiClient.post(`/articles/${id}/versions`),
        rollbackVersion: (id, vNo) => apiClient.post(`/articles/${id}/versions/${vNo}/rollback`),
        diffVersions: (id, vNo, targetNo) => apiClient.get(`/articles/${id}/versions/${vNo}/diff?target=${targetNo}`),
        submitArticle: (id) => apiClient.post(`/articles/${id}/submit`),
        approveArticle: (id) => apiClient.post(`/articles/${id}/approve`),
        rejectArticle: (id, reason) => apiClient.post(`/articles/${id}/reject`, { reason }),
        scheduleArticle: (id, date) => apiClient.post(`/articles/${id}/schedule`, { scheduled_at: date }),
        unpublishArticle: (id) => apiClient.post(`/articles/${id}/unpublish`),
        unscheduleArticle: (id) => apiClient.post(`/articles/${id}/unschedule`),
    }
}

const route = useRoute();
const userStore = useUserStore();
const article = ref(null);
const liked = ref(false);
const bookmarked = ref(false);
const likeCount = ref(0);
const liking = ref(false);
const bookmarking = ref(false);
const loading = ref(false);
const acting = ref(false);
const error = ref('');

// 新增状态
const tocItems = ref([]);
const activeHeading = ref('');
const readingProgress = ref(0);

// 内容渲染器状态
const contentTypeInfo = ref(null);
const isDevelopmentMode = computed(() => process.env.NODE_ENV === 'development' || import.meta.env.DEV);

// 代码主题相关变量已移除

const WORKFLOW_TRANSITIONS = {
    draft: ['submit'],
    pending: ['approve', 'reject'],
}

const nextList = computed(()=> article.value ? (WORKFLOW_TRANSITIONS[article.value.status] || []) : []);
const canOperate = (target) => true; // Simplified for demo
const canSchedule = computed(()=> article.value && article.value.status === 'draft');
const canUnschedule = computed(()=> article.value && article.value.status === 'scheduled');
const canUnpublish = computed(()=> article.value && article.value.status === 'published');

async function doTransition(target){
  if(!article.value) return;
  acting.value=true; error.value='';
  try {
    const id = article.value.id;
    if(target==='submit') await API.ArticlesService.submitArticle(id);
    else if(target==='approve') await API.ArticlesService.approveArticle(id);
    else if(target==='reject') await API.ArticlesService.rejectArticle(id, 'Rejected from UI');
    ElMessage.success('操作成功');
    await load();
  } catch(e){ ElMessage.error('操作失败'); } 
  finally { acting.value=false; }
}

async function load(){
  loading.value = true; 
  error.value = '';
  
  try {
    const slug = route.params.slug;
    if (!slug) {
      throw new Error('文章slug参数缺失');
    }
    
    const resp = await API.ArticlesService.getArticleBySlug(slug);
    if (!resp || !resp.data) {
      throw new Error('API响应格式错误');
    }
    
    const data = resp.data.data;
    if (!data) {
      throw new Error('文章数据为空');
    }
    
    article.value = data;
    likeCount.value = data.likes_count || 0;
    liked.value = !!data.liked;
    bookmarked.value = !!data.bookmarked;
    
    // 确保主题初始化后再应用高亮
    initTheme();
    await nextTick();
    await highlightLater();
  } catch(e){ 
    console.error('文章加载失败:', e);
    error.value = e.response?.data?.message || e.message || '加载文章失败'; 
  } 
  finally { 
    loading.value = false; 
  }
}
onMounted(load);

async function schedule(){
  if(!article.value) return; 
  const date = new Date(Date.now()+3600_000).toISOString();
  await API.ArticlesService.scheduleArticle(article.value.id, date).then(load);
}
async function unpublish(){ 
  if(!article.value) return;
  await API.ArticlesService.unpublishArticle(article.value.id).then(load); 
}
async function unschedule(){ 
  if(!article.value) return;
  await API.ArticlesService.unscheduleArticle(article.value.id).then(load); 
}

// 版本控制相关函数已移除，专注于基本文章显示功能

async function toggleLike(){
  if (!article.value) return;
  liking.value=true;
  try {
    await API.ArticlesService.likeArticle(article.value.id);
    const r = await API.ArticlesService.getArticleBySlug(route.params.slug);
    likeCount.value = r.data.data.likes_count;
    liked.value = r.data.data.liked;
  } catch (error) {
    console.error('点赞操作失败:', error);
  }
  liking.value=false;
}
async function toggleBookmark(){
  if (!article.value) return;
  bookmarking.value=true;
  try {
    await API.ArticlesService.bookmarkArticle(article.value.id);
    bookmarked.value = !bookmarked.value;
  } catch (error) {
    console.error('收藏操作失败:', error);
  }
  bookmarking.value=false;
}

async function highlightLater(){
  await nextTick();
  
  console.log('🎨 ArticleDetail: 开始应用代码高亮');
  
  // 使用默认代码主题
  updateGlobalCodeTheme('default');
  
  // 使用 lowlight 对代码块进行语法高亮和功能增强
  const codeBlocks = document.querySelectorAll('.article-content pre code');
  codeBlocks.forEach((block, index) => {
    const pre = block.parentElement;
    if (!pre) return;
    
    // 获取原始代码内容
    const originalCode = block.textContent || '';
    
    // 尝试检测语言类型
    let language = 'text';
    const classNames = block.className.split(' ');
    for (const className of classNames) {
      if (className.startsWith('language-')) {
        language = className.replace('language-', '');
        break;
      }
    }
    
    try {
      // 使用 lowlight 进行语法高亮
      const result = lowlight.highlight(language, originalCode);
      
      // 清空并重新添加高亮内容
      block.innerHTML = '';
      block.appendChild(result);
      block.className = `hljs language-${language}`;
      
      console.log(`🎯 文章详情页语法高亮成功: ${language}`);
      
      // 添加语言标签
      if (!pre.querySelector('.code-language-label')) {
        addLanguageLabel(pre, language);
      }
    } catch (error) {
      // 语言不支持或出错时，保持原样
      console.warn(`语法高亮失败 (${language}):`, error);
      block.className = `hljs language-${language}`;
    }
    
    // 添加复制按钮
    if (!pre.querySelector('.code-copy-btn')) {
      addCopyButton(pre, originalCode);
    }
  });
  
  console.log(`✅ 语法高亮完成`);
}


// 添加语言标签的辅助函数
function addLanguageLabel(pre, language) {
  if (language && language !== 'text') {
    const label = document.createElement('div');
    label.className = 'code-language-label';
    label.textContent = language.toUpperCase();
    pre.appendChild(label);
  }
}

// 添加复制按钮的辅助函数
function addCopyButton(pre, code) {
  const copyBtn = document.createElement('button');
  copyBtn.className = 'code-copy-btn';
  copyBtn.innerHTML = '<i class="fa fa-copy"></i><span class="copy-text">复制</span>';
  copyBtn.title = '复制代码';
  copyBtn.onclick = () => copyCodeToClipboard(code, copyBtn);
  pre.appendChild(copyBtn);
}

// 复制代码到剪贴板 - 增强版本
function copyCodeToClipboard(text, button) {
  // 清理代码内容，移除多余的空行和缩进
  const cleanedText = text
    .split('\n')
    .map(line => line.trimEnd())
    .join('\n')
    .replace(/^\n+/, '')
    .replace(/\n+$/, '');
  
  navigator.clipboard.writeText(cleanedText).then(() => {
    // 更新按钮状态
    button.innerHTML = '<i class="fa fa-check"></i><span class="copy-text">已复制</span>';
    button.classList.add('copied');
    ElMessage.success('代码已复制到剪贴板');
    
    // 2秒后恢复按钮状态
    setTimeout(() => {
      button.innerHTML = '<i class="fa fa-copy"></i><span class="copy-text">复制</span>';
      button.classList.remove('copied');
    }, 2000);
  }).catch(() => {
    ElMessage.error('复制失败，请手动选择复制');
    
    // 降级方案：选中文本
    try {
      const range = document.createRange();
      const selection = window.getSelection();
      range.selectNodeContents(button.parentElement.querySelector('code'));
      selection.removeAllRanges();
      selection.addRange(range);
    } catch (e) {
      console.warn('无法选中文本:', e);
    }
  });
}

// 代码主题切换功能已移除

// ========== 工具函数 ==========
function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return String(num);
}

function formatPublishDate(dateString) {
  if (!dateString) return '';
  
  try {
    // 修复时区问题：强制将后端时间作为UTC时间处理
    let processedDateString = dateString;
    // 如果时间字符串没有时区标识，添加Z表示UTC
    if (!processedDateString.endsWith('Z') && !processedDateString.includes('+') && !processedDateString.includes('-', 10)) {
      processedDateString += 'Z';
    }
    
    const date = new Date(processedDateString);
    const now = new Date();
    
    // 调试日志 - 在开发模式下显示
    if (process.env.NODE_ENV === 'development') {
      console.log('formatPublishDate debug:', {
        originalInput: dateString,
        processedInput: processedDateString,
        parsedDate: date.toISOString(),
        now: now.toISOString(),
        dateLocal: date.toLocaleString('zh-CN'),
        nowLocal: now.toLocaleString('zh-CN')
      });
    }
    
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    // 相对时间显示 - 更精确
    if (diffMinutes < 1) return '刚刚';
    if (diffMinutes < 60) return `${diffMinutes}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}个月前`;
    
    return date.toLocaleDateString('zh-CN');
  } catch (error) {
    console.warn('formatPublishDate error:', error, 'input:', dateString);
    return '';
  }
}

function calculateReadTime(content) {
  if (!content) return 0;
  const plainText = content.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
  const chineseChars = (plainText.match(/[\u4e00-\u9fa5]/g) || []).length;
  const englishWords = (plainText.replace(/[\u4e00-\u9fa5]/g, '').match(/\b\w+\b/g) || []).length;
  const totalWords = chineseChars + englishWords;
  return Math.max(1, Math.ceil(totalWords / 275));
}

function getStatusType(status) {
  const statusMap = {
    'draft': 'info',
    'pending': 'warning', 
    'published': 'success',
    'scheduled': 'primary'
  };
  return statusMap[status] || 'info';
}

function getStatusText(status) {
  const statusMap = {
    'draft': '草稿',
    'pending': '待审核',
    'published': '已发布',
    'scheduled': '定时发布'
  };
  return statusMap[status] || status;
}

function handleAuthorAvatarError(e) {
  e.target.style.display = 'none';
}

function shareArticle() {
  if (!article.value) return;
  
  if (navigator.share) {
    navigator.share({
      title: article.value.title,
      text: article.value.summary || '推荐一篇文章',
      url: window.location.href,
    });
  } else {
    // 降级方案：复制链接到剪贴板
    navigator.clipboard.writeText(window.location.href).then(() => {
      ElMessage.success('链接已复制到剪贴板');
    });
  }
}

// 生成目录
function generateTOC() {
  tocItems.value = [];
  const content = document.querySelector('.article-content');
  if (!content) return;
  
  const headings = content.querySelectorAll('h1, h2, h3, h4, h5, h6');
  headings.forEach((heading, index) => {
    const id = `heading-${index}`;
    heading.id = id;
    
    tocItems.value.push({
      id,
      text: heading.textContent,
      level: parseInt(heading.tagName.charAt(1))
    });
  });
}

// 滚动到指定标题
function scrollToHeading(id) {
  const element = document.getElementById(id);
  if (element) {
    element.scrollIntoView({ 
      behavior: 'smooth',
      block: 'start'
    });
  }
}

// 监听滚动，更新阅读进度和活跃标题
function handleScroll() {
  // 计算阅读进度
  const scrollTop = window.pageYOffset;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  readingProgress.value = Math.min((scrollTop / docHeight) * 100, 100);
  
  // 更新活跃标题
  const headings = document.querySelectorAll('.article-content h1, .article-content h2, .article-content h3, .article-content h4, .article-content h5, .article-content h6');
  let activeId = '';
  
  headings.forEach(heading => {
    const rect = heading.getBoundingClientRect();
    if (rect.top <= 100 && rect.top >= -100) {
      activeId = heading.id;
    }
  });
  
  activeHeading.value = activeId;
}

// 监听文章变化
watch(()=>article.value, async (newVal) => {
  if (newVal) {
    await highlightLater();
    await nextTick();
    generateTOC();
  }
}, { deep: true });

// 监听滚动事件
onMounted(() => {
  window.addEventListener('scroll', handleScroll);
  // initTheme() 现在在 load() 函数中调用，确保主题和内容同步
});

// 清理事件监听器
onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});

// ===== 内容渲染器处理方法 =====

// 处理内容类型检测结果
const handleContentTypeDetected = (analysis) => {
  contentTypeInfo.value = analysis;
  
  // 静默处理，不输出调试信息
  // 根据内容类型调整页面行为
  if (analysis.type === 'html_source' && analysis.features?.estimatedPreservationNeeded) {
    // 为HTML内容启用特殊处理
    nextTick(() => {
      // 静默处理样式隔离
    });
  }
};

// 处理内容渲染完成
const handleContentRendered = (renderInfo) => {
  // 静默处理渲染完成事件
  
  // 内容渲染完成后的后续处理
  nextTick(async () => {
    // 重新生成目录（因为内容可能发生了变化）
    await generateTOC();
    
    // 重新应用代码高亮（如果需要）
    if (renderInfo.contentType === 'markdown') {
      await highlightLater();
    }
  });
};

// 处理内容渲染错误
const handleContentError = (error) => {
  console.error('❌ ArticleDetail: 内容渲染错误', error);
  ElMessage.error(`内容渲染失败: ${error.message || '未知错误'}`);
  
  // 可以在这里实现降级处理，比如显示原始HTML
  if (isDevelopmentMode.value) {
    console.warn('💡 考虑实现内容渲染的降级处理机制');
  }
};

// 处理内容点击事件
const handleContentClick = (clickInfo) => {
  const { event, contentType, target } = clickInfo;
  
  // 处理外部链接
  if (target.tagName === 'A' && target.getAttribute('href')?.startsWith('http')) {
    // 外部链接处理
    if (!target.hasAttribute('target')) {
      target.setAttribute('target', '_blank');
      target.setAttribute('rel', 'noopener noreferrer');
    }
  }
  
  // 如果是代码块点击，可能需要特殊处理
  if (target.closest('pre') && contentType === 'html_source') {
    // HTML源码中的代码块点击处理
    const codeBlock = target.closest('pre');
    if (!codeBlock.querySelector('.code-copy-btn')) {
      // 为HTML内容中的代码块添加复制按钮
      addCopyButton(codeBlock, codeBlock.textContent);
    }
  }
};

</script>

<style scoped>
/* ===== 文章详情页主体样式 ===== */

.article-detail-page {
  min-height: 100vh;
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(255 255 255) 100%);
  padding: 2rem 1rem;
}

/* 文章布局 */
.article-layout {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 3rem;
  align-items: start;
}

@media (max-width: 1024px) {
  .article-layout {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
}

/* ===== 主要内容区样式 ===== */

.article-main {
  min-width: 0;
}

.article-container {
  background: white;
  border-radius: 24px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

/* ===== 文章头部样式 ===== */

.article-header {
  padding: 3rem 3rem 2rem;
  background: linear-gradient(135deg, rgb(255 255 255) 0%, rgb(248 250 252) 100%);
}

.admin-status-bar {
  margin-bottom: 1rem;
}

/* 面包屑导航 */
.breadcrumb-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 2rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.breadcrumb-link {
  color: #3b82f6;
  text-decoration: none;
  transition: color 0.2s ease;
}

.breadcrumb-link:hover {
  color: #2563eb;
}

.breadcrumb-separator {
  color: #9ca3af;
}

.breadcrumb-current {
  color: #374151;
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 文章标题 */
.article-title {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1.2;
  color: #111827;
  margin-bottom: 2rem;
  letter-spacing: -0.025em;
}

@media (max-width: 768px) {
  .article-title {
    font-size: 2rem;
  }
}

/* 文章元信息 */
.article-meta {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.meta-primary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

/* 作者信息 */
.author-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.author-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  color: white;
  font-size: 1.25rem;
}

.author-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.author-name {
  font-weight: 600;
  color: #111827;
  font-size: 1rem;
}

.publish-date {
  color: #6b7280;
  font-size: 0.875rem;
}

/* 文章统计 */
.article-stats {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.stat-item i {
  color: #9ca3af;
  font-size: 0.875rem;
}

/* 标签样式 */
.article-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.tag-item {
  transition: all 0.2s ease;
  cursor: pointer;
}

.tag-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* ===== 封面图片样式 ===== */

.featured-image-container {
  margin: 2rem 3rem;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
}

.featured-image-wrapper {
  aspect-ratio: 16/9;
  overflow: hidden;
  border-radius: 16px;
}

.featured-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.featured-image-container:hover .featured-image {
  transform: scale(1.05);
}

/* ===== 管理操作区样式 ===== */

.admin-actions {
  margin: 0 3rem 2rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border: 1px solid #f59e0b;
  border-radius: 12px;
}

.admin-actions-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.admin-actions-label {
  font-weight: 600;
  color: #92400e;
}

.admin-actions-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* ===== 文章正文样式 ===== */

.article-content {
  padding: 0 3rem 3rem;
  font-size: 1.125rem;
  line-height: 1.8;
  color: #374151;
  max-width: none;
}

.article-content :deep(h1),
.article-content :deep(h2),
.article-content :deep(h3),
.article-content :deep(h4),
.article-content :deep(h5),
.article-content :deep(h6) {
  margin: 2rem 0 1rem;
  font-weight: 700;
  line-height: 1.3;
  color: #111827;
  scroll-margin-top: 100px;
}

.article-content :deep(h1) { font-size: 2rem; }
.article-content :deep(h2) { font-size: 1.75rem; }
.article-content :deep(h3) { font-size: 1.5rem; }
.article-content :deep(h4) { font-size: 1.25rem; }

.article-content :deep(p) {
  margin: 1.5rem 0;
  text-align: justify;
}

.article-content :deep(ul),
.article-content :deep(ol) {
  margin: 1.5rem 0;
  padding-left: 2rem;
}

.article-content :deep(li) {
  margin: 0.5rem 0;
}

.article-content :deep(blockquote) {
  margin: 2rem 0;
  padding: 1rem 1.5rem;
  border-left: 4px solid #3b82f6;
  background: #f8fafc;
  border-radius: 0 8px 8px 0;
  font-style: italic;
}

/* ===== Shiki 代码块样式 ===== */

.article-content :deep(.shiki) {
  position: relative;
  margin: 2rem 0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 25px -5px rgba(0, 0, 0, 0.25);
  border: 1px solid #3c4043;
  transition: all 0.3s ease;
}

.article-content :deep(.shiki:hover) {
  box-shadow: 0 12px 35px -5px rgba(0, 0, 0, 0.35);
  transform: translateY(-2px);
}

.article-content :deep(.shiki pre) {
  margin: 0;
  padding: 1.5rem;
  overflow-x: auto;
  background: transparent !important;
  white-space: pre !important;
  word-wrap: normal !important;
}

.article-content :deep(.shiki code) {
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace !important;
  font-size: 0.875rem !important;
  line-height: 1.6 !important;
  font-weight: 400;
  background: transparent !important;
  padding: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  tab-size: 4;
  -moz-tab-size: 4;
  display: block !important;
}

/* 统一的语法高亮代码块样式 */
.article-content :deep(pre) {
  position: relative;
  margin: 2rem 0;
  padding: 1.5rem;
  background: #0d1117 !important;
  border-radius: 16px;
  overflow-x: auto;
  box-shadow: 0 8px 25px -5px rgba(0, 0, 0, 0.25);
  border: 1px solid #30363d;
  transition: all 0.3s ease;
  white-space: pre !important;
  word-wrap: normal !important;
}

.article-content :deep(pre:hover) {
  box-shadow: 0 12px 35px -5px rgba(0, 0, 0, 0.35);
  transform: translateY(-2px);
}

.article-content :deep(pre code) {
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #f0f6fc !important;
  background: transparent !important;
  padding: 0 !important;
  border: none !important;
  display: block !important;
  font-weight: 400;
}

/* Lowlight 语法高亮样式 - 与编辑器保持一致 */
.article-content :deep(.hljs) {
  background: transparent !important;
  color: #f0f6fc !important;
}

/* 语法高亮颜色配置 - GitHub Dark 主题 */
.article-content :deep(.hljs-comment),
.article-content :deep(.hljs-quote) {
  color: #8b949e !important;
  font-style: italic;
}

.article-content :deep(.hljs-keyword),
.article-content :deep(.hljs-selector-tag),
.article-content :deep(.hljs-literal),
.article-content :deep(.hljs-type) {
  color: #ff7b72 !important;
}

.article-content :deep(.hljs-string),
.article-content :deep(.hljs-regexp) {
  color: #a5d6ff !important;
}

.article-content :deep(.hljs-subst),
.article-content :deep(.hljs-symbol) {
  color: #f0f6fc !important;
}

.article-content :deep(.hljs-class),
.article-content :deep(.hljs-function),
.article-content :deep(.hljs-title) {
  color: #d2a8ff !important;
}

.article-content :deep(.hljs-params),
.article-content :deep(.hljs-built_in) {
  color: #ffa657 !important;
}

.article-content :deep(.hljs-number),
.article-content :deep(.hljs-literal) {
  color: #79c0ff !important;
}

.article-content :deep(.hljs-variable),
.article-content :deep(.hljs-template-variable) {
  color: #ffa657 !important;
}

.article-content :deep(.hljs-attribute) {
  color: #79c0ff !important;
}

/* 通用代码样式 */
.article-content :deep(code) {
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  font-weight: 400;
}

/* 优化后的行内代码样式 */
.article-content :deep(p code),
.article-content :deep(li code),
.article-content :deep(td code) {
  background: #f6f8fa;
  color: #d73a49;
  padding: 0.1875rem 0.375rem;
  border-radius: 6px;
  font-size: 0.85em;
  font-weight: 500;
  border: 1px solid #e1e4e8;
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
}

/* 现代化代码复制按钮 */
.article-content :deep(.code-copy-btn) {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #d1d5db;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  backdrop-filter: blur(12px);
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 70px;
  justify-content: center;
}

.article-content :deep(.code-copy-btn:hover) {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
  color: #bfdbfe;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.article-content :deep(.code-copy-btn:active) {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
}

.article-content :deep(.code-copy-btn.copied) {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.4);
  color: #86efac;
}

.article-content :deep(.code-copy-btn .copy-text) {
  font-size: 0.75rem;
  font-weight: 500;
}

.article-content :deep(.code-copy-btn i) {
  font-size: 0.75rem;
}

/* 代码语言标签 */
.article-content :deep(.code-language-label) {
  position: absolute;
  top: 12px;
  left: 12px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  z-index: 2;
}

/* 代码块滚动条样式 */
.article-content :deep(pre)::-webkit-scrollbar {
  height: 8px;
}

.article-content :deep(pre)::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.article-content :deep(pre)::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.article-content :deep(pre)::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.article-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 2rem auto;
  display: block;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* ===== 文章底部交互区样式 ===== */

.article-footer {
  padding: 2rem 3rem 3rem;
  background: #f9fafb;
}

.interaction-section {
  margin-bottom: 2rem;
}

.interaction-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.interaction-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 50px;
  background: white;
  color: #6b7280;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.3s ease;
  cursor: pointer;
  min-width: 100px;
  justify-content: center;
}

.interaction-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.interaction-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.like-btn.liked {
  background: linear-gradient(135deg, #fef2f2, #fecaca);
  border-color: #f87171;
  color: #dc2626;
}

.bookmark-btn.bookmarked {
  background: linear-gradient(135deg, #eff6ff, #bfdbfe);
  border-color: #60a5fa;
  color: #2563eb;
}

.share-btn:hover {
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border-color: #0ea5e9;
  color: #0284c7;
}

.count {
  font-size: 0.75rem;
  opacity: 0.8;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 2rem 0;
}

/* ===== 作者信息卡片样式 ===== */

.author-card {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
}

.author-card-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.author-card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-card-fallback {
  color: white;
  font-size: 1.5rem;
}

.author-card-info {
  flex: 1;
  min-width: 0;
}

.author-card-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.5rem;
}

.author-card-bio {
  color: #6b7280;
  line-height: 1.5;
  margin: 0;
}

/* ===== 侧边栏样式 ===== */

.article-sidebar {
  position: sticky;
  top: 2rem;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .article-sidebar {
    position: static;
    max-height: none;
    order: 2;
  }
}

.sidebar-section {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
}

/* 主题选择器相关样式已移除 */

:deep(.el-select .el-input__inner:focus) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

:deep(.el-select-dropdown) {
  border-radius: 8px;
  border-color: #e5e7eb;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

:deep(.el-select-dropdown__item) {
  padding: 8px 12px;
  font-size: 0.875rem;
}

:deep(.el-select-dropdown__item:hover) {
  background: #f3f4f6;
}

:deep(.el-select-dropdown__item.selected) {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #f3f4f6;
}

/* 目录样式 */
.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-item {
  margin: 0.25rem 0;
}

.toc-link {
  display: block;
  padding: 0.5rem 0.75rem;
  color: #6b7280;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.4;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.toc-link:hover {
  background: #f3f4f6;
  color: #374151;
}

.toc-item.active .toc-link {
  background: #eff6ff;
  color: #2563eb;
  border-left-color: #3b82f6;
  font-weight: 500;
}

.toc-level-2 .toc-link { padding-left: 1.5rem; }
.toc-level-3 .toc-link { padding-left: 2.25rem; }
.toc-level-4 .toc-link { padding-left: 3rem; }

.toc-empty {
  color: #9ca3af;
  font-size: 0.875rem;
  text-align: center;
  margin: 0;
  padding: 1rem;
}

/* 阅读进度样式 */
.reading-progress {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  min-width: 40px;
}

/* ===== 评论区样式 ===== */

.comments-section {
  margin-top: 3rem;
  padding: 2rem 1rem;
  background: white;
}

.comments-container {
  background: white;
  border-radius: 24px;
  padding: 3rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.comments-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 2rem;
  text-align: center;
}

/* ===== 响应式设计 ===== */

@media (max-width: 768px) {
  .article-detail-page {
    padding: 1rem 0.5rem;
  }
  
  .article-header,
  .article-content,
  .article-footer {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
  
  .featured-image-container {
    margin-left: 1.5rem;
    margin-right: 1.5rem;
  }
  
  .article-content {
    font-size: 1rem;
    line-height: 1.7;
  }
  
  .meta-primary {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .article-stats {
    gap: 1rem;
  }
  
  .interaction-buttons {
    flex-direction: column;
    align-items: stretch;
  }
  
  .interaction-btn {
    min-width: auto;
  }
  
  .comments-container {
    padding: 2rem 1.5rem;
  }
}

@media (max-width: 480px) {
  .article-title {
    font-size: 1.75rem;
  }
  
  .breadcrumb-current {
    max-width: 150px;
  }
  
  .author-card {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}

/* ===== 可访问性优化 ===== */

@media (prefers-reduced-motion: reduce) {
  .featured-image,
  .interaction-btn,
  .toc-link,
  .progress-fill {
    transition: none;
  }
}

/* ===== 打印样式 ===== */

@media print {
  .article-sidebar,
  .interaction-section,
  .admin-actions,
  .comments-section {
    display: none;
  }
  
  .article-layout {
    grid-template-columns: 1fr;
  }
  
  .article-container {
    box-shadow: none;
    border: 1px solid #e5e7eb;
  }
}
</style>