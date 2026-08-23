import { describe, it, expect, beforeEach } from 'vitest'
import { blocksFromMarkdown, slugifyHeading, _resetBlockIds } from '../src/utils/blocksFromMarkdown'

describe('blocksFromMarkdown', () => {
  beforeEach(() => {
    _resetBlockIds()
  })

  it('converts paragraphs', () => {
    const blocks = blocksFromMarkdown('第一段文字。\n\n第二段文字。')
    const paras = blocks.filter((b) => b.type === 'paragraph')
    expect(paras).toHaveLength(2)
    expect(paras[0]).toMatchObject({ type: 'paragraph', width: 'text' })
    expect(paras[0].html).toContain('第一段文字')
  })

  it('converts headings with stable slugged anchors and dedupes them', () => {
    const md = '## 基础富文本\n\n### 深入\n\n## 基础富文本'
    const blocks = blocksFromMarkdown(md)
    const heads = blocks.filter((b) => b.type === 'heading')
    expect(heads).toHaveLength(3)
    expect(heads[0]).toMatchObject({ level: 2, text: '基础富文本', anchor: '基础富文本' })
    // 同名标题第二次出现追加序号
    expect(heads[2].anchor).toBe('基础富文本-1')
    // 稳定性:两次转换结果一致
    const again = blocksFromMarkdown(md)
    expect(again.filter((b) => b.type === 'heading').map((h) => h.anchor)).toEqual(
      heads.map((h) => h.anchor),
    )
  })

  it('converts fenced code with language and filename convention', () => {
    const md = '```python:rag_pipeline.py\ndef f():\n    pass\n```'
    const blocks = blocksFromMarkdown(md)
    expect(blocks).toHaveLength(1)
    expect(blocks[0]).toMatchObject({
      type: 'code',
      language: 'python',
      filename: 'rag_pipeline.py',
      width: 'code',
    })
    expect(blocks[0].code).toContain('def f')
  })

  it('converts standalone images into image blocks with alt as caption', () => {
    const md = '![混合检索示意](https://example.com/fig.png)'
    const blocks = blocksFromMarkdown(md)
    expect(blocks).toHaveLength(1)
    expect(blocks[0]).toMatchObject({
      type: 'image',
      src: 'https://example.com/fig.png',
      alt: '混合检索示意',
      width: 'wide',
    })
  })

  it('converts tables preserving head and rows', () => {
    const md = '| 方案 | 召回率 |\n|---|---|\n| 向量 | 82.4% |\n| 混合 | 91.3% |'
    const blocks = blocksFromMarkdown(md)
    const table = blocks.find((b) => b.type === 'table')
    expect(table).toBeTruthy()
    expect(table.head).toEqual(['方案', '召回率'])
    expect(table.rows).toHaveLength(2)
    expect(table.rows[0]).toEqual(['向量', '82.4%'])
    expect(table.width).toBe('wide')
  })

  it('converts blockquotes and extracts cite from trailing — line', () => {
    const md = '> 技术文章真正难的往往不是写出来。\n>\n> — 设计备注'
    const blocks = blocksFromMarkdown(md)
    const quote = blocks.find((b) => b.type === 'quote')
    expect(quote).toBeTruthy()
    expect(quote.html).toContain('技术文章真正难')
    expect(quote.cite).toBe('设计备注')
  })

  it('converts ordered and bullet lists', () => {
    const md = '- 甲\n- 乙\n\n1. 一\n2. 二'
    const blocks = blocksFromMarkdown(md)
    const lists = blocks.filter((b) => b.type === 'list')
    expect(lists).toHaveLength(2)
    expect(lists[0]).toMatchObject({ ordered: false })
    expect(lists[0].items.map((i) => i.html.join ? '' : '')).toBeTruthy()
    expect(lists[0].items).toHaveLength(2)
    expect(lists[1]).toMatchObject({ ordered: true })
  })

  it('returns empty array for empty input', () => {
    expect(blocksFromMarkdown('')).toEqual([])
    expect(blocksFromMarkdown('   \n  ')).toEqual([])
  })

  it('slugifyHeading keeps cjk letters and strips symbols', () => {
    expect(slugifyHeading('RAG 到底是什么?')).toBe('rag-到底是什么')
    expect(slugifyHeading('!!!')).toBe('section')
  })
})
