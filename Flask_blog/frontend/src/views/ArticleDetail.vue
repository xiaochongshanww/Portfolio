<template>
  <div class="article-detail-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="shell state-shell">
      <el-skeleton :rows="12" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="shell state-shell">
      <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>
    
    <!-- 文章内容 -->
    <div v-else-if="article" class="article-layout shell">
      <!-- 主要内容区 -->
      <main class="article-main">
        <article class="article-container">
          <!-- Stage 1: 文章身份(03 号规范第 5 节,text 轴) -->
          <header class="article-head content-width-text">
            <div class="crumb">{{ article.category || '文章' }}</div>
            <h1 class="article-title">{{ article.title }}</h1>
            <p v-if="article.summary" class="deck">{{ article.summary }}</p>
            <div class="article-meta">
              <span>{{ formatDate(article.published_at || article.created_at) }}</span>
              <span v-if="article.updated_at && article.updated_at !== article.published_at">·</span>
              <span v-if="article.updated_at && article.updated_at !== article.published_at">最后更新于 {{ formatDate(article.updated_at) }}</span>
            </div>
            <div v-if="articleTags.length" class="article-tags">
              <span v-for="t in articleTags" :key="t" class="tag">{{ t }}</span>
            </div>
          </header>

          <!-- 管理操作区（仅管理员可见） -->
          <ArticleActions
            :is-moderator="!!userStore.hasRole(['editor', 'admin'])"
            :next-list="nextList"
            :can-schedule="!!canSchedule"
            :can-unschedule="!!canUnschedule"
            :can-unpublish="!!canUnpublish"
            :acting="acting"
            :can-operate="canOperate"
            @transition="doTransition"
            @schedule="schedule"
            @unschedule="unschedule"
            @unpublish="unpublish"
          />

          <!-- 正文渲染区(Stage 3):Blocks 统一渲染 -->
          <section class="reading-canvas">
            <ArticleRenderer v-if="blocks.length" :blocks="blocks" />
            <!-- Blocks 为空时回退旧渲染器(防御:转换异常不至于白屏) -->
            <ArticleContentRenderer
              v-else
              :content="article.content_md || article.content_html"
              :show-debug-info="false"
              @content-error="handleContentError"
            />
          </section>

          <!-- Stage 4: 结尾(E6) -->
          <footer class="article-end content-width-text">
            <div class="maintenance">
              <h3>这篇文章仍在持续维护</h3>
              <p>如果内容存在错误或需要补充,欢迎通过 GitHub Issue 指出。</p>
              <div class="maintenance-meta">
                <span>最后更新:{{ formatDate(article.updated_at || article.published_at || article.created_at) }}</span>
              </div>
            </div>

            <nav v-if="prevNext.prev || prevNext.next" class="article-nav">
              <a v-if="prevNext.prev" :href="'/article/' + prevNext.prev.slug" @click.prevent="goArticle(prevNext.prev.slug)">
                <small>上一篇</small>
                <b>{{ prevNext.prev.title }}</b>
              </a>
              <a v-if="prevNext.next" :href="'/article/' + prevNext.next.slug" @click.prevent="goArticle(prevNext.next.slug)">
                <small>下一篇</small>
                <b>{{ prevNext.next.title }}</b>
              </a>
            </nav>
          </footer>
        </article>
      </main>

      <!-- 页面级阅读工具(fixed,不占布局) -->
      <ReadingRail :toc="railToc" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';

const props = withDefaults(defineProps<{
  slug?: string
}>(), { slug: '' })

import { ElMessage, ElMessageBox } from 'element-plus';
import ArticleContentRenderer from '../components/ArticleContentRenderer.vue';
import ArticleActions from '../components/ArticleActions.vue';
import ArticleRenderer from '../components/article/ArticleRenderer.vue';
import ReadingRail from '../components/article/ReadingRail.vue';
import { blocksFromMarkdown } from '../utils/blocksFromMarkdown';
import { recordRecentArticle } from '../composables/useSearchOverlay';
import { setMeta } from '../composables/useMeta';
import type { ArticleBlock } from '../types/articleBlocks';
import { common, createLowlight } from 'lowlight';
import hljs from 'highlight.js';
import { 
  initTheme,
  updateGlobalCodeTheme
} from '../utils/codeTheme';
import { API as UnifiedAPI } from '../api';
import type { Article } from '../types';

