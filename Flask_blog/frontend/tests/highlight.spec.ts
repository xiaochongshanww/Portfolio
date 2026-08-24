import { describe, it, expect } from 'vitest'
import { splitHighlight } from '../src/utils/highlight'

describe('splitHighlight(B3 XSS 红线)', () => {
  it('无关键词返回整段普通文本', () => {
    expect(splitHighlight('hello world', '')).toEqual([{ text: 'hello world', hit: false }])
  })

  it('精确子串命中且大小写不敏感', () => {
    expect(splitHighlight('深入理解 RAG 系统', 'rag')).toEqual([
      { text: '深入理解 ', hit: false },
      { text: 'RAG', hit: true },
      { text: ' 系统', hit: false },
    ])
  })

  it('多命中全部标出', () => {
    const parts = splitHighlight('aXa aXa', 'x')
    expect(parts.filter((p) => p.hit).length).toBe(2)
    expect(parts.map((p) => p.text).join('')).toBe('aXa aXa')
  })

  it('关键词为含标签的注入串时仅作字面文本处理', () => {
    const parts = splitHighlight('前<img onerror=alert(1)>后', '<img onerror=alert(1)>')
    // 结构化片段,无任何 HTML 解释;渲染层用 mustache 输出,天然转义
    expect(parts).toEqual([{ text: '前', hit: false }, { text: '<img onerror=alert(1)>', hit: true }, { text: '后', hit: false }])
  })

  it('空文本与空关键词边界', () => {
    expect(splitHighlight('', 'kw')).toEqual([])
    expect(splitHighlight(null, 'kw')).toEqual([])
    expect(splitHighlight('text', '   ')).toEqual([{ text: 'text', hit: false }])
  })
})
