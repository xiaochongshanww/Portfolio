import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const api = vi.hoisted(() => ({ getPublicTaxonomy: vi.fn(), getPublicArticles: vi.fn() }))
const mocks = vi.hoisted(() => ({
  route: { query: {} },
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../src/api', () => ({
  API: {
    getPublicTaxonomy: (...a: unknown[]) => api.getPublicTaxonomy(...a),
    getPublicArticles: (...a: unknown[]) => api.getPublicArticles(...a),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}))

import TopicsPage from '../src/views/TopicsPage.vue'

const CATS = [
  { id: 1, name: 'AI 工程', slug: 'ai', article_count: 12, description: null },
  { id: 2, name: '软件设计', slug: 'sw', article_count: 9, description: null },
  { id: 3, name: '产品实践', slug: 'pd', article_count: 8, description: null },
  { id: 4, name: 'Python', slug: 'py', article_count: 18, description: null },
  { id: 5, name: '测试工程', slug: 'qa', article_count: 3, description: null },
]

const ARTICLES = [
  { id: 10, title: '最新 AI 文', slug: 'a', category_id: 1, published_at: '2026-08-01T00:00:00Z', updated_at: '2026-08-10T00:00:00Z' },
  { id: 11, title: '旧 AI 文', slug: 'b', category_id: 1, published_at: '2026-01-01T00:00:00Z', updated_at: null },
]

function mockData(cats: unknown[] = CATS, articles: unknown[] = ARTICLES) {
  api.getPublicTaxonomy.mockReset()
  api.getPublicArticles.mockReset()
  api.getPublicTaxonomy.mockResolvedValue({ data: { data: { categories: cats } } })
  api.getPublicArticles.mockResolvedValue({ data: { data: { list: articles } } })
}

function mountPage() {
  return mount(TopicsPage, {
    global: { stubs: { 'el-skeleton': { template: '<div class="skel" />' } } },
  })
}

describe('TopicsPage(P1-C)', () => {
  beforeEach(() => {
    mocks.push.mockReset()
    mockData()
  })

  it('渲染 ≤4 张主卡:名称/篇数/最新一篇,超出折叠为次级链接(C1)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.findAll('.topic-card').length).toBe(4)
    const first = wrapper.findAll('.topic-card')[0]
    expect(first.find('h2').text()).toBe('Python') // 按篇数降序
    expect(first.find('.topic-count').text()).toContain('18 篇文章')
    // 最新一篇标题
    const aiCard = wrapper.findAll('.topic-card').find((c) => c.find('h2').text() === 'AI 工程')!
    expect(aiCard.find('.topic-latest').text()).toContain('最新 AI 文')
    // 第 5 个分类折叠
    expect(wrapper.find('.topic-extras').text()).toContain('测试工程')
  })

  it('有更新文章的专题显示「持续更新」标记(C1)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const aiCard = wrapper.findAll('.topic-card').find((c) => c.find('h2').text() === 'AI 工程')!
    expect(aiCard.find('.topic-count').text()).toContain('持续更新')
    const pyCard = wrapper.findAll('.topic-card').find((c) => c.find('h2').text() === 'Python')!
    expect(pyCard.find('.topic-count').text()).not.toContain('持续更新')
  })

  it('点击卡片跳转 /topics/:slug(C2)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('.topic-card').trigger('click')
    expect(mocks.push).toHaveBeenCalledWith('/topics/py')
  })

  it('无分类时空态「专题正在整理中」(C1)', async () => {
    mockData([], [])
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('专题正在整理中')
  })

  it('taxonomy 失败进入错误态(C2)', async () => {
    api.getPublicTaxonomy.mockReset()
    api.getPublicTaxonomy.mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('专题加载失败')
  })
})
