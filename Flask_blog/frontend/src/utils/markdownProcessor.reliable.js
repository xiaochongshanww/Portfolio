/**
 * 可靠的Markdown处理器 - 专注于稳定性和功能完整性
 * 使用业界最佳实践，确保Shiki代码高亮和KaTeX数学公式都能正常工作
 */

import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'
import { createHighlighter } from 'shiki'

// 全局缓存
/** @type {any} */
let highlighterCache = null
/** @type {any} */
let mdCache = null

/**
 * 创建并缓存Shiki高亮器
 */
const createShikiHighlighter = async () => {
  if (highlighterCache) return highlighterCache
  
  try {
    
    // 使用最小化的语言集合，只包含确定支持的语言
    highlighterCache = await createHighlighter({
      themes: ['github-light', 'github-dark'],
      langs: [
        'javascript',
        'typescript', 
        'python',
        'html', 'css',
        'json', 'yaml',
        'bash', 'shell',
        'sql', 'php', 'java',
        'go', 'rust',
        'vue',
        'markdown',
        'text'
      ]
    })
    
    
    // 测试高亮器是否工作
    const testCode = 'const hello = "world";'
    const testResult = highlighterCache.codeToHtml(testCode, {
      lang: 'javascript',
      theme: 'github-light'
    })
    
    if (testResult && testResult.includes('<span')) {
    } else {
      console.warn('⚠️ Shiki高亮器测试失败，但继续使用')
    }
    
    return highlighterCache
  } catch (error) {
    console.error('❌ Shiki高亮器创建失败:', error)
    
    // 尝试使用最小配置重新创建
    try {
      highlighterCache = await createHighlighter({
        themes: ['github-light'],
        langs: ['javascript', 'python', 'html', 'css', 'json', 'text']
      })
      return highlighterCache
    } catch (fallbackError) {
      console.error('❌ 最小配置也失败:', fallbackError)
      highlighterCache = null
      return null
    }
  }
}

/**
 * 创建配置完整的MarkdownIt实例
 */
