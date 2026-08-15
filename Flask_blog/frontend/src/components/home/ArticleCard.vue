<template>
  <article class="article-card article-card-body bg-slate-50 rounded-3xl shadow-sm hover:shadow-xl transition-all duration-300 group">
    <!-- 封面图片（顶部） - 优化的嵌入样式 -->
    <div class="cover-image-container">
      <RouterLink :to="'/article/' + article.slug">
        <div class="aspect-[16/9] bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 relative cover-image-wrapper">
          <CoverImage 
            :src="article.featured_image || getDefaultCoverImage(article)" 
            :alt="article.title" 
            container-class="absolute inset-0 overflow-hidden"
            image-class="w-full h-full object-cover group-hover:scale-105 transition-all duration-500"
            style="border-radius: 24px;"
          />
          <!-- 渐变遮罩 -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent" style="border-radius: 24px;" />
        </div>
      </RouterLink>
    </div>

    <!-- 主要内容区域 -->
    <div>
      <!-- 文章标题 -->
      <RouterLink 
        :to="'/article/' + article.slug"
        class="block group-hover:text-blue-600 transition-colors duration-200 text-center"
      >
        <h3 class="text-xl font-bold text-gray-900 leading-tight mb-4 line-clamp-2 hover:text-blue-600 transition-colors">
          {{ article.title }}
        </h3>
      </RouterLink>

      <!-- 文章元信息 -->
      <div class="post-meta text-sm text-gray-500 mb-4 text-center">
        <!-- 第一行：基础信息 -->
        <div class="flex items-center flex-wrap mb-1 justify-center">
          <!-- 发布时间 -->
          <div class="post-meta-item">
            <i class="fa fa-clock-o" aria-hidden="true" />
            {{ formatDate(article.published_at) }}
          </div>
          
          <div class="post-meta-divider">|</div>
          
          <!-- 浏览次数 -->
          <div v-if="article.views_count != null" class="post-meta-item">
            <i class="fa fa-eye" aria-hidden="true" />
            {{ formatNumber(article.views_count) }}
          </div>
          
          <div v-if="article.views_count != null" class="post-meta-divider">|</div>
          
          <!-- 评论数 -->
          <div class="post-meta-item">
            <i class="fa fa-comments-o" aria-hidden="true" />
            {{ article.comments_count || 0 }}
          </div>
          
          <div class="post-meta-divider">|</div>
          
          <!-- 文章分类 -->
          <div v-if="article.category" class="post-meta-item">
            <i class="fa fa-bookmark-o" aria-hidden="true" />
            <span class="text-blue-600 hover:text-blue-800 transition-colors cursor-pointer" @click="$emit('category-click', article.category_id)">
              {{ article.category }}
            </span>
          </div>
          
          <div v-if="article.category" class="post-meta-divider">|</div>
          
          <!-- 最后编辑时间 -->
          <div v-if="article.updated_at && article.updated_at !== article.published_at" class="post-meta-item">
            <i class="fa fa-clock-o" aria-hidden="true" />
            {{ formatDate(article.updated_at) }}
          </div>
          
          <div v-if="article.updated_at && article.updated_at !== article.published_at" class="post-meta-divider">|</div>
          
          <!-- 文章作者 -->
          <div class="post-meta-item">
            <i class="fa fa-user-circle-o" aria-hidden="true" />
            {{ article.author?.name || '匿名作者' }}
          </div>
        </div>
          
        <!-- 第二行：字数和阅读时间 -->
        <div class="flex items-center justify-center">
          <!-- 字数统计 -->
          <div class="post-meta-item">
            <i class="fa fa-file-word-o" aria-hidden="true" />
            {{ calculateWordCount(article.content_md || article.summary || '') }} 字
          </div>
          
          <div class="post-meta-divider">|</div>
          
          <!-- 预计阅读时间 -->
          <div class="post-meta-item">
            <i class="fa fa-hourglass-end" aria-hidden="true" />
            {{ calculateReadTime(article.content_md || article.summary || '') }} 分钟
          </div>
        </div>
      </div>

      <!-- 文章摘要 -->
      <p class="text-gray-600 leading-relaxed mb-4 line-clamp-3">
        {{ getArticleSummary(article) }}
      </p>

      <!-- 底部操作区域 -->
      <div class="flex flex-col gap-4">
        <!-- 标签区域 -->
        <div v-if="Array.isArray(article.tags) && article.tags.length" class="flex items-center gap-2 flex-wrap justify-center">
          <el-tag 
            v-for="t in article.tags.slice(0, 3)" 
            :key="t" 
            size="small" 
            type="info"
            class="cursor-pointer hover:bg-gray-200 transition-colors"
            @click="$emit('tag-click', t)"
          >
            #{{ t }}
          </el-tag>
          <span v-if="article.tags.length > 3" class="text-xs text-gray-400">+{{ article.tags.length - 3 }}</span>
        </div>
          
        <!-- 互动按钮 - 移除分割线和边距 -->
        <div class="interaction-buttons-container">
          <!-- 点赞按钮 -->
          <button 
            :class="[
              'interaction-btn',
              article.is_liked ? 'liked' : ''
            ]"
            :disabled="likingIds.includes(article.id)"
            :title="article.is_liked ? '取消点赞' : '点赞'"
            @click="toggleLike(article)"
          >
            <i :class="article.is_liked ? 'fa fa-heart' : 'fa fa-heart-o'" aria-hidden="true" />
            <span>{{ formatNumber(article.likes_count || 0) }}</span>
          </button>
            
          <!-- 收藏按钮 -->
          <button 
            :class="[
              'interaction-btn',
              article.is_bookmarked ? 'bookmarked' : ''
            ]"
            :disabled="bookmarkingIds.includes(article.id)"
            :title="article.is_bookmarked ? '取消收藏' : '收藏文章'"
            @click="toggleBookmark(article)"
          >
            <i :class="article.is_bookmarked ? 'fa fa-bookmark' : 'fa fa-bookmark-o'" aria-hidden="true" />
            <span>收藏</span>
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import CoverImage from '../CoverImage.vue';