// 创建 lowlight 实例，与编辑器保持一致
const lowlight = createLowlight(common);

// API服务定义（统一走 @/api 出口）
const API = {
    ArticlesService: {
        getArticleBySlug: (slug: string) => UnifiedAPI.getArticleBySlug(slug),
        getVersions: (id: number) => UnifiedAPI.getArticleVersions(id),
        createVersion: (id: number) => UnifiedAPI.createArticleVersion(id),
        rollbackVersion: (id: number, vNo: number) => UnifiedAPI.rollbackVersion(id, vNo),
        diffVersions: (id: number, vNo: number, targetNo: number) => UnifiedAPI.diffVersions(id, vNo, targetNo),
        submitArticle: (id: number) => UnifiedAPI.submitArticle(id),
        approveArticle: (id: number) => UnifiedAPI.approveArticle(id),
        rejectArticle: (id: number, reason: string) => UnifiedAPI.rejectArticle(id, { reason }),
        scheduleArticle: (id: number, date: string) => UnifiedAPI.scheduleArticle(id, { scheduled_at: date }),
        unpublishArticle: (id: number) => UnifiedAPI.unpublishArticle(id),
        unscheduleArticle: (id: number) => UnifiedAPI.unscheduleArticle(id),
    }
}

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const article = ref<Article | null>(null);
const loading = ref(false);
const acting = ref(false);
const error = ref('');

// 新增状态
const tocItems = ref<{ id?: string; text?: string; level?: number }[]>([]);
const activeHeading = ref('');
const readingProgress = ref(0);

// Blocks 渲染管线(E7):content_md → ArticleBlock[]
const blocks = computed<ArticleBlock[]>(() => {
  const md = article.value?.content_md
  if (!md) return []
  try {
    return blocksFromMarkdown(md)
  } catch (e) {
    console.warn('[ArticleDetail] blocks 转换失败,回退旧渲染器:', e)
    return []
  }
});

/** ReadingRail 目录:由 heading blocks 生成(≤H3) */
const railToc = computed(() =>
  blocks.value.flatMap((b) =>
    b.type === 'heading' && b.level <= 3 ? [{ anchor: b.anchor, text: b.text }] : [],
  ),
);

/** 文章头标签 chips(原型 Stage 1);兼容 tags 为 slug 字符串数组或 {name} 对象数组 */
const articleTags = computed(() => {
  const t = article.value?.tags;
  if (!Array.isArray(t)) return [];
  const list = t as Array<string | { name?: string }>;
  return list
    .map((x) => (typeof x === 'string' ? x : x?.name))
    .filter((name): name is string => !!name);
});

/** 上一篇/下一篇(E6):P0 用同列表相邻文章近似 */
const prevNext = computed(() => {
  // 相邻文章需要列表上下文,P0 先留空——单篇文章时导航隐藏
  return { prev: null as null | { slug: string; title: string }, next: null as null | { slug: string; title: string } };
});

