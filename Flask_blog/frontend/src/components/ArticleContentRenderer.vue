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
        v-html="processedContent"
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
        v-html="processedContent"
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
import { computed, ref, watch, nextTick, onMounted, onBeforeMount } from 'vue';
import { ElMessage } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';
import DOMPurify from 'dompurify';
import katex from 'katex';
import 'katex/dist/katex.min.css';

import { ContentTypeDetector } from '@/utils/contentTypeDetector.js';
import { renderMarkdown, preload, testProcessor, getProcessorStatus } from '@/utils/markdownProcessor.reliable.js';

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
        'section', 'article', 'aside', 'nav', 'header', 'footer', 'main',
        // MathML tags
        'math', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac',
        'munder', 'mover', 'munderover', 'msqrt', 'mroot', 'mspace',
        'mstyle', 'mtext', 'menclose', 'mpadded', 'mphantom',
        'annotation', 'semantics', 'mtable', 'mtr', 'mtd'
      ],
      ALLOWED_ATTR: [
        'style', 'class', 'id', 'title', 'alt', 'src', 'href', 'target', 'rel',
        'width', 'height', 'border', 'cellpadding', 'cellspacing',
        'colspan', 'rowspan', 'scope', 'headers',
        'data-*', 'aria-*', 'role',
        // MathML and KaTeX specific attributes
        'xmlns', 'display', 'mathvariant', 'mathsize', 'mathcolor', 'mathbackground',
        'scriptlevel', 'displaystyle', 'scriptsizemultiplier', 'scriptminsize',
        'color', 'background-color', 'font-family', 'font-size', 'font-style', 'font-weight'
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

// 新的内容渲染处理逻辑 - 优先处理数学公式
const processContent = async (content, type) => {
  if (!content) return '';
  
  try {
    // 优先策略：检查是否包含数学公式标记
    const hasMathFormulas = content.includes('$') || content.includes('\\(') || content.includes('\\[');
    
    console.log('🔍 Content processing pipeline started:', {
      contentLength: content.length,
      contentType: type,
      hasMathFormulas: hasMathFormulas,
      firstChars: content.substring(0, 100),
      mathIndicators: {
        dollars: content.includes('$'),
        parentheses: content.includes('\\('),
        brackets: content.includes('\\[')
      }
    });
    
    if (type === 'markdown' || hasMathFormulas) {
      // 使用Markdown处理器，自动处理数学公式和代码高亮
      console.log('🧮 Processing with Markdown renderer (math formulas detected)');
      const markdownResult = await renderMarkdown(content);
      
      console.log('🧮 Markdown processing completed:', {
        inputLength: content.length,
        outputLength: markdownResult.length,
        containsKaTeX: markdownResult.includes('katex'),
        containsMathML: markdownResult.includes('<math>'),
        containsMathClass: markdownResult.includes('math-'),
        containsSpanKatex: markdownResult.includes('<span class="katex">'),
        firstOutputChars: markdownResult.substring(0, 200)
      });
      
      // 检查是否需要额外处理
      if (hasMathFormulas && !markdownResult.includes('katex')) {
        console.warn('⚠️ Math formulas detected in input but no KaTeX output found! Attempting client-side KaTeX fallback.');
        console.log('Input sample:', content.substring(0, 200));
        console.log('Output sample (before fallback):', markdownResult.substring(0, 200));

        try {
          const fallback = renderMathWithKatex(markdownResult);
          console.log('✅ Client-side KaTeX fallback applied');
          return fallback;
        } catch (e) {
          console.error('Client-side KaTeX fallback failed:', e);
          // 返回原始结果（保持最低破坏性）
          return markdownResult;
        }
      }

      // 检查Shiki代码高亮是否被意外清理
      const hasOriginalColors = markdownResult.includes('<span style="color:');
      console.log('🎨 Markdown渲染结果检查:', {
        hasShikiClass: markdownResult.includes('shiki'),
        hasColorSpans: hasOriginalColors,
        originalLength: markdownResult.length
      });

      return markdownResult;
    } else {
      // 纯HTML内容，只进行安全清理
      console.log('🧹 Processing with DOMPurify only (no math formulas)');
      const purifiedResult = DOMPurify.sanitize(content, props.sanitizationOptions);
      
      console.log('🧹 DOMPurify processing completed:', {
        inputLength: content.length,
        outputLength: purifiedResult.length,
        containsKaTeX: purifiedResult.includes('katex'),
        stripped: content.length - purifiedResult.length
      });
      
      return purifiedResult;
    }
  } catch (error) {
    console.error('Content processing error:', error);
    return `<div class="content-processing-error">
      <p>⚠️ 内容处理失败: ${error.message}</p>
      <pre>${content}</pre>
    </div>`;
  }
};

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

// 响应式的处理后内容
const processedContent = ref('');

// 异步处理内容的函数
const renderContent = async () => {
  if (!props.content) {
    processedContent.value = '';
    return;
  }
  
  isProcessing.value = true;
  hasError.value = false;
  errorMessage.value = '';
  
  try {
    let result;
    
    if (!props.enableSanitization) {
      // 如果不启用安全处理，直接使用原内容
      result = props.content;
    } else {
      // 使用新的统一处理器
      result = await processContent(props.content, contentAnalysis.value.type);
    }
    
    processedContent.value = result;
    
    // 调试：检查最终结果是否保留了颜色信息
    const finalHasColors = result.includes('<span style="color:');
    console.log('🔍 最终渲染结果检查:', {
      finalLength: result.length,
      hasShikiClass: result.includes('shiki'),
      hasColorSpans: finalHasColors,
      firstColorSpan: finalHasColors ? result.match(/<span style="color:[^"]+"/)?.[0] : 'none',
      sampleOutput: result.substring(0, 300) + '...'
    });
    
    // 通知父组件渲染完成
    emit('content-rendered', {
      contentType: contentAnalysis.value.type,
      contentLength: result.length,
      success: true
    });
    
  } catch (error) {
    console.error('ContentRenderer: 内容渲染失败', error);
    hasError.value = true;
    errorMessage.value = '内容渲染失败: ' + error.message;
    processedContent.value = '';
    
    emit('content-error', error);
  } finally {
    isProcessing.value = false;
  }
};

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
  await renderContent();
};

// 预加载highlighter
onBeforeMount(async () => {
  try {
    console.log('🚀 开始预加载Markdown处理器...')
    await preload();
    
    // 获取处理器状态
    const status = getProcessorStatus()
    console.log('📊 处理器状态:', status)
    
    // 运行快速测试
    console.log('🧪 运行处理器测试...')
    const testResult = await testProcessor()
    
    if (testResult) {
      // 检查测试结果中是否有代码高亮
      const hasHighlighting = testResult.includes('shiki') || testResult.includes('<span style="color:')
      console.log('🔍 测试结果分析:', {
        hasResult: !!testResult,
        length: testResult.length,
        hasHighlighting,
        hasCodeBlocks: testResult.includes('<pre'),
        sample: testResult.substring(0, 200) + '...'
      })
    }
    
    console.log('✅ Markdown处理器预加载和测试完成')
  } catch (error) {
    console.error('❌ 预加载失败:', error);
  }
});

// 监听内容变化
watch(() => props.content, async (newContent, oldContent) => {
  if (newContent !== oldContent) {
    rawContent.value = newContent;
    await renderContent();
  }
}, { immediate: true });

// 监听内容类型变化
watch(() => contentAnalysis.value.type, async () => {
  if (props.content) {
    await renderContent();
  }
});

