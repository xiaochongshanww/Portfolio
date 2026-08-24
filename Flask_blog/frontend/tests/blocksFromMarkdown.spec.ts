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

describe('blocksFromMarkdown callout 容器(补齐 :::note 解析)', () => {
  beforeEach(() => {
    _resetBlockIds()
  })

  it(':::note title 容器解析为 callout block,内部 markdown 正常渲染', () => {
    const md = [':::note 设计原则', '所有 Block 共享同一条**内容轴**。', ':::', '', '后续段落。'].join('\n')
    const blocks = blocksFromMarkdown(md)
    const callout = blocks.find((b) => b.type === 'callout')
    expect(callout).toBeTruthy()
    expect(callout).toMatchObject({ tone: 'note', title: '设计原则', width: 'text' })
    expect(String(callout?.html)).toContain('<strong>内容轴</strong>')
    // 容器外的段落不受影响
    expect(blocks.filter((b) => b.type === 'paragraph')).toHaveLength(1)
  })

  it('tone 别名映射:tip→success,danger→warning;无标题用默认', () => {
    const md = [
      ':::tip', '小技巧。', ':::', '',
      ':::danger 危险操作', '别在生产库执行。', ':::',
    ].join('\n')
    const blocks = blocksFromMarkdown(md)
    const callouts = blocks.filter((b) => b.type === 'callout')
    expect(callouts).toHaveLength(2)
    expect(callouts[0]).toMatchObject({ tone: 'success', title: '提示' })
    expect(callouts[1]).toMatchObject({ tone: 'warning', title: '危险操作' })
  })

  it('未闭合容器按原文回落,不吞内容', () => {
    const md = [':::note', '这段会保留为普通段落。'].join('\n')
    const blocks = blocksFromMarkdown(md)
    expect(blocks.some((b) => b.type === 'callout')).toBe(false)
    expect(blocks.some((b) => String((b as any).html ?? '').includes('普通段落'))).toBe(true)
  })

  it('callout 内嵌脚本被消毒(XSS 红线)', () => {
    const md = [':::note', '内容 <img src=x onerror=alert(1)> 结束', ':::'].join('\n')
    const blocks = blocksFromMarkdown(md)
    const callout: any = blocks.find((b) => b.type === 'callout')
    expect(callout.html).not.toContain('onerror')
  })
})