function formatDate(s?: string | null) {
  if (!s) return '';
  try {
    let str = s;
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) str += 'Z';
    const d = new Date(str);
    return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`;
  } catch (e) {
    return '';
  }
}

function goArticle(slug: string) {
  router.push(`/article/${slug}`);
}

// 内容渲染器状态
const contentTypeInfo = ref<{ type: string; features?: { estimatedPreservationNeeded?: boolean } } | null>(null);
const isDevelopmentMode = computed(() => process.env.NODE_ENV === 'development' || import.meta.env.DEV);

// 代码主题相关变量已移除

const WORKFLOW_TRANSITIONS: Record<string, string[]> = {
    draft: ['submit'],
    pending: ['通过', '拒绝'],
}

const nextList = computed(()=> article.value ? (WORKFLOW_TRANSITIONS[article.value.status || ''] || []) : []);
const canOperate = (target: string) => true; // Simplified for demo
const canSchedule = computed(()=> article.value && article.value.status === 'draft');
const canUnschedule = computed(()=> article.value && article.value.status === 'scheduled');
const canUnpublish = computed(()=> article.value && article.value.status === 'published');

// 检查是否为文章作者
const isAuthor = computed(() => {
  return userStore.user?.id === article.value?.author?.id;
});

// 检查编辑权限（作者或管理员）
const canEdit = computed(() => {
  return isAuthor.value || userStore.hasRole(['editor', 'admin']);
});

// 编辑文章
function editArticle() {
  if (!article.value || !canEdit.value) {
    ElMessage.warning('没有编辑权限');
    return;
  }
  
  // 路由到普通编辑页面，传入文章ID
  router.push(`/articles/${article.value.id}/edit`);
}

async function doTransition(target: string){
  if(!article.value) return;
  acting.value=true; error.value='';
  
  // 调试信息：检查管理操作前的认证状态
  const tokenBefore = localStorage.getItem('access_token');
  console.log(`🔧 管理操作${target}前 - Token存在:`, !!tokenBefore);
  
  try {
    const id = article.value.id;
    if(target==='submit') await API.ArticlesService.submitArticle(id);
    else if(target==='通过') await API.ArticlesService.approveArticle(id);
    else if(target==='拒绝') await API.ArticlesService.rejectArticle(id, 'Rejected from UI');
    
    // 调试信息：检查管理操作后的认证状态
    const tokenAfter = localStorage.getItem('access_token');
    console.log(`🔧 管理操作${target}后 - Token存在:`, !!tokenAfter);
    console.log(`🔧 Token状态变化:`, tokenBefore === tokenAfter ? '无变化' : '已变化');
    
    ElMessage.success('操作成功');
    await load();
  } catch(e){ 
    console.error(`🔧 管理操作${target}失败:`, e);
    ElMessage.error('操作失败'); 
  } 
  finally { acting.value=false; }
}

async function load(){
  loading.value = true; 
  error.value = '';
  
  try {
    const slugParam = props.slug || route.params.slug;
    const slug = Array.isArray(slugParam) ? slugParam[0] : (slugParam || '');
    if (!slug) {
      throw new Error('文章slug参数缺失');
    }
    
    // 调试信息：检查用户认证状态
    console.log('🔍 页面加载 - 用户认证状态:', !!userStore.token, '用户ID:', userStore.user?.id);
    
    const resp = await API.ArticlesService.getArticleBySlug(slug);
    if (!resp || !resp.data) {
      throw new Error('API响应格式错误');
    }
    
    const data = resp.data.data;
    if (!data) {
      throw new Error('文章数据为空');
    }
    
    // 调试：检查API返回的内容格式
    console.log('📊 API返回的文章数据:', {
      title: data.title,
      hasContentHtml: !!data.content_html,
      hasContentMd: !!data.content_md,
      contentHtmlLength: data.content_html?.length || 0,
      contentMdLength: data.content_md?.length || 0,
      contentHtmlSample: data.content_html?.substring(0, 100) + '...',
      contentMdSample: data.content_md?.substring(0, 100) + '...',
      actualContentUsed: data.content_md || data.content_html,
      actualContentLength: (data.content_md || data.content_html)?.length || 0
    });
    
    article.value = data;
    // D1:记录最近浏览(SearchOverlay 默认态数据源)
    if (data?.slug) recordRecentArticle(String(data.slug), String(data.title || ''));
    // F2:SEO 元素(title/description/canonical/OG/时间)
    setMeta({
      title: data.seo_title || data.title || '',
      description: data.seo_desc || data.summary || '',
      image: data.featured_image || undefined,
      type: 'article',
      publishedTime: data.published_at || data.created_at || undefined,
      modifiedTime: data.updated_at || data.published_at || undefined,
    });

    // 确保主题初始化后再应用高亮
    initTheme();
    await nextTick();
    await highlightLater();
  } catch(e){ 
    console.error('文章加载失败:', e);
    const err = e as { response?: { data?: { message?: string } }; message?: string };
    error.value = err.response?.data?.message || err.message || '加载文章失败'; 
  } 
  finally { 
    loading.value = false; 
  }
}
onMounted(async () => {
  // 调试信息：页面挂载时的认证状态
  const tokenOnMount = localStorage.getItem('access_token');
  console.log('🚀 页面挂载 - Token存在:', !!tokenOnMount);
  console.log('🚀 页面挂载 - userStore.token存在:', !!userStore.token);
  
  // 等待用户认证状态初始化完成
  if (userStore.token) {
    console.log('⏳ 等待用户认证状态初始化...');
    await userStore.initAuth();
    console.log('✅ 用户认证状态初始化完成');
  }
  
  // 开始加载文章数据
  await load();
  
  // 调试信息：页面加载完成后的认证状态
  const tokenAfterLoad = localStorage.getItem('access_token');
  console.log('🏁 页面加载完成 - Token存在:', !!tokenAfterLoad);
});

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

async function highlightLater(){
  await nextTick();
  
  console.log('🎨 ArticleDetail: 开始应用代码高亮');
  
  // 使用默认代码主题
  updateGlobalCodeTheme('default');
  
  // 检查代码块，但优先保留Shiki渲染
  const codeBlocks = document.querySelectorAll('.article-content pre code');
  console.log(`🔍 发现 ${codeBlocks.length} 个代码块`);
  
  codeBlocks.forEach((block, index) => {
    const pre = block.parentElement;
    if (!pre) return;
    
    // 检查是否已经由 Shiki 或新的处理器渲染
    if (pre.classList.contains('shiki') || 
        pre.classList.contains('basic-code-block') || 
        pre.classList.contains('fallback-code-block') ||
        pre.querySelector('.shiki') ||
        pre.style.backgroundColor) { // Shiki通常会添加背景色
      console.log(`✅ 第 ${index + 1} 个代码块已由现代处理器渲染，跳过传统highlight.js处理`);
      return;
    }
    
    console.log(`⚠️ 第 ${index + 1} 个代码块未被现代处理器渲染，可能需要降级处理`);
    // 但是现在我们不做降级处理，让用户知道有问题
    
    // 暂时跳过传统highlight.js处理，让新的Shiki处理器处理所有代码块
    // 如果有未处理的代码块，说明新处理器有问题，需要调试
    console.warn(`🚨 代码块 ${index + 1} 未被Shiki处理器渲染，这可能表示配置问题`);
    
    // 添加一个明显的标记，方便调试
    if (!pre.querySelector('.debug-unprocessed-marker')) {
      const marker = document.createElement('div');
      marker.className = 'debug-unprocessed-marker';
      marker.style.cssText = 'background: red; color: white; padding: 2px 4px; font-size: 12px; margin-bottom: 4px;';
      marker.textContent = `未处理的代码块 - 检查Shiki配置`;
      pre.insertBefore(marker, pre.firstChild);
    }
    
    // 不再使用lowlight处理，避免冲突
    
    // 添加复制按钮
    if (!pre.querySelector('.code-copy-btn')) {
      addCopyButton(pre, block.textContent || '');
    }
  });
  
  console.log(`✅ 语法高亮完成`);
}


// 添加语言标签的辅助函数
function addLanguageLabel(pre: HTMLElement, language: string) {
  if (language && language !== 'text') {
    const label = document.createElement('div');
    label.className = 'code-language-label';
    label.textContent = language.toUpperCase();
    pre.appendChild(label);
  }
}

// 添加复制按钮的辅助函数
function addCopyButton(pre: HTMLElement, code: string) {
  const copyBtn = document.createElement('button');
  copyBtn.className = 'code-copy-btn';
  copyBtn.innerHTML = '<i class="fa fa-copy"></i><span class="copy-text">复制</span>';
  copyBtn.title = '复制代码';
  copyBtn.onclick = () => copyCodeToClipboard(code, copyBtn);
  pre.appendChild(copyBtn);
}

// 复制代码到剪贴板 - 增强版本
function copyCodeToClipboard(text: string, button: HTMLElement) {
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
      const parent = button.parentElement;
      const codeEl = parent ? parent.querySelector('code') : null;
      if (!selection || !codeEl) return;
      range.selectNodeContents(codeEl);
      selection.removeAllRanges();
      selection.addRange(range);
    } catch (e) {
      console.warn('无法选中文本:', e);
    }
  });
}

// 代码主题切换功能已移除


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
function scrollToHeading(id: string) {
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
const handleContentTypeDetected = (analysis: { type: string; features?: { estimatedPreservationNeeded?: boolean } }) => {
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
const handleContentRendered = (renderInfo: { contentType: string }) => {
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
const handleContentError = (error: Error) => {
  console.error('❌ ArticleDetail: 内容渲染错误', error);
  ElMessage.error(`内容渲染失败: ${error.message || '未知错误'}`);
  
  // 可以在这里实现降级处理，比如显示原始HTML
  if (isDevelopmentMode.value) {
    console.warn('💡 考虑实现内容渲染的降级处理机制');
  }
};

// 处理内容点击事件
const handleContentClick = (clickInfo: { event: Event; contentType: string; target: HTMLElement }) => {
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
    const codeBlock = target.closest<HTMLPreElement>('pre');
    if (codeBlock && !codeBlock.querySelector('.code-copy-btn')) {
      // 为HTML内容中的代码块添加复制按钮
      addCopyButton(codeBlock, codeBlock.textContent || '');
    }
  }
};

</script>

<style scoped>
/* ===== P0 排版(E6/E7,原型 V5b clean-rail):暖纸底 + shell 单列内容轴 ===== */

.article-detail-page {
  background: var(--bg);
  padding: 0 0 60px;
}

/* loading/error 态:与首页 state-block 同语言,边框优先于阴影 */
.state-shell {
  padding-top: 60px;
  padding-bottom: 60px;
}

/* 不再双列:ReadingRail 是 fixed 浮层,不占 grid 位;宽度由 .shell(1180px)提供 */
.article-layout {
  display: block;
}

.article-container {
  background: transparent;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
  padding-top: 54px;
}

/* Stage 1: 文章身份 */
.crumb {
  font-size: 13px;
  color: var(--muted);
}
.article-title {
  font-size: clamp(36px, 5vw, 48px);
  line-height: 1.1;
  letter-spacing: -0.052em;
  margin: 17px 0 15px;
  color: var(--text);
}
.deck {
  font-size: 18px;
  line-height: 1.72;
  color: var(--muted);
  margin: 0;
}
.article-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 21px;
  font-size: 13px;
  color: var(--muted);
}
.article-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 17px;
}
.article-tags .tag {
  padding: 6px 9px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 12px;
  color: var(--muted);
}
.article-head {
  padding-bottom: 28px;
  border-bottom: 1px solid var(--line);
}

/* Stage 3: 阅读画布(原型:38px 顶距,68px 底距) */
.reading-canvas {
  padding: 38px 0 68px;
}

/* Stage 4: 结尾 */
.article-end {
  padding-top: 10px;
}
.maintenance {
  border-top: 1px solid var(--line);
  padding-top: 28px;
  margin-top: 20px;
}
.maintenance h3 {
  font-size: 18px;
  margin: 0 0 8px;
  color: var(--text);
}
.maintenance p {
  font-size: 14px;
  color: var(--muted);
  line-height: 1.7;
  margin: 0;
}
.maintenance-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 15px;
  font-size: 12px;
  color: var(--muted);
}
.article-nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 28px;
}
.article-nav a {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  padding: 16px;
}
.article-nav a:hover {
  border-color: var(--line-strong);
}
.article-nav small {
  font-size: 11px;
  color: var(--muted);
}
.article-nav b {
  display: block;
  font-size: 14px;
  margin-top: 6px;
  color: var(--text);
}
@media (max-width: 650px) {
  .article-nav { grid-template-columns: 1fr; }
}

/* 主列防护:防 grid/flex 子项溢出(旧布局遗留的唯一有效规则) */
.article-main {
  min-width: 0;
}
</style>