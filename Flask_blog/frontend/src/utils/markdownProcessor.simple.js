/**
 * 简化的Markdown处理器 - 业界最佳实践版本
 * 完全依赖插件自动化处理，无需手动干预
 */

import MarkdownIt from 'markdown-it'
// markdown-it-katex可能需要特殊导入方式
import markdownItKatex from 'markdown-it-katex'
import { fromHighlighter } from '@shikijs/markdown-it'
import { createHighlighter } from 'shiki'

// 缓存highlighter实例
let highlighterCache = null

/**
 * 创建Shiki高亮器
 */
const getHighlighter = async () => {
  if (highlighterCache) return highlighterCache

  try {
    highlighterCache = await createHighlighter({
      themes: ['github-light', 'github-dark'],
      langs: [
        'javascript', 'typescript', 'python', 'html', 'css', 'json',
        'bash', 'yaml', 'sql', 'php', 'java', 'go', 'rust', 'vue'
      ]
    })
    return highlighterCache
  } catch (error) {
    console.error('Failed to create highlighter:', error)
    return null
  }
}

/**
 * 创建标准的MarkdownIt实例 - 业界最佳实践
 */
export const createProcessor = async () => {
  // 基础配置
  const md = MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
  })

  // 数学公式支持 - 完全自动化
  try {
    // 检查插件是否正确导入
    const katexPlugin = markdownItKatex.default || markdownItKatex;
    md.use(katexPlugin, {
      throwOnError: false,
      errorColor: '#cc0000'
    });
    console.log('✅ KaTeX plugin loaded successfully');
  } catch (error) {
    console.error('❌ Failed to load KaTeX plugin:', error);
  }

  // 代码高亮支持
  try {
    const highlighter = await getHighlighter()
    if (highlighter) {
      md.use(fromHighlighter(highlighter, {
        theme: 'github-light'
      }))
      console.log('✅ Shiki代码高亮器已配置');
    } else {
      console.warn('⚠️ Shiki高亮器创建失败');
      // 如果Shiki失败，使用基础代码块渲染
      md.renderer.rules.fence = function(tokens, idx) {
        const token = tokens[idx]
        const code = token.content.trim()
        const lang = token.info.trim()
        return `<pre class="basic-code-block"><code class="language-${lang}">${md.utils.escapeHtml(code)}</code></pre>`
      }
    }
  } catch (error) {
    console.error('❌ 代码高亮配置失败:', error)
    // 降级到基础代码块
    md.renderer.rules.fence = function(tokens, idx) {
      const token = tokens[idx]
      const code = token.content.trim()
      const lang = token.info.trim()
      return `<pre class="basic-code-block"><code class="language-${lang}">${md.utils.escapeHtml(code)}</code></pre>`
    }
  }

  return md
}

/**
 * 处理Markdown - 业界标准方法
 */
export const renderMarkdown = async (content) => {
  if (!content) return ''
  
  try {
    const md = await createProcessor()
    console.log('✅ Markdown processor created successfully')
    return md.render(content)
  } catch (error) {
    console.error('Markdown processing failed:', error)
    return content // 降级返回原内容
  }
}

// 预加载
export const preload = async () => {
  try {
    await getHighlighter()
    console.log('✅ Markdown processor preloaded')
  } catch (error) {
    console.warn('⚠️ Preload failed:', error)
  }
}