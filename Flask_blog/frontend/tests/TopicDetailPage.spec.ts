import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const api = vi.hoisted(() => ({ getPublicTaxonomy: vi.fn(), getPublicArticles: vi.fn() }))
const mocks = vi.hoisted(() => ({
  route: { query: {}, params: {} },
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

import TopicDetailPage from '../src/views/TopicDetailPage.vue'

const CATS = [{ id: 1, name: 'AI 工程', slug: 'ai', article_count: 3, description: null }]

const ARTICLES = [
  { id: 1, title: '发布新但未更新', slug: 'pub-new', summary: 's1', tags: ['rag'], published_at: '2026-08-12T00:00:00Z', updated_at: null },
  { id: 2, title: '更新最早', slug: 'upd-old', summary: 's2', tags: ['agent'], published_at: '2026-05-01T00:00:00Z', updated_at: '2026-06-01T00:00:00Z' },
  { id: 3, title: '更新最新', slug: 'upd-new', summary: 's3', tags: ['eval'], published_at: '2026-03-01T00:00:00Z', updated_at: '2026-08-20T00:00:00Z' },
]

function mockData() {
  api.getPublicTaxonomy.mockReset()
  api.getPublicArticles.mockReset()
  api.getPublicTaxonomy.mockResolvedValue({ data: { data: { categories: CATS } } })
  api.getPublicArticles.mockResolvedValue({ data: { data: { list: ARTICLES } } })
}

function mountPage(slug = 'ai') {
  return mount(TopicDetailPage, {
    props: { slug },
    global: { stubs: { 'el-skeleton': { template: '<div class="skel" />' } } },
  })
}

describe('TopicDetailPage(P1-D)', () => {
  beforeEach(() => {
    mocks.push.mockReset()
    mockData()
  })

  it('Hero 渲染名称与统计数字,统计与文章数一致(D1)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.topic-hero h1').text()).toBe('AI 工程')
    expect(wrapper.find('.topic-stat strong').text()).toBe('3')
    expect(wrapper.find('.eyebrow').text()).toContain('长期专题 / AI 工程')
  })

  it('slug 无对应专题渲染 404 态(D1)', async () => {
    const wrapper = mountPage('not-exist')
    await flushPromises()
    expect(wrapper.text()).toContain('没有找到这个专题')
    expect(wrapper.text()).toContain('返回专题列表')
  })

  it('推荐起点无配置时降级为排序后最新一篇(D2)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.featured h2').text()).toBe('更新最新')
    expect(wrapper.find('.featured-copy .meta').text()).toContain('2026')
  })

  it('文章序列按 updated_at(降级 published_at)倒序(D3)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    // 排序键:upd-new=08-20 > pub-new(未更新,取发布 08-12) > upd-old=06-01
    const titles = wrapper.findAll('.feed-title').map((n) => n.text())
    expect(titles).toEqual(['更新最新', '发布新但未更新', '更新最早'])
  })

  it('点击推荐卡进入文章详情(D2)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('.featured').trigger('click')
    expect(mocks.push).toHaveBeenCalledWith('/article/upd-new')
  })

  it('专题无文章时显示「这个专题还在整理中」(D4)', async () => {
    api.getPublicArticles.mockReset()
    api.getPublicArticles.mockResolvedValue({ data: { data: { list: [] } } })
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('这个专题还在整理中')
  })

  it('加载失败显示错误态(D4)', async () => {
    api.getPublicTaxonomy.mockReset()
    api.getPublicTaxonomy.mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('专题加载失败')
  })
})
