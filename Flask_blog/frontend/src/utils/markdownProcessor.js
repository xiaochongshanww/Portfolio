/**
 * 统一的Markdown处理器
 * 集成数学公式(KaTeX)和代码高亮(Shiki)支持
 * 基于markdown-it生态系统的最佳实践
 */

import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'
import { fromHighlighter } from '@shikijs/markdown-it'
import { createHighlighter } from 'shiki'
import anchor from 'markdown-it-anchor'

// 缓存highlighter实例，避免重复创建
let highlighterCache = null

/**
 * 创建Shiki高亮器实例
 */
const createShikiHighlighter = async () => {
  if (highlighterCache) {
    return highlighterCache
  }

  try {
    highlighterCache = await createHighlighter({
      themes: [
        'github-light',
        'github-dark',
        'vitesse-light',
        'vitesse-dark'
      ],
      langs: [
        'javascript',
        'typescript',
        'python',
        'html',
        'css',
        'scss',
        'json',
        'bash',
        'sh',
        'yaml',
        'xml',
        'sql',
        'php',
        'java',
        'c',
        'cpp',
        'go',
        'rust',
        'vue',
        'react',
        'markdown',
        'latex',
        'tex'
      ]
    })
    
    console.log('✅ Shiki highlighter created successfully')
    return highlighterCache
  } catch (error) {
    console.error('❌ Failed to create Shiki highlighter:', error)
    return null
  }
}

/**
 * 创建配置好的MarkdownIt实例
 */
export const createMarkdownProcessor = async (options = {}) => {
  const {
    theme = 'github-light',
    mathDelimiters = 'all', // 'dollars', 'brackets', 'all'
    enableAnchor = true,
    enableMath = true,
    enableHighlight = true
  } = options

  // 创建基础MarkdownIt实例
  const md = MarkdownIt({
    html: true,          // 允许HTML标签
    xhtmlOut: false,     // 使用HTML5输出
    breaks: false,       // 不将换行符转换为<br>
    langPrefix: 'language-', // CSS语言前缀
    linkify: true,       // 自动识别链接
    typographer: true,   // 启用智能引号和其他排版替换
    quotes: '""\u2018\u2019',      // 引号样式
  })

  // 添加锚点支持（用于目录导航）
  if (enableAnchor) {
    md.use(anchor, {
      permalink: anchor.permalink.headerLink({
        symbol: '#',
        renderHref: (anchor) => `#${anchor}`,
        class: 'header-anchor'
      }),
      level: [1, 2, 3, 4, 5, 6],
      slugify: (str) => encodeURIComponent(str.trim().toLowerCase().replace(/\s+/g, '-'))
    })
  }

  // 添加数学公式支持
  if (enableMath) {
    md.use(markdownItKatex, {
      throwOnError: false,
      errorColor: '#cc0000',
      strict: 'warn',
      macros: {
        // 常用的数学宏定义
        '\\RR': '\\mathbb{R}',
        '\\NN': '\\mathbb{N}',
        '\\ZZ': '\\mathbb{Z}',
        '\\QQ': '\\mathbb{Q}',
        '\\CC': '\\mathbb{C}',
      }
    })
  }

  // 添加代码高亮支持
  if (enableHighlight) {
    try {
      const highlighter = await createShikiHighlighter()
      if (highlighter) {
        md.use(fromHighlighter(highlighter, {
          theme: 'github-light'
        }))
      } else {
        console.warn('⚠️ Shiki highlighter not available, falling back to basic code blocks')
      }
    } catch (error) {
      console.error('❌ Failed to setup Shiki highlighting:', error)
    }
  }

  // 自定义渲染规则
  setupCustomRenderers(md)

  return md
}

/**
 * 设置自定义渲染规则
 */
const setupCustomRenderers = (md) => {
  // 自定义图片渲染，添加懒加载和响应式支持
  const defaultImageRenderer = md.renderer.rules.image || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

  md.renderer.rules.image = (tokens, idx, options, env, self) => {
    const token = tokens[idx]
    const srcIndex = token.attrIndex('src')
    const altIndex = token.attrIndex('alt')
    
    if (srcIndex >= 0) {
      // 添加懒加载和响应式类
      token.attrPush(['loading', 'lazy'])
      token.attrPush(['class', 'markdown-image'])
    }
    
    return defaultImageRenderer(tokens, idx, options, env, self)
  }

  // 自定义表格渲染，添加响应式包装
  const defaultTableRenderer = md.renderer.rules.table_open || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

  md.renderer.rules.table_open = (tokens, idx, options, env, self) => {
    return '<div class="markdown-table-wrapper">' + defaultTableRenderer(tokens, idx, options, env, self)
  }

  md.renderer.rules.table_close = (tokens, idx, options, env, self) => {
    return '</table></div>'
  }
}

/**
 * 处理Markdown内容的主要函数
 */
export const processMarkdown = async (content, options = {}) => {
  if (!content || typeof content !== 'string') {
    return ''
  }

  try {
    const md = await createMarkdownProcessor(options)
    const rendered = md.render(content)
    
    console.log('✅ Markdown processed successfully', {
      inputLength: content.length,
      outputLength: rendered.length,
      options
    })
    
    return rendered
  } catch (error) {
    console.error('❌ Markdown processing failed:', error)
    // 返回原始内容作为降级方案
    return `<div class="markdown-error">
      <p>⚠️ Markdown渲染失败</p>
      <pre>${content}</pre>
    </div>`
  }
}

/**
 * 预加载highlighter（在应用启动时调用）
 */
export const preloadHighlighter = async () => {
  try {
    await createShikiHighlighter()
    console.log('✅ Markdown processor preloaded')
  } catch (error) {
    console.warn('⚠️ Failed to preload markdown processor:', error)
  }
}

// 导出单例实例
let processorInstance = null

/**
 * 获取单例Markdown处理器实例
 */
export const getMarkdownProcessor = async (options = {}) => {
  if (!processorInstance) {
    processorInstance = await createMarkdownProcessor(options)
  }
  return processorInstance
}

/**
 * 重置处理器实例（用于配置更新）
 */
export const resetProcessor = () => {
  processorInstance = null
  highlighterCache = null
}