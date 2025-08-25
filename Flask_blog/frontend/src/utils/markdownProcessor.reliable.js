/**
 * 可靠的Markdown处理器 - 专注于稳定性和功能完整性
 * 使用业界最佳实践，确保Shiki代码高亮和KaTeX数学公式都能正常工作
 */

import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'
import { createHighlighter } from 'shiki'

// 全局缓存
let highlighterCache = null
let mdCache = null

/**
 * 创建并缓存Shiki高亮器
 */
const createShikiHighlighter = async () => {
  if (highlighterCache) return highlighterCache
  
  try {
    console.log('🚀 正在创建Shiki高亮器...')
    
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
    
    console.log('✅ Shiki高亮器创建成功')
    
    // 测试高亮器是否工作
    const testCode = 'const hello = "world";'
    const testResult = highlighterCache.codeToHtml(testCode, {
      lang: 'javascript',
      theme: 'github-light'
    })
    
    if (testResult && testResult.includes('<span')) {
      console.log('✅ Shiki高亮器测试通过')
    } else {
      console.warn('⚠️ Shiki高亮器测试失败，但继续使用')
    }
    
    return highlighterCache
  } catch (error) {
    console.error('❌ Shiki高亮器创建失败:', error)
    console.log('🔄 尝试使用最小配置重新创建...')
    
    // 尝试使用最小配置重新创建
    try {
      highlighterCache = await createHighlighter({
        themes: ['github-light'],
        langs: ['javascript', 'python', 'html', 'css', 'json', 'text']
      })
      console.log('✅ 使用最小配置创建成功')
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
  
  console.log('🔧 创建MarkdownIt处理器...')
  
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
    console.log('✅ KaTeX插件已加载')
  } catch (error) {
    console.error('❌ KaTeX插件加载失败:', error)
  }
  
  // 2. 配置Shiki代码高亮支持
  const highlighter = await createShikiHighlighter()
  
  if (highlighter) {
    // 自定义fence渲染规则 - 最简单可靠的方法
    md.renderer.rules.fence = function (tokens, idx, options, env, renderer) {
      const token = tokens[idx]
      const code = token.content
      const info = token.info ? token.info.trim() : ''
      const langName = info.split(/\s+/g)[0]
      
      // 详细调试信息
      console.log(`🎨 渲染代码块详细信息:`, {
        tokenType: token.type,
        tokenInfo: token.info,
        infoTrimmed: info,
        langName: langName,
        codeLength: code.length,
        codeFirst50: code.substring(0, 50),
        token: token
      })
      
      try {
        // 支持的语言映射
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
          console.log(`🔍 需要推断语言，当前: ${langName || 'empty'}，代码片段:`, code.substring(0, 100));
          
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
            console.log('✅ 从代码内容推断为 Python');
          } else if (jsPatterns.some(pattern => pattern.test(code))) {
            finalLang = 'javascript';
            console.log('✅ 从代码内容推断为 JavaScript');
          } else if (htmlPatterns.some(pattern => pattern.test(code))) {
            finalLang = 'html';
            console.log('✅ 从代码内容推断为 HTML');
          } else {
            // 对于机器学习内容，大概率是Python
            finalLang = 'python';
            console.log('✅ 无法推断，默认使用 Python (机器学习上下文)');
          }
        }
        
        // 尝试不同的Shiki配置方法
        let html;
        
        // 使用正确的亮色主题
        console.log(`🎨 使用Shiki渲染 (${finalLang})...`)
        
        html = highlighter.codeToHtml(code, {
          lang: finalLang,
          theme: 'github-light'
        })
        
        console.log(`🎨 使用主题: github-light`)
        
        // 输出原始HTML用于调试
        console.log(`🔍 Shiki原始输出:`, html.substring(0, 200))
        
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
          
          console.log(`🔧 HTML修改前:`, beforeModification)
          console.log(`🔧 HTML修改后:`, afterModification)
        }
        
        // 检查背景色情况
        const hasInlineBackground = html.includes('background-color')
        const backgroundColorMatch = html.match(/background-color:[^;\"]+/)
        
        console.log(`🎨 背景色分析:`, {
          hasInlineBackground,
          backgroundColorMatch: backgroundColorMatch ? backgroundColorMatch[0] : 'none',
          htmlSample: html.substring(0, 300)
        })
        
        console.log(`✅ Shiki渲染成功: "${langName}" → "${finalLang}"`)
        console.log(`📄 生成HTML长度: ${html.length}, 包含颜色span: ${html.includes('<span style="color:')}`);
        
        return html
        
      } catch (error) {
        console.warn(`⚠️ Shiki渲染失败 (${langName}):`, error.message)
        
        // 降级到基础代码块
        const escapedCode = md.utils.escapeHtml(code)
        return `<pre class="fallback-code-block"><code class="language-${md.utils.escapeHtml(langName || 'text')}">${escapedCode}</code></pre>`
      }
    }
    
    console.log('✅ Shiki代码高亮已配置')
  } else {
    console.warn('⚠️ 使用基础代码块渲染')
    
    // 基础代码块渲染
    md.renderer.rules.fence = function (tokens, idx, options, env, renderer) {
      const token = tokens[idx]
      const code = token.content
      const info = token.info ? token.info.trim() : ''
      const langName = info.split(/\s+/g)[0]
      
      const escapedCode = md.utils.escapeHtml(code)
      return `<pre class="basic-code-block"><code class="language-${md.utils.escapeHtml(langName || 'text')}">${escapedCode}</code></pre>`
    }
  }
  
  // 3. 自定义图片渲染 - 添加响应式支持
  const defaultImageRenderer = md.renderer.rules.image || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }
  
  md.renderer.rules.image = function(tokens, idx, options, env, self) {
    const token = tokens[idx]
    token.attrPush(['loading', 'lazy'])
    token.attrPush(['class', 'markdown-image'])
    return defaultImageRenderer(tokens, idx, options, env, self)
  }
  
  // 4. 自定义表格渲染 - 添加响应式包装
  const defaultTableOpenRenderer = md.renderer.rules.table_open || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }
  
  md.renderer.rules.table_open = function(tokens, idx, options, env, self) {
    return '<div class="table-wrapper">' + defaultTableOpenRenderer(tokens, idx, options, env, self)
  }
  
  md.renderer.rules.table_close = function(tokens, idx, options, env, self) {
    return '</table></div>'
  }
  
  mdCache = md
  console.log('✅ MarkdownIt处理器创建完成')
  return md
}

/**
 * 主要的Markdown渲染函数
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
  
  console.log('📝 开始渲染Markdown内容:', {
    length: content.length,
    hasMath: content.includes('$'),
    hasCodeBlocks: content.includes('```'),
    detectedCodeBlocks: codeBlocks,
    contentSample: content.substring(0, 300) + '...'
  })
  
  try {
    const md = await createMarkdownProcessor()
    const result = md.render(content)
    
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
    
    console.log('✅ Markdown渲染完成:', resultAnalysis)
    
    // 如果有代码块但没有语法高亮，输出详细信息
    if (content.includes('```') && !resultAnalysis.hasShikiCode && !resultAnalysis.hasShikiSpans) {
      console.warn('🚨 检测到代码块但没有Shiki高亮效果!')
      
      // 提取前500字符的输出用于调试
      const outputSample = result.substring(0, 500)
      console.log('📄 渲染输出示例:', outputSample)
      
      // 查找所有的代码块
      const codeMatches = result.match(/<pre[^>]*>.*?<\/pre>/gs)
      if (codeMatches) {
        console.log('🔍 找到的代码块:', codeMatches.map((match, i) => `${i+1}: ${match.substring(0, 100)}...`))
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
  console.log('🔄 预加载Markdown处理器...')
  
  try {
    await createMarkdownProcessor()
    console.log('✅ Markdown处理器预加载完成')
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
  console.log('🔄 缓存已重置')
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
  console.log('🧪 测试Markdown处理器...')
  
  const testContent = `# 测试文档

这是一个测试文档，包含：

## 数学公式
行内公式：$E = mc^2$

块级公式：
$$\\sum_{i=1}^{n} x_i = \\frac{1}{n}\\sum_{i=1}^{n} x_i$$

## 代码块
\`\`\`javascript
const hello = "world";
console.log(hello);
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
    console.log('🧪 测试结果:', {
      success: !!result,
      length: result.length,
      hasKaTeX: result.includes('katex'),
      hasCode: result.includes('<pre'),
      sample: result.substring(0, 200) + '...'
    })
    return result
  } catch (error) {
    console.error('🧪 测试失败:', error)
    return null
  }
}

/**
 * 快速测试函数 - 在浏览器控制台中使用
 */
export const quickTest = async (testContent) => {
  const content = testContent || `# 快速测试

这是一个测试：

\`\`\`javascript
const hello = "world";
console.log(hello);
\`\`\`

数学公式测试：$E = mc^2$

完成！`

  console.log('🚀 快速测试开始...')
  const result = await renderMarkdown(content)
  console.log('📊 测试结果:', {
    success: !!result,
    hasShiki: result.includes('shiki'),
    hasKaTeX: result.includes('katex'),
    hasCode: result.includes('<pre'),
    fullResult: result
  })
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
  console.log('🔧 已在 window.markdownTest 中暴露测试函数')
}