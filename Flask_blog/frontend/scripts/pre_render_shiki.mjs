import fs from 'fs/promises'
import path from 'path'
import { createHighlighter } from 'shiki'

async function renderMarkdownWithShiki(inputMarkdown, theme = 'github-light') {
  // 简单替换所有 fenced code blocks: ```lang\ncode\n```
  const fenceRE = /```(\w+)?\n([\s\S]*?)```/g
  const highlighter = await createHighlighter({ themes: [theme] })

  const replaced = await replaceAsync(inputMarkdown, fenceRE, async (match, lang = '', code) => {
    const langName = (lang || 'text')
    try {
      const html = highlighter.codeToHtml(code, { lang: langName, theme })
      return html
    } catch (e) {
      // fallback: escape and return pre block
      return `<pre class="basic-code-block"><code class="language-${escapeHtml(langName)}">${escapeHtml(code)}</code></pre>`
    }
  })

  return replaced
}

// helper: async replace
async function replaceAsync(str, regex, asyncFn) {
  const parts = []
  let lastIndex = 0
  let match
  while ((match = regex.exec(str)) !== null) {
    parts.push(str.slice(lastIndex, match.index))
    parts.push(await asyncFn(...match))
    lastIndex = match.index + match[0].length
  }
  parts.push(str.slice(lastIndex))
  return parts.join('')
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

async function main() {
  const argv = process.argv.slice(2)
  if (argv.length >= 2) {
    const inPath = path.resolve(process.cwd(), argv[0])
    const outPath = path.resolve(process.cwd(), argv[1])
    const md = await fs.readFile(inPath, 'utf8')
    const rendered = await renderMarkdownWithShiki(md)
    await fs.writeFile(outPath, rendered, 'utf8')
    console.log(`Wrote rendered HTML to ${outPath}`)
    return
  }

  // No args: run a small demo
  const demoLines = [
    '# Demo',
    '',
    '这是一个包含代码块的示例：',
    '',
    '```' + 'python',
    'import numpy as np',
    'def f(x):',
    '  return np.exp(-x**2)',
    '```',
    '',
    '文本结束.'
  ]
  const demo = demoLines.join('\n')
  const out = await renderMarkdownWithShiki(demo)
  console.log('--- Rendered demo output (truncated) ---')
  console.log(out.substring(0, 1200))
}

const __filename = new URL('', import.meta.url).pathname
if (process.argv[1] && process.argv[1].endsWith('pre_render_shiki.mjs') || import.meta.url.endsWith('pre_render_shiki.mjs')) {
  main().catch(err => {
    console.error('pre_render_shiki failed:', err)
    process.exit(1)
  })
}

export { renderMarkdownWithShiki }