// 组件挂载
onMounted(async () => {
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
  
  // 确保内容被渲染
  if (props.content && !processedContent.value) {
    await renderContent();
  }

  // 开发环境下自动运行样式检查
  if (isDevelopment.value && typeof window !== 'undefined') {
    try {
      // 检查KaTeX样式
      // 检查页面上的代码块元素
      setTimeout(() => {
        const codeBlocks = document.querySelectorAll('.article-content pre');
        console.log('🔍 页面上的代码块数量:', codeBlocks.length);
        
        codeBlocks.forEach((block, index) => {
          const hasShikiClass = block.classList.contains('shiki');
          const hasInlineStyles = block.style.length > 0;
          const hasColorSpans = block.querySelectorAll('span[style*="color"]').length;
          const allSpans = block.querySelectorAll('span').length;
          
          console.log(`📋 代码块 ${index + 1}:`, {
            tagName: block.tagName,
            classes: Array.from(block.classList),
            hasShikiClass,
            hasInlineStyles,
            hasColorSpans,
            totalSpans: allSpans,
            innerHTML: block.innerHTML.substring(0, 200) + '...'
          });
          
          // 如果有Shiki类但没有颜色，进行深入分析
          if (hasShikiClass && hasColorSpans === 0 && allSpans > 0) {
            console.warn('🚨 Shiki代码块没有颜色！分析HTML结构:');
            console.log('完整innerHTML:', block.innerHTML);
            
            // 尝试手动添加一个测试span看是否被过滤
            const testSpan = document.createElement('span');
            testSpan.style.color = 'red';
            testSpan.textContent = 'TEST';
            block.appendChild(testSpan);
            
            setTimeout(() => {
              const testExists = block.contains(testSpan);
              const testHasColor = testSpan.style.color === 'red';
              console.log('🧪 测试span结果:', {
                exists: testExists,
                hasColor: testHasColor,
                actualColor: testSpan.style.color
              });
            }, 100);
          }
        });
      }, 1000);
      
    } catch (e) {
      console.warn('Style check failed:', e);
    }
  }
});

// 暴露方法给父组件
defineExpose({
  getContentAnalysis: () => contentAnalysis.value,
  getProcessedContent: () => processedContent.value,
  retryRender,
  renderContent,
  toggleDebugInfo: () => {
    // 可以被父组件调用来切换调试信息显示
    emit('debug-info-toggle');
  }
});

/**
 * 将渲染后的 HTML 中的 $$...$$ 和 $...$ 用 KaTeX 在客户端渲染为 HTML
 * 仅在 markdown-it-katex 未生成 KaTeX HTML 时作为回退策略
 */
function renderMathWithKatex(html) {
  if (!html) return html;

  // 先处理块级公式 $$...$$，使用非贪婪匹配
  html = html.replace(/\$\$([\s\S]+?)\$\$/g, (match, tex) => {
    try {
      return katex.renderToString(tex, { displayMode: true, throwOnError: false });
    } catch (e) {
      console.warn('KaTeX render error for display math:', e);
      return match;
    }
  });

  // 再处理行内公式 $...$，但要避免替换已经在 HTML 标签内的美元符号
  // 简单策略：对剩余文本进行替换（可能不是完美解决方案，但适合大多数用例）
  html = html.replace(/\$(.+?)\$/g, (match, tex) => {
    // 略过包含空格首尾过多的匹配，减少误替换
    if (!tex || tex.trim().length === 0) return match;
    try {
      return katex.renderToString(tex, { displayMode: false, throwOnError: false });
    } catch (e) {
      console.warn('KaTeX render error for inline math:', e);
      return match;
    }
  });

  return html;
}
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

/* KaTeX数学公式样式 */
.math-display {
  margin: 1.2em 0;
  text-align: center;
  overflow-x: auto;
  padding: 0.5em 0;
}

.math-error {
  color: #cc0000;
  background-color: rgba(255, 204, 204, 0.2);
  border: 1px solid #cc0000;
  border-radius: 4px;
  padding: 2px 6px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  cursor: help;
  display: inline-block;
}

/* KaTeX响应式样式优化 */
.katex-display {
  margin: 1.2em 0;
  text-align: center;
  overflow-x: auto;
}

.katex {
  font-size: 1.1em;
  line-height: 1.4;
}

/* Shiki代码高亮样式 */
.shiki {
  border-radius: 6px;
  padding: 0.8em 1em;
  margin: 1em 0;
  overflow-x: auto;
  border: 1px solid #e1e4e8;
  font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  line-height: 1.45;
  position: relative;
}

/* 确保Shiki生成的pre标签样式正确 */
:deep(pre.shiki) {
  background: #ffffff !important; /* 确保有背景色 */
  margin: 1em 0 !important;
  padding: 0.8em 1em !important;
  border-radius: 6px !important;
  overflow-x: auto !important;
  border: 1px solid #e1e4e8 !important;
  font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace !important;
  font-size: 0.9em !important;
  line-height: 1.45 !important;
}