defineProps({
  article: {
    type: /** @type {import('vue').PropType<import('@/types').Article>} */ (Object),
    required: true
  }
});

defineEmits(['category-click', 'tag-click']);

// 点赞 / 收藏操作中的进行中状态
/** @type {import('vue').Ref<number[]>} */
const likingIds = ref([]);
/** @type {import('vue').Ref<number[]>} */
const bookmarkingIds = ref([]);

// 工具函数
/** @param {string | null | undefined} s */
function formatDate(s) { 
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

/** @param {number | undefined} num */
function formatNumber(num) {
  if (num == null) num = 0;
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return String(num);
}

// 计算文章字数
/** @param {string} content */
function calculateWordCount(content) {
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
/** @param {string} content */
function calculateReadTime(content) {
  const wordCount = calculateWordCount(content);
  // 假设平均阅读速度：中文 300 字/分钟，英文 250 词/分钟
  const readTime = Math.max(1, Math.ceil(wordCount / 275));
  return readTime;
}

// 获取默认封面图片
/** @param {any} article */
function getDefaultCoverImage(article) {
  // 根据文章分类生成不同的默认封面 (16:9 比例)
  /** @type {Record<string, string>} */
  const categoryImages = {
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
/** @param {any} article */
function getArticleSummary(article) {
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

// 点赞功能
/** @param {any} article */
async function toggleLike(article) {
  if (likingIds.value.includes(article.id)) return;
  
  likingIds.value.push(article.id);
  const wasLiked = article.is_liked;
  const originalCount = article.likes_count || 0;
  
  // 乐观更新
  article.is_liked = !wasLiked;
  article.likes_count = wasLiked ? originalCount - 1 : originalCount + 1;
  
  try {
    await API.likeArticle(article.id);
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
/** @param {any} article */
async function toggleBookmark(article) {
  if (bookmarkingIds.value.includes(article.id)) return;
  
  bookmarkingIds.value.push(article.id);
  const wasBookmarked = article.is_bookmarked;
  
  // 乐观更新
  article.is_bookmarked = !wasBookmarked;
  
  try {
    await API.bookmarkArticle(article.id);
    ElMessage.success(article.is_bookmarked ? '收藏成功' : '取消收藏');
  } catch (error) {
    // 回滚
    article.is_bookmarked = wasBookmarked;
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    bookmarkingIds.value = bookmarkingIds.value.filter(id => id !== article.id);
  }
}
</script>

<style scoped>
.article-card-body { background-color: rgb(248 250 252); padding: 24px; }

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
</style>
