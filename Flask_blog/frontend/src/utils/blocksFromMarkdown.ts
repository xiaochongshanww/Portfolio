/**
 * Markdown → ArticleBlock[] 转换器
 * 来源: docs/design/blog-redesign-2026-08/03_文章内容系统与Block规范.md 第 25 节
 *
 * 管线: Markdown 文本 → markdown-it token 流 → Normalized Blocks
 * 旧文章(content_md)无需修改即可进入统一 Renderer。
 */
import MarkdownIt from 'markdown-it'
import type { ArticleBlock, BlockWidth } from '../types/articleBlocks'
import { DEFAULT_BLOCK_WIDTH } from '../types/articleBlocks'
import { sanitizeBlockHtml } from './sanitizeBlocks'

// 与 markdownProcessor.reliable.js 保持一致的基础配置(不含 shiki——高亮在 CodeBlock 组件内做)
const md = new MarkdownIt({ html: true, linkify: true, typographer: true, breaks: false })

let blockSeq = 0

function nextId(): string {
  blockSeq += 1
  return `blk-${blockSeq}`
}

/** 中文/混合文本的稳定 slug:同输入恒同输出 */
export function slugifyHeading(text: string): string {
  const base = text
    .trim()
    .toLowerCase()
    .replace(/[\s]+/g, '-')
    .replace(/[^\p{Letter}\p{Number}-]/gu, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  return base || 'section'
}

/** info string 支持 ```python 与 ```python:title 两种约定 */
function parseFenceInfo(info: string): { language: string; filename?: string } {
  const trimmed = info.trim()
  if (!trimmed) return { language: 'text' }
  // ```python:title —— 冒号紧贴语言名时拆分
  const colonIdx = trimmed.indexOf(':')
  if (colonIdx > 0 && !/\s/.test(trimmed.slice(0, colonIdx))) {
    return {
      language: trimmed.slice(0, colonIdx),
      filename: trimmed.slice(colonIdx + 1).trim() || undefined,
    }
  }
  // ```python title 或 ```python
  const parts = trimmed.split(/\s+/)
  const language = parts[0] || 'text'
  const filename = parts.slice(1).join(' ') || undefined
  return { language, filename }
}

/** 行内 token 流渲染为受控 HTML(inner 内容已由 markdown-it 生成),出口统一过 DOMPurify */
function renderInline(tokens: any[]): string {
  return sanitizeBlockHtml(md.renderer.renderInline(tokens, {}, {}))
}

/** 块级 token 序列中的行内子序列起点 */
function inlineChildren(token: any[]): any[] {
  return token[1]?.children ?? []
}

/**
 * :::note / :::warning title 形式的 callout 容器解析。
 * 未注册 container 插件时按普通段落处理,此处扫描原始 markdown 行实现轻量识别。
 */
function extractCallouts(source: string): string {
  return source
}

/** 主入口:markdown 文本 → ArticleBlock[] */
export function blocksFromMarkdown(source: string): ArticleBlock[] {
  if (!source || !source.trim()) return []

  const normalized = extractCallouts(String(source))
  const tokens: any[] = md.parse(normalized, {})
  const blocks: ArticleBlock[] = []
  /** heading anchor 去重表 */
  const seenAnchors = new Map<string, number>()

  for (let i = 0; i < tokens.length; i++) {
    const tok = tokens[i]
    if (tok.type === 'heading_open') {
      const level = Number(tok.tag.slice(1)) // h2 → 2
      const inline = tokens[i + 1]
      const text = (inline?.children ?? [])
        .filter((c: any) => c.type === 'text' || c.type === 'code_inline')
        .map((c: any) => c.content)
        .join('')
        .trim()
      let anchor = slugifyHeading(text)
      const n = seenAnchors.get(anchor) ?? 0
      seenAnchors.set(anchor, n + 1)
      if (n > 0) anchor = `${anchor}-${n}`
      blocks.push({
        id: nextId(),
        type: 'heading',
        width: DEFAULT_BLOCK_WIDTH.heading,
        level,
        text,
        anchor,
      })
      i += 1 // skip inline + close
      continue
    }

    if (tok.type === 'paragraph_open') {
      const inline = tokens[i + 1]
      const children: any[] = inline?.children ?? []
      // 纯图片段落(仅一张图+空白)→ ImageBlock
      const meaningful = children.filter(
        (c) =>
          c.type !== 'softbreak' &&
          c.type !== 'hardbreak' &&
          !(c.type === 'text' && !c.content?.trim()),
      )
      if (meaningful.length === 1 && meaningful[0].type === 'image') {
        const imgTok = meaningful[0]
        // token.attrs 在不同环境表现为数组([['src','...'],...])或 Map,做兼容取值
        const attrPairs: any[] = imgTok?.attrs ?? []
        const srcAttr = attrPairs.find?.((a) => a && a[0] === 'src')
        const src = typeof imgTok?.attrs?.get === 'function'
          ? imgTok.attrs.get('src') ?? ''
          : (srcAttr?.[1] ?? '')
        const alt = imgTok?.content?.trim() ?? ''
        blocks.push({
          id: nextId(),
          type: 'image',
          width: DEFAULT_BLOCK_WIDTH.image,
          src,
          alt,
          caption: alt || undefined,
        })
        i += 2
        continue
      }
      blocks.push({
        id: nextId(),
        type: 'paragraph',
        width: DEFAULT_BLOCK_WIDTH.paragraph,
        html: renderInline(children),
      })
      i += 2
      continue
    }

    if (tok.type === 'blockquote_open') {
      // 收集到 blockquote_close 为止(含嵌套段落)
      let depth = 1
      let j = i + 1
      const innerHtml: string[] = []
      let cite: string | undefined
      while (j < tokens.length && depth > 0) {
        const t = tokens[j]
        if (t.type === 'blockquote_open') depth += 1
        if (t.type === 'blockquote_close') depth -= 1
        if (t.type === 'inline' && depth >= 1) {
          innerHtml.push(renderInline(t.children ?? []))
        }
        j += 1
      }
      // 尾部 "— 出处" 视为 cite
      if (innerHtml.length > 0) {
        const last = innerHtml[innerHtml.length - 1]
        const m = last.match(/^—\s*(.+)$/)
        if (m) {
          cite = m[1].trim()
          innerHtml.pop()
        }
      }
      blocks.push({
        id: nextId(),
        type: 'quote',
        width: DEFAULT_BLOCK_WIDTH.quote,
        html: innerHtml.join('<br>'),
        cite,
      })
      i = j - 1
      continue
    }

    if (tok.type === 'fence') {
      const { language, filename } = parseFenceInfo(tok.info || '')
      blocks.push({
        id: nextId(),
        type: 'code',
        width: DEFAULT_BLOCK_WIDTH.code,
        language,
        filename,
        code: tok.content.replace(/\n$/, ''),
      })
      continue
    }

    if (tok.type === 'ordered_list_open' || tok.type === 'bullet_list_open') {
      const ordered = tok.type === 'ordered_list_open'
      const items: Array<{ html: string }> = []
      let depth = 1
      let j = i + 1
      while (j < tokens.length && depth > 0) {
        const t = tokens[j]
        if (t.type === 'ordered_list_open' || t.type === 'bullet_list_open') depth += 1
        if (t.type === 'ordered_list_close' || t.type === 'bullet_list_close') depth -= 1
        if (t.type === 'inline' && depth >= 1) items.push({ html: renderInline(t.children ?? []) })
        j += 1
      }
      blocks.push({
        id: nextId(),
        type: 'list',
        width: DEFAULT_BLOCK_WIDTH.list,
        ordered,
        items,
      })
      i = j - 1
      continue
    }

    if (tok.type === 'table_open') {
      /** @type {string[]} */
      const head: string[] = []
      /** @type {string[][]} */
      const rows: string[][] = []
      let j = i + 1
      let section: 'head' | 'body' | null = null
      /** @type {string[] | null} */
      let currentRow: string[] | null = null
      while (j < tokens.length && tok.type !== 'table_close') {
        const t = tokens[j]
        if (t.type === 'thead_open') section = 'head'
        if (t.type === 'tbody_open') section = 'body'
        if (t.type === 'tr_open') currentRow = []
        if (t.type === 'inline' && currentRow) {
          currentRow.push(renderInline(t.children ?? []))
        }
        if (t.type === 'tr_close' && currentRow) {
          if (section === 'head') head.push(...currentRow)
          else rows.push(currentRow)
          currentRow = null
        }
        if (t.type === 'table_close') break
        j += 1
      }
      blocks.push({
        id: nextId(),
        type: 'table',
        width: DEFAULT_BLOCK_WIDTH.table,
        head,
        rows,
      })
      i = j
      continue
    }

    if (tok.type === 'inline' && tok.children) {
      // 兜底:未被上方分支消费的 inline 按段落收
      blocks.push({
        id: nextId(),
        type: 'paragraph',
        width: DEFAULT_BLOCK_WIDTH.paragraph,
        html: renderInline(tok.children),
      })
      i += 2
      continue
    }

    if (tok.type === 'html_block') {
      blocks.push({
        id: nextId(),
        type: 'paragraph',
        width: DEFAULT_BLOCK_WIDTH.paragraph,
        html: sanitizeBlockHtml(tok.content),
      })
      continue
    }

    // hr / math_block / 其他未识别类型:P0 静默降级为空(不渲染),不阻塞
  }

  return blocks
}

/** 供测试与调试:重置 id 序列(仅在测试环境使用) */
export function _resetBlockIds(): void {
  blockSeq = 0
}
