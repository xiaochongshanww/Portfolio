import { describe, it, expect, vi, beforeEach } from 'vitest'

const api = vi.hoisted(() => ({
  search: vi.fn(),
  getPublicArticles: vi.fn(),
  getPublicTaxonomy: vi.fn(),
  getPublicProjects: vi.fn(),
}))

vi.mock('../src/api', () => ({
  API: {
    SearchService: { search: (...a: unknown[]) => api.search(...a) },
    getPublicArticles: (...a: unknown[]) => api.getPublicArticles(...a),
    getPublicTaxonomy: (...a: unknown[]) => api.getPublicTaxonomy(...a),
    getPublicProjects: (...a: unknown[]) => api.getPublicProjects(...a),
  },
}))

import { unifiedSearch } from '../src/composables/useUnifiedSearch'

describe('unifiedSearch(B2 统一搜索)', () => {
  beforeEach(() => {
    api.search.mockReset()
    api.getPublicArticles.mockReset()
    api.getPublicTaxonomy.mockReset()
    api.getPublicProjects.mockReset()
    // 默认:项目 API 返回空列表(各用例按需覆盖)
    api.getPublicProjects.mockResolvedValue({ data: { data: { list: [] } } })
  })

  it('空关键词不发起任何请求', async () => {
    const { results, counts } = await unifiedSearch('   ')
    expect(results).toEqual([])
    expect(counts.all).toBe(0)
    expect(api.search).not.toHaveBeenCalled()
    expect(api.getPublicTaxonomy).not.toHaveBeenCalled()
  })

  it('三类结果混合返回,类型标记与计数正确', async () => {
    api.search.mockResolvedValue({
      data: { data: { list: [
        { title: 'RAG 入门', slug: 'rag-intro', excerpt: '关于 RAG', category: 'AI 工程' },
      ] } },
    })
    api.getPublicTaxonomy.mockResolvedValue({
      data: { data: { categories: [
        { id: 1, name: 'AI 工程', slug: 'ai', article_count: 12, description: null },
      ] } },
    })

    const { results, counts } = await unifiedSearch('rag')
    // 文章 1 + 专题(名称"AI 工程"不含 rag,描述为空 → 0) + 项目(空) = 1
    expect(results.map((r) => r.type)).toEqual(['article'])
    expect(counts).toEqual({ all: 1, article: 1, topic: 0, project: 0 })
    expect(results[0].href).toBe('/article/rag-intro')
  })

  it('专题按名称匹配并返回篇数 meta', async () => {
    api.search.mockResolvedValue({ data: { data: { list: [] } } })
    api.getPublicTaxonomy.mockResolvedValue({
      data: { data: { categories: [
        { id: 2, name: '软件设计', slug: 'sw', article_count: 9, description: null },
      ] } },
    })
    const { results, counts } = await unifiedSearch('软件')
    expect(counts.topic).toBe(1)
    expect(results[0].meta).toBe('专题 · 9 篇')
    expect(results[0].href).toBe('/topics/sw')
  })

  it('项目来源来自 Project API', async () => {
    api.search.mockResolvedValue({ data: { data: { list: [] } } })
    api.getPublicTaxonomy.mockResolvedValue({ data: { data: { categories: [] } } })
    api.getPublicProjects.mockResolvedValue({
      data: { data: { list: [
        { id: 1, name: 'Structure Lab', slug: 'structure-lab', description: '结构实验', status: 'active' },
        { id: 2, name: '无关项目', slug: 'other', description: '别的', status: 'paused' },
      ] } },
    })
    const { results, counts } = await unifiedSearch('structure')
    expect(counts.project).toBe(1)
    expect(results[0].type).toBe('project')
    expect(results[0].href).toBe('/projects/structure-lab')
    expect(results[0].meta).toContain('开发中')
  })

  it('搜索接口失败时静默降级为公开列表本地过滤,不抛错', async () => {
    api.search.mockRejectedValue(new Error('meili down'))
    api.getPublicArticles.mockResolvedValue({
      data: { data: { list: [
        { id: 1, title: 'Structure Lab 手记', slug: 's1', summary: '结构实验', category: '产品' },
        { id: 2, title: '无关文章', slug: 's2', summary: '别的', category: '' },
      ] } },
    })
    api.getPublicTaxonomy.mockResolvedValue({ data: { data: { categories: [] } } })

    const { results, counts } = await unifiedSearch('structure')
    expect(counts.article).toBe(1)
    expect(results[0].slug ?? results[0].href).toContain('s1')
  })

  it('taxonomy 失败不影响文章/项目结果', async () => {
    api.search.mockResolvedValue({
      data: { data: { list: [{ title: 'x', slug: 'x', excerpt: '', category: '' }] } },
    })
    api.getPublicTaxonomy.mockRejectedValue(new Error('taxonomy down'))
    const { counts } = await unifiedSearch('x')
    expect(counts.article).toBe(1)
    expect(counts.topic).toBe(0)
  })
})