/* 确保Shiki的内联样式不被覆盖 */
:deep(pre.shiki span) {
  font-family: inherit !important;
}

/* 确保所有带有color样式的span都显示颜色 */
:deep(span[style*="color"]) {
  /* 不覆盖内联样式，让颜色正常显示 */
}

/* 代码块内的代码文本样式 */
.shiki code {
  background: transparent !important;
  color: inherit !important;
  font-family: inherit !important;
}

/* 基础代码块样式（Shiki失败时的降级） */
:deep(.basic-code-block) {
  background-color: #f6f8fa !important;
  border-radius: 6px !important;
  padding: 0.8em 1em !important;
  margin: 1em 0 !important;
  overflow-x: auto !important;
  border: 1px solid #e1e4e8 !important;
  font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace !important;
  font-size: 0.9em !important;
  line-height: 1.45 !important;
}

:deep(.basic-code-block code) {
  background: transparent !important;
  color: #24292e !important;
  font-family: inherit !important;
}

/* 降级代码块样式 */
.fallback-code-block {
  background-color: #fdf6e3;
  border-radius: 6px;
  padding: 0.8em 1em;
  margin: 1em 0;
  overflow-x: auto;
  border: 1px solid #eee8d5;
  font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  line-height: 1.45;
}

.fallback-code-block code {
  background: transparent;
  color: #657b83;
  font-family: inherit;
}


.shiki-line-numbers {
  counter-reset: line-number;
}

.shiki-line-numbers .line::before {
  counter-increment: line-number;
  content: counter(line-number);
  display: inline-block;
  width: 2em;
  text-align: right;
  margin-right: 1em;
  color: #999;
  user-select: none;
}

/* 表格样式（支持新的table-wrapper类） */
.table-wrapper,
.markdown-table-wrapper {
  overflow-x: auto;
  margin: 1em 0;
  border-radius: 6px;
  border: 1px solid #e1e4e8;
  background: white;
}

.table-wrapper table,
.markdown-table-wrapper table {
  width: 100%;
  border-collapse: collapse;
  margin: 0;
  background: white;
}

.table-wrapper th,
.table-wrapper td,
.markdown-table-wrapper th,
.markdown-table-wrapper td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #e1e4e8;
}

.table-wrapper th,
.markdown-table-wrapper th {
  background-color: #f6f8fa;
  font-weight: 600;
  border-bottom: 2px solid #e1e4e8;
}

.table-wrapper tr:last-child td,
.markdown-table-wrapper tr:last-child td {
  border-bottom: none;
}

/* Markdown图片优化 */
.markdown-image {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin: 1em 0;
}

/* 内容处理错误样式 */
.content-processing-error {
  background-color: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 6px;
  padding: 1em;
  margin: 1em 0;
  color: #c53030;
}

.content-processing-error p {
  margin: 0 0 0.5em 0;
  font-weight: 600;
}

.content-processing-error pre {
  background-color: #f7fafc;
  padding: 0.5em;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85em;
  margin: 0;
}

/* 锚点链接样式 */
.header-anchor {
  color: #1e90ff;
  text-decoration: none;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.header-anchor:hover {
  opacity: 1;
  text-decoration: underline;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .math-display {
    margin: 0.8em 0;
    padding: 0.3em 0;
    font-size: 0.9em;
  }
  
  .katex {
    font-size: 1em;
  }
  
  .katex-display {
    margin: 0.8em 0;
  }
  
  /* 长公式水平滚动 */
  .math-display,
  .katex-display {
    overflow-x: auto;
    overflow-y: hidden;
    max-width: 100%;
  }
  
  .shiki {
    padding: 0.6em 0.8em;
    font-size: 0.85em;
    margin: 0.8em 0;
  }
  
  .markdown-table-wrapper {
    font-size: 0.9em;
  }
  
  .markdown-table-wrapper th,
  .markdown-table-wrapper td {
    padding: 6px 8px;
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
  
  /* 暗色模式下的数学公式错误样式 */
  .math-error {
    color: #ff6b6b;
    background-color: rgba(255, 107, 107, 0.1);
    border-color: #ff6b6b;
  }
}
</style>