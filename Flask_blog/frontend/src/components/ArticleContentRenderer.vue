<template>
  <div class="content-renderer-container">
    <!-- 开发模式下的内容类型指示器 -->
    <div v-if="showDebugInfo && isDevelopment" class="content-type-indicator">
      <div class="indicator-main">
        <el-tag 
          :type="contentAnalysis.type === 'html_source' ? 'warning' : 'success'" 
          size="small"
          effect="light"
        >
          {{ contentAnalysis.type === 'html_source' ? 'HTML源码内容' : 'Markdown内容' }}
        </el-tag>
        <span class="confidence-score">
          置信度: {{ Math.round(contentAnalysis.confidence * 100) }}%
        </span>
      </div>
      
      <!-- 详细特征信息 -->
      <div v-if="contentAnalysis.features" class="feature-details">
        <template v-if="contentAnalysis.type === 'html_source'">
          <span class="feature-item">HTML标签: {{ contentAnalysis.features.htmlTagCount }}</span>
          <span class="feature-item">内联样式: {{ contentAnalysis.features.inlineStyleCount }}</span>
          <span class="feature-item">HTML密度: {{ contentAnalysis.features.htmlDensity }}</span>
          <span v-if="contentAnalysis.features.estimatedPreservationNeeded" class="feature-item preservation-needed">
            需要样式保护
          </span>
        </template>
        <template v-else>
          <span class="feature-item">Markdown特征: {{ contentAnalysis.features.markdownPatterns }}</span>
        </template>
      </div>
    </div>
    
    <!-- Markdown内容渲染器 -->
    <div 
      v-if="contentAnalysis.type === 'markdown'"
      class="markdown-content-renderer"
      :class="{ 'content-loading': isProcessing }"
    >
      <div 
        class="article-body markdown-content"
        v-html="sanitizedContent"
        @click="handleContentClick"
      ></div>
    </div>
    
    <!-- HTML源码内容渲染器 -->
    <div 
      v-else-if="contentAnalysis.type === 'html_source'"
      class="html-content-renderer"
      :class="{ 'content-loading': isProcessing }"
    >
      <div 
        class="html-content-isolated"
        :class="getHTMLContentClasses()"
        v-html="sanitizedContent"
        @click="handleContentClick"
      ></div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isProcessing" class="content-processing-overlay">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在处理内容...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-if="hasError" class="content-error-state">
      <el-alert
        title="内容渲染错误"
        :description="errorMessage"
        type="error"
        show-icon
        :closable="false"
      />
      <div class="error-actions">
        <el-button size="small" @click="retryRender">重试渲染</el-button>
        <el-button size="small" type="info" @click="showRawContent = !showRawContent">
          {{ showRawContent ? '隐藏' : '显示' }}原始内容
        </el-button>
      </div>
      <div v-if="showRawContent" class="raw-content">
        <pre>{{ rawContent }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';
import DOMPurify from 'dompurify';

import { ContentTypeDetector } from '@/utils/contentTypeDetector.js';

// Props定义
const props = defineProps({
  content: {
    type: String,
    required: true,
    default: ''
  },
  showDebugInfo: {
    type: Boolean,
    default: false
  },
  enableSanitization: {
    type: Boolean,
    default: true
  },
  sanitizationOptions: {
    type: Object,
    default: () => ({
      ALLOWED_TAGS: [
        'div', 'p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
        'strong', 'em', 'u', 's', 'mark', 'small', 'del', 'ins',
        'code', 'pre', 'blockquote', 'cite', 'q',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'a', 'img', 'figure', 'figcaption',
        'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'caption',
        'br', 'hr', 'wbr',
        'details', 'summary',
        'section', 'article', 'aside', 'nav', 'header', 'footer', 'main'
      ],
      ALLOWED_ATTR: [
        'style', 'class', 'id', 'title', 'alt', 'src', 'href', 'target', 'rel',
        'width', 'height', 'border', 'cellpadding', 'cellspacing',
        'colspan', 'rowspan', 'scope', 'headers',
        'data-*', 'aria-*', 'role'
      ],
      ALLOW_DATA_ATTR: true,
      ALLOW_ARIA_ATTR: true,
      KEEP_CONTENT: true
    })
  },
  onContentTypeDetected: {
    type: Function,
    default: null
  }
});

// Emits定义
const emit = defineEmits([
  'content-rendered',
  'content-error',
  'content-type-detected',
  'content-click'
]);

// 响应式数据
const isProcessing = ref(false);
const hasError = ref(false);
const errorMessage = ref('');
const showRawContent = ref(false);
const rawContent = ref('');

// 计算属性
const isDevelopment = computed(() => {
  return process.env.NODE_ENV === 'development' || import.meta.env.DEV;
});

// 内容分析
const contentAnalysis = computed(() => {
  if (!props.content) {
    return { type: 'markdown', confidence: 1.0, features: {} };
  }
  
  try {
    const analysis = ContentTypeDetector.analyzeContent(props.content);
    
    // 通知父组件内容类型检测结果
    if (props.onContentTypeDetected) {
      nextTick(() => {
        props.onContentTypeDetected(analysis);
      });
    }
    
    emit('content-type-detected', analysis);
    
    return analysis;
  } catch (error) {
    console.error('ContentRenderer: 内容类型检测失败', error);
    return { type: 'markdown', confidence: 0.5, features: {} };
  }
});

// 内容安全处理
const sanitizedContent = computed(() => {
  if (!props.content) return '';
  
  try {
    if (!props.enableSanitization) {
      return props.content;
    }
    
    // 配置DOMPurify选项
    const purifyOptions = {
      ...props.sanitizationOptions,
      // 为HTML源码内容添加额外配置
      ...(contentAnalysis.value.type === 'html_source' ? {
        // 保持更多HTML特性用于样式保护
        ADD_TAGS: ['mark', 'details', 'summary'],
        ADD_ATTR: ['open']
      } : {})
    };
    
    // 使用DOMPurify清理内容
    const cleaned = DOMPurify.sanitize(props.content, purifyOptions);
    
    // 验证清理结果
    if (cleaned !== props.content) {
      console.log('ContentRenderer: 内容已被清理', {
        original: props.content.length,
        cleaned: cleaned.length,
        type: contentAnalysis.value.type
      });
    }
    
    return cleaned;
    
  } catch (error) {
    console.error('ContentRenderer: 内容清理失败', error);
    hasError.value = true;
    errorMessage.value = '内容安全处理失败: ' + error.message;
    return '';
  }
});

// HTML内容的CSS类计算
const getHTMLContentClasses = () => {
  const classes = [];
  
  if (contentAnalysis.value.features?.estimatedPreservationNeeded) {
    classes.push('preserve-inline-styles');
  }
  
  if (contentAnalysis.value.features?.specialFeatures?.hasTableStructure) {
    classes.push('has-table-structure');
  }
  
  if (contentAnalysis.value.features?.specialFeatures?.hasMediaElements) {
    classes.push('has-media-elements');
  }
  
  return classes;
};

// 内容点击处理
const handleContentClick = (event) => {
  emit('content-click', {
    event,
    contentType: contentAnalysis.value.type,
    target: event.target
  });
  
  // 处理链接点击
  if (event.target.tagName === 'A') {
    const href = event.target.getAttribute('href');
    if (href && href.startsWith('#')) {
      // 内部锚点链接处理
      event.preventDefault();
      const target = document.getElementById(href.substring(1));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }
};

// 重试渲染
const retryRender = async () => {
  hasError.value = false;
  errorMessage.value = '';
  isProcessing.value = true;
  
  try {
    await nextTick();
    // 触发重新计算
    emit('content-rendered', {
      contentType: contentAnalysis.value.type,
      success: true
    });
  } catch (error) {
    hasError.value = true;
    errorMessage.value = error.message;
    emit('content-error', error);
  } finally {
    isProcessing.value = false;
  }
};

// 监听内容变化
watch(() => props.content, (newContent, oldContent) => {
  if (newContent !== oldContent) {
    hasError.value = false;
    errorMessage.value = '';
    rawContent.value = newContent;
    
    if (newContent) {
      isProcessing.value = true;
      nextTick(() => {
        isProcessing.value = false;
        emit('content-rendered', {
          contentType: contentAnalysis.value.type,
          contentLength: newContent.length,
          success: true
        });
      });
    }
  }
}, { immediate: true });

// 组件挂载
onMounted(() => {
  rawContent.value = props.content;
  
  // 性能监控
  if (isDevelopment.value && props.content) {
    console.log('ContentRenderer mounted:', {
      contentLength: props.content.length,
      contentType: contentAnalysis.value.type,
      confidence: contentAnalysis.value.confidence,
      features: contentAnalysis.value.features
    });
  }
});

// 暴露方法给父组件
defineExpose({
  getContentAnalysis: () => contentAnalysis.value,
  getSanitizedContent: () => sanitizedContent.value,
  retryRender,
  toggleDebugInfo: () => {
    // 可以被父组件调用来切换调试信息显示
    emit('debug-info-toggle');
  }
});
</script>

<style scoped>
/* 容器样式 */
.content-renderer-container {
  position: relative;
  width: 100%;
}

/* 内容类型指示器 */
.content-type-indicator {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 1px solid #dee2e6;
  border-radius: 8px;
  font-size: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.indicator-main {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.confidence-score {
  font-weight: 600;
  color: #495057;
  background: rgba(255, 255, 255, 0.8);
  padding: 2px 8px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.feature-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.feature-item {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  font-size: 11px;
  color: #6c757d;
  font-weight: 500;
}

.feature-item.preservation-needed {
  background: rgba(255, 193, 7, 0.1);
  border-color: rgba(255, 193, 7, 0.3);
  color: #856404;
}

/* 渲染器容器 */
.markdown-content-renderer,
.html-content-renderer {
  position: relative;
  transition: all 0.3s ease;
}

.content-loading {
  opacity: 0.7;
  pointer-events: none;
}

/* 加载状态覆盖层 */
.content-processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #6c757d;
  font-size: 14px;
  z-index: 10;
  border-radius: 4px;
}

.content-processing-overlay .el-icon {
  font-size: 24px;
  color: #409eff;
}

/* 错误状态 */
.content-error-state {
  margin: 16px 0;
}

.error-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.raw-content {
  margin-top: 12px;
  padding: 12px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.raw-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* HTML内容隔离样式 - 新策略：最小干预 + 层叠上下文隔离 */
.html-content-isolated {
  /* 创建新的层叠上下文，隔离样式影响 */
  contain: layout style;
  isolation: isolate;
  
  /* 基础重置，不影响子元素 */
  margin: 0;
  padding: 0;
  
  /* 确保响应式和可访问性 */
  box-sizing: border-box;
  max-width: 100%;
  word-wrap: break-word;
}

/* 关键策略：不对子元素做任何样式重置，让内联样式自然生效 */
/* 内联样式优先级 = 1000，我们不与之竞争 */

/* 表格结构优化 */
.html-content-isolated.has-table-structure {
  overflow-x: auto;
}

/* 多媒体内容优化 */
.html-content-isolated.has-media-elements img,
.html-content-isolated.has-media-elements video {
  max-width: 100%;
  height: auto;
}

/* 保持极简的子元素样式 */
.html-content-isolated * {
  /* 只确保盒模型一致性 */
  box-sizing: border-box;
}

/* 最小化干预，只在必要时覆盖样式 */

/* 确保图片响应式 */
.html-content-isolated img {
  max-width: 100%;
  height: auto;
}

/* 确保表格可滚动 */
.html-content-isolated table {
  max-width: 100%;
  overflow-x: auto;
}

/* 防止代码块溢出 */
.html-content-isolated pre {
  overflow-x: auto;
  max-width: 100%;
}

/* 只有在没有内联样式时才应用基础样式 */
.html-content-isolated a:not([style]) {
  color: #0066cc;
  text-decoration: underline;
}

.html-content-isolated a:not([style]):hover {
  text-decoration: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .content-type-indicator {
    padding: 8px 12px;
    font-size: 11px;
  }
  
  .feature-details {
    gap: 4px;
  }
  
  .feature-item {
    font-size: 10px;
    padding: 1px 6px;
  }
  
  .html-content-isolated {
    font-size: 15px;
  }
  
  .html-content-isolated table,
  .html-content-isolated pre {
    font-size: 13px;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .content-type-indicator {
    background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
    border-color: #4a5568;
    color: #e2e8f0;
  }
  
  .confidence-score {
    background: rgba(0, 0, 0, 0.3);
    color: #e2e8f0;
    border-color: rgba(255, 255, 255, 0.2);
  }
  
  .feature-item {
    background: rgba(0, 0, 0, 0.2);
    border-color: rgba(255, 255, 255, 0.2);
    color: #cbd5e0;
  }
}
</style>