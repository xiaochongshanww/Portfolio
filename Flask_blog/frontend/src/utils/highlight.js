/**
 * 命中词高亮(B3):纯文本拆分为 {text, hit} 片段数组,由模板循环渲染,
 * 全程不经过 v-html——注入的 HTML 只会被当作字面文本,天然满足 XSS 红线。
 */

/**
 * @param {string | null | undefined} text 原文本
 * @param {string} keyword 关键词(大小写不敏感,多命中全部标出)
 * @returns {Array<{text: string, hit: boolean}>}
 */
export function splitHighlight(text, keyword) {
  const src = String(text ?? '')
  const kw = String(keyword ?? '').trim()
  if (!kw) return src ? [{ text: src, hit: false }] : []

  const lower = src.toLowerCase()
  const k = kw.toLowerCase()
  /** @type {Array<{text: string, hit: boolean}>} */
  const parts = []
  let i = 0
  while (i < lower.length) {
    const idx = lower.indexOf(k, i)
    if (idx === -1) {
      parts.push({ text: src.slice(i), hit: false })
      break
    }
    if (idx > i) parts.push({ text: src.slice(i, idx), hit: false })
    parts.push({ text: src.slice(idx, idx + k.length), hit: true })
    i = idx + k.length
  }
  return parts.filter((p) => p.text !== '')
}