const createMarkdownProcessor = async () => {
  if (mdCache) return mdCache
  
  
  const md = MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    breaks: false
  })
  
  // 1. 配置KaTeX数学公式支持
  try {
    const katexPlugin = markdownItKatex.default || markdownItKatex
    md.use(katexPlugin, {
      throwOnError: false,
      errorColor: '#cc0000',
      strict: 'warn'
    })
  } catch (error) {
    console.error('❌ KaTeX插件加载失败:', error)
  }
  
  // 2. 配置Shiki代码高亮支持
  const highlighter = await createShikiHighlighter()
  
  if (highlighter) {
    // 自定义fence渲染规则 - 最简单可靠的方法
    md.renderer.rules.fence = function (
      /** @type {any[]} */ tokens,
      /** @type {number} */ idx,
      /** @type {any} */ _options,
      /** @type {any} */ _env,
      /** @type {any} */ _renderer
    ) {
      const token = tokens[idx]
      const code = token.content
      const info = /** @type {string} */ (token.info ? token.info.trim() : '')
      const langName = info.split(/\s+/g)[0]
      
      // 详细调试信息
      
      
      try {
        // 支持的语言映射
        /** @type {Record<string, string>} */
        const langMap = {
          'js': 'javascript',
          'ts': 'typescript',
          'py': 'python',
          'sh': 'bash',
          'yml': 'yaml',
          'jsx': 'javascript', // 将jsx映射到javascript
          'tsx': 'typescript',  // 将tsx映射到typescript
          'react': 'javascript', // 将react映射到javascript
          'node': 'javascript',  // 将node映射到javascript
        }
        
        const mappedLang = langMap[langName] || langName || 'text'
        
        // 如果没有语言信息，尝试从代码内容推断
        let finalLang = mappedLang;
        if (!langName || langName === 'text') {
          
          // Python特征检测
          const pythonPatterns = [
            /import\s+(numpy|pandas|matplotlib|sklearn|seaborn)/,
            /from\s+(sklearn|pandas|numpy)/,
            /def\s+\w+\(/,
            /#.*导入|#.*库/,
            /print\(/,
            /plt\./,
            /pd\./,
            /np\./,
            /\blen\(/,
            /:\s*$/m  // 行末有冒号
          ];
          
          // JavaScript特征检测
          const jsPatterns = [
            /function\s+\w+\(/,
            /const\s+\w+\s*=/,
            /let\s+\w+\s*=/,
            /var\s+\w+\s*=/,
            /console\.log/,
            /=>\s*{/
          ];
          
          // HTML特征检测
          const htmlPatterns = [
            /<[^>]+>/,
            /<!DOCTYPE/i,
            /<html/i,
            /<div/i,
            /<script/i
          ];
          
          if (pythonPatterns.some(pattern => pattern.test(code))) {
            finalLang = 'python';
          } else if (jsPatterns.some(pattern => pattern.test(code))) {
            finalLang = 'javascript';
          } else if (htmlPatterns.some(pattern => pattern.test(code))) {
            finalLang = 'html';
          } else {
            // 对于机器学习内容，大概率是Python
            finalLang = 'python';
          }
        }
        
        // 尝试不同的Shiki配置方法
        let html;
        
        // 使用正确的亮色主题
        
        html = highlighter.codeToHtml(code, {
          lang: finalLang,
          theme: 'github-light'
        })
        
        
        // 输出原始HTML用于调试
        
        // 强制设置正确的背景色和标识
        if (html.includes('<pre')) {
          const beforeModification = html.substring(0, 200)
          
          // 直接在style属性中强制设置背景色，优先级最高
          html = html.replace(
            /<pre([^>]*)style="([^"]*)"([^>]*)>/,
            '<pre$1style="$2; background-color: #f6f8fa !important;"$3 data-theme="github-light" class="shiki">'
          )
          
          // 如果没有style属性，添加一个
          if (!html.includes('style=')) {
            html = html.replace(
              '<pre',
              '<pre style="background-color: #f6f8fa !important;" data-theme="github-light" class="shiki"'
            )
          }
          
          const afterModification = html.substring(0, 200)
          
        }
        
        // 检查背景色情况
        const hasInlineBackground = html.includes('background-color')
        const backgroundColorMatch = html.match(/background-color:[^;\"]+/)
        
        
        
        
        return html
        
      } catch (error) {
        const err = /** @type {{ message?: string }} */ (error)
        console.warn(`⚠️ Shiki渲染失败 (${langName}):`, err.message)
        
        // 降级到基础代码块
        const escapedCode = md.utils.escapeHtml(code)
        return `<pre class="fallback-code-block"><code class="language-${md.utils.escapeHtml(langName || 'text')}">${escapedCode}</code></pre>`
      }
    }
    
  } else {
    console.warn('⚠️ 使用基础代码块渲染')
    
    // 基础代码块渲染
    md.renderer.rules.fence = function (
      /** @type {any[]} */ tokens,
      /** @type {number} */ idx,
      /** @type {any} */ _options,
      /** @type {any} */ _env,
      /** @type {any} */ _renderer
    ) {
      const token = tokens[idx]
      const code = token.content
      const info = /** @type {string} */ (token.info ? token.info.trim() : '')
      const langName = info.split(/\s+/g)[0]
      
      const escapedCode = md.utils.escapeHtml(code)
      return `<pre class="basic-code-block"><code class="language-${md.utils.escapeHtml(langName || 'text')}">${escapedCode}</code></pre>`
    }
  }
  
  // 3. 自定义图片渲染 - 添加响应式支持
  const defaultImageRenderer = md.renderer.rules.image || function(
    /** @type {any[]} */ tokens,
    /** @type {number} */ idx,
    /** @type {any} */ options,
    /** @type {any} */ env,
    /** @type {any} */ self
  ) {
    return self.renderToken(tokens, idx, options)
  }
  
  md.renderer.rules.image = function(
    /** @type {any[]} */ tokens,
    /** @type {number} */ idx,
    /** @type {any} */ options,
    /** @type {any} */ env,
    /** @type {any} */ self
  ) {
    const token = tokens[idx]
    token.attrPush(['loading', 'lazy'])
    token.attrPush(['class', 'markdown-image'])
    return defaultImageRenderer(tokens, idx, options, env, self)
  }
  
  // 4. 自定义表格渲染 - 添加响应式包装
  const defaultTableOpenRenderer = md.renderer.rules.table_open || function(
    /** @type {any[]} */ tokens,
    /** @type {number} */ idx,
    /** @type {any} */ options,
    /** @type {any} */ env,
    /** @type {any} */ self
  ) {
    return self.renderToken(tokens, idx, options)
  }
  
  md.renderer.rules.table_open = function(
    /** @type {any[]} */ tokens,
    /** @type {number} */ idx,
    /** @type {any} */ _options,
    /** @type {any} */ _env,
    /** @type {any} */ _self
  ) {
    return '<div class="table-wrapper">' + defaultTableOpenRenderer(tokens, idx, _options, _env, _self)
  }
  
  md.renderer.rules.table_close = function(
    /** @type {any[]} */ _tokens,
    /** @type {number} */ _idx,
    /** @type {any} */ _options,
    /** @type {any} */ _env,
    /** @type {any} */ _self
  ) {
    return '</table></div>'
  }
  
  mdCache = md
  return md
}

/**
 * 主要的Markdown渲染函数
 * @param {string} content
 * @returns {Promise<string>}
 */
export const renderMarkdown = async (content) => {
  if (!content || typeof content !== 'string') {
    return ''
  }
  
  // 分析代码块信息
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
  const codeBlocks = [];
  let match;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    codeBlocks.push({
      language: match[1] || 'none',
      content: match[2] ? match[2].substring(0, 50) + '...' : 'empty'
    });
  }
  
  
  
  try {
    const md = await createMarkdownProcessor()
    const result = /** @type {string} */ (md.render(content))
    
    // 更详细的结果分析
    const resultAnalysis = {
      inputLength: content.length,
      outputLength: result.length,
      hasKaTeX: result.includes('katex'),
      hasShikiCode: result.includes('shiki'),
      hasShikiSpans: result.includes('<span style="color:'),
      hasBasicCode: result.includes('basic-code-block'),
      hasFallbackCode: result.includes('fallback-code-block'),
      hasPreTags: result.includes('<pre'),
      hasCodeTags: result.includes('<code'),
      codeBlockCount: (result.match(/<pre/g) || []).length
    }
    
    
    // 如果有代码块但没有语法高亮，输出详细信息
    if (content.includes('```') && !resultAnalysis.hasShikiCode && !resultAnalysis.hasShikiSpans) {
      console.warn('🚨 检测到代码块但没有Shiki高亮效果!')
      
      // 提取前500字符的输出用于调试
      const outputSample = result.substring(0, 500)
      
      // 查找所有的代码块
      const codeMatches = result.match(/<pre[^>]*>.*?<\/pre>/gs)
      if (codeMatches) {
      }
    }
    
    return result
    
  } catch (error) {
    console.error('❌ Markdown渲染失败:', error)
    
    // 最低限度的降级处理
    return `<div class="markdown-error">
      <p>⚠️ 内容渲染失败</p>
      <pre>${content}</pre>
    </div>`
  }
}

/**
 * 预加载资源
 */
export const preload = async () => {
  
  try {
    await createMarkdownProcessor()
  } catch (error) {
    console.warn('⚠️ 预加载失败:', error)
  }
}

/**
 * 重置缓存（用于开发调试）
 */
export const resetCache = () => {
  highlighterCache = null
  mdCache = null
}

/**
 * 获取处理器状态信息
 */
export const getProcessorStatus = () => {
  return {
    highlighterLoaded: !!highlighterCache,
    processorCached: !!mdCache,
    timestamp: new Date().toISOString()
  }
}

/**
 * 测试函数 - 快速验证功能
 */
export const testProcessor = async () => {
  
  const testContent = `# 测试文档

这是一个测试文档，包含：

## 数学公式
行内公式：$E = mc^2$

块级公式：
$$\\sum_{i=1}^{n} x_i = \\frac{1}{n}\\sum_{i=1}^{n} x_i$$

## 代码块
\`\`\`javascript
const hello = "world";
\`\`\`

\`\`\`python
def hello():
    print("Hello, World!")
\`\`\`

\`\`\`html
<h1>Hello World</h1>
\`\`\`

测试完成！`

  try {
    const result = await renderMarkdown(testContent)
    
    return result
  } catch (error) {
    console.error('🧪 测试失败:', error)
    return null
  }
}

/**
 * 快速测试函数 - 在浏览器控制台中使用
 * @param {string} [testContent]
 * @returns {Promise<string | null>}
 */
export const quickTest = async (testContent) => {
  const content = testContent || `# 快速测试

这是一个测试：

\`\`\`javascript
const hello = "world";
\`\`\`

数学公式测试：$E = mc^2$

完成！`

  const result = await renderMarkdown(content)
  
  return result
}

// 导出便捷函数
export default {
  renderMarkdown,
  preload,
  resetCache,
  getProcessorStatus,
  testProcessor,
  quickTest
}

// 在浏览器中暴露测试函数
if (typeof window !== 'undefined') {
  window.markdownTest = {
    quickTest,
    renderMarkdown,
    getProcessorStatus,
    testProcessor
  }
}