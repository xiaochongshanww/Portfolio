/**
 * Block HTML 安全过滤(03 号规范第 28 节)
 * - Block 内 HTML 一律经 DOMPurify 白名单清洗,不信任 markdown-it 原样输出;
 * - embed/media src 走域名白名单(P0 白名单为空 = 禁外部嵌入);
 * - attachment 仅允许相对路径。
 */
import DOMPurify from 'dompurify'

/** 允许的标签白名单:覆盖 markdown-it 常规输出 + KaTeX 数学公式 */
const ALLOWED_TAGS = [
  // 文本
  'p', 'br', 'hr', 'span', 'div',
  'strong', 'b', 'em', 'i', 'u', 's', 'del', 'ins', 'mark', 'code', 'kbd', 'sub', 'sup', 'small',
  // 标题/列表(QuoteBlock 等场景)
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  // 引用/表格
  'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption',
  // 链接与图片
  'a', 'img',
  // KaTeX 输出所需
  'math', 'semantics', 'annotation', 'mrow', 'mi', 'mn', 'mo', 'ms', 'mtext', 'mfrac', 'msqrt',
  'mroot', 'msub', 'msup', 'msubsup', 'munder', 'mover', 'munderover', 'mtable', 'mtr', 'mtd',
  'mstyle', 'mspace', 'mpadded', 'mphantom', 'menclose', 'mglyph', 'svg', 'path', 'g', 'use',
  // input 仅保留 checkbox(disabled 只读,任务列表)
  'input',
]

const ALLOWED_ATTR = [
  'href', 'title', 'alt', 'src', 'srcset', 'width', 'height', 'colspan', 'rowspan',
  'class', 'id', 'style', 'target', 'rel',
  // KaTeX
  'encoding', 'mathvariant', 'display', 'aria-hidden', 'role',
  'd', 'fill', 'stroke', 'stroke-width', 'viewBox', 'xmlns', 'transform',
  // 任务列表 checkbox
  'type', 'checked', 'disabled',
]

/** 禁止的协议 scheme */
const FORBID_ATTR_RE = [/^on/i, /^javascript:/i, /^data:text\/html/i]
DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
  const v = String(data.attrValue || '')
  if (FORBID_ATTR_RE.some((re) => re.test(v.trim().toLowerCase()))) {
    data.keepAttr = false
  }
})

/**
 * 清洗 Block 场景下的受信 HTML(markdown-it 渲染产物)。
 * @param {string} html
 */
export function sanitizeBlockHtml(html) {
  if (!html) return ''
  return DOMPurify.sanitize(String(html), {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
    KEEP_CONTENT: true,
  })
}

/** embed/media 外部来源白名单:P0 为空 = 全部禁止,渲染 fallback
 * @type {string[]} */
const EMBED_HOST_WHITELIST = []

/** @param {string} url */
export function isEmbedAllowed(url) {
  if (!url) return false
  try {
    const u = new URL(url, window.location.origin)
    if (u.origin === window.location.origin) return true
    return EMBED_HOST_WHITELIST.includes(u.hostname)
  } catch (e) {
    return false
  }
}

/** attachment 仅允许站内相对路径
 * @param {string} url
 */
export function isAttachmentUrlSafe(url) {
  if (!url) return false
  return url.startsWith('/') && !url.startsWith('//')
}
