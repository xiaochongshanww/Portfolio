/**
 * 简化的Markdown处理器 - 干净实现
 */

import MarkdownIt from 'markdown-it'
// markdown-it-katex 可能需要 default 导出支持
import markdownItKatex from 'markdown-it-katex'
import { createHighlighter } from 'shiki'

// 缓存 highlighter 实例
let highlighterCache = null
let lastHighlighterError = null

const getHighlighter = async () => {
  if (highlighterCache) return highlighterCache

  try {
    console.log('Shiki: creating highlighter. isBrowser:', typeof window !== 'undefined')
    highlighterCache = await createHighlighter({
      themes: ['github-light', 'github-dark'],
      langs: [
        'javascript', 'typescript', 'python', 'html', 'css', 'json',
        'bash', 'yaml', 'sql', 'php', 'java', 'go', 'rust', 'vue'
      ]
    })
    // 快速检测 highlighter 是否在当前运行时能产生 token color 信息
    try {
      const sample = 'const x = 42\nfunction f() { return x }'
      const tokens = typeof highlighterCache.codeToThemedTokens === 'function'
        ? highlighterCache.codeToThemedTokens(sample, 'javascript')
        : null
      const hasColor = Array.isArray(tokens) && tokens.some(line => line.some(part => !!part.color))
      if (!hasColor && typeof window !== 'undefined') {
        console.warn('Shiki highlighter instantiated but produced no token colors in browser. Trying shiki-wasm fallback...')
          try {
            // 尝试动态加载 shiki-wasm 包（如果已安装）——使用变量名以避免 Vite 在构建时静态解析不存在的包
            let wasmModule = null
            const tryPkgs = ['shiki-wasm', '@shikijs/shiki-wasm']
            for (const name of tryPkgs) {
              try {
                wasmModule = await import(name)
                if (wasmModule) { break }
              } catch (e) {
                // 忽略单个包的导入错误，继续尝试下一个
              }
            }

            if (wasmModule && (wasmModule.createHighlighter || wasmModule.default && wasmModule.default.createHighlighter)) {
              const createWasmHighlighter = wasmModule.createHighlighter || (wasmModule.default && wasmModule.default.createHighlighter)
              const wasmHigh = await createWasmHighlighter({ themes: ['github-light', 'github-dark'] })
              const wasmTokens = typeof wasmHigh.codeToThemedTokens === 'function'
                ? wasmHigh.codeToThemedTokens(sample, 'javascript')
                : null
              const wasmHasColor = Array.isArray(wasmTokens) && wasmTokens.some(line => line.some(part => !!part.color))
              if (wasmHasColor) {
                console.log('✅ shiki-wasm fallback produced token colors; using wasm highlighter')
                highlighterCache = wasmHigh
              } else {
                console.warn('shiki-wasm loaded but did not produce token colors')
              }
            } else {
              console.warn('shiki-wasm not available to import')
            }
          } catch (wasmErr) {
            console.warn('shiki-wasm fallback attempt failed:', wasmErr)
          }
      }
    } catch (testErr) {
      console.warn('Shiki token color test failed:', testErr)
    }
    return highlighterCache
  } catch (err) {
    lastHighlighterError = err
    try { console.error('Failed to create shiki highlighter:', err && err.stack ? err.stack : err) } catch (e) {}
    return null
  }
}

export const checkShikiStatus = () => ({
  isBrowser: typeof window !== 'undefined',
  highlighterCachePresent: !!highlighterCache,
  lastError: lastHighlighterError ? (lastHighlighterError.stack || String(lastHighlighterError)) : null
})

export const createProcessor = async () => {
  const md = MarkdownIt({ html: true, linkify: true, typographer: true })

  // KaTeX 插件
  try {
    const katexPlugin = markdownItKatex.default || markdownItKatex
    md.use(katexPlugin, { throwOnError: false, errorColor: '#cc0000' })
    console.log('✅ KaTeX plugin loaded')
  } catch (e) {
    console.warn('Failed to load markdown-it-katex:', e)
  }

  // 配置代码高亮
  try {
    const highlighter = await getHighlighter()
    const themeName = 'github-light'

    if (highlighter) {
      md.renderer.rules.fence = function(tokens, idx) {
        const token = tokens[idx]
        const code = token.content || ''
        const info = token.info ? token.info.trim() : ''
        const lang = info || ''

        try {
          if (typeof highlighter.codeToThemedTokens === 'function') {
            const themed = highlighter.codeToThemedTokens(code, lang || undefined)
            // 检查是否至少有一个 token 带 color
            const hasColor = themed.some(line => line.some(part => !!part.color))
            if (hasColor) {
              const lines = themed.map(line => {
                const parts = line.map(part => {
                  const text = md.utils.escapeHtml(part.content)
                  if (part.color) return `<span style="color:${part.color}">${text}</span>`
                  return `<span>${text}</span>`
                })
                return `<span class="line">${parts.join('')}</span>`
              })
              const inner = lines.join('\n')
              return `<pre class="shiki ${md.utils.escapeHtml(themeName)}" data-shiki-inlined="true"><code class="language-${md.utils.escapeHtml(lang)}">${inner}</code></pre>`
            }
            // 如果没有 token color，则回退到 codeToHtml
          }

          // fallback to codeToHtml which returns full HTML string
          return highlighter.codeToHtml(code, { lang: lang || undefined, theme: themeName })
        } catch (e) {
          console.warn('Shiki rendering failed, fallback to escaped block:', e)
          return `<pre class="basic-code-block"><code class="language-${md.utils.escapeHtml(lang)}">${md.utils.escapeHtml(code)}</code></pre>`
        }
      }

      console.log('✅ Shiki configured for markdown rendering')
    } else {
      console.warn('⚠️ Shiki not available, using plain code blocks')
      md.renderer.rules.fence = function(tokens, idx) {
        const token = tokens[idx]
        const code = token.content || ''
        const lang = token.info ? token.info.trim() : ''
        return `<pre class="basic-code-block"><code class="language-${md.utils.escapeHtml(lang)}">${md.utils.escapeHtml(code)}</code></pre>`
      }
    }
  } catch (e) {
    console.error('Error configuring code highlighter:', e)
    md.renderer.rules.fence = function(tokens, idx) {
      const token = tokens[idx]
      const code = token.content || ''
      const lang = token.info ? token.info.trim() : ''
      return `<pre class="basic-code-block"><code class="language-${md.utils.escapeHtml(lang)}">${md.utils.escapeHtml(code)}</code></pre>`
    }
  }

  return md
}

export const renderMarkdown = async (content) => {
  if (!content) return ''
  try {
    const md = await createProcessor()
    return md.render(content)
  } catch (e) {
    console.error('Markdown processing failed:', e)
    return content
  }
}

export const preload = async () => {
  try { await getHighlighter(); console.log('✅ Markdown processor preloaded') } catch (e) { console.warn('Preload failed:', e) }
}