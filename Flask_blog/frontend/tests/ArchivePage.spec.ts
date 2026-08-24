import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const api = vi.hoisted(() => ({ getPublicArticles: vi.fn() }))
const mocks = vi.hoisted(() => ({
  route: { query: {} as Record<string, string> },
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../src/api', () => ({
  API: { getPublicArticles: (...a: unknown[]) => api.getPublicArticles(...a) },
}))
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}))

import ArchivePage from '../src/views/ArchivePage.vue'

const ARTICLES = [
  { id: 1, title: 'A 2026-08', slug: 'a', published_at: '2026-08-12T00:00:00Z', category: 'AI 工程' },
  { id: 2, title: 'B 2026-01', slug: 'b', published_at: '2026-01-05T00:00:00Z', category: 'Python' },
  { id: 3, title: 'C 2025-12', slug: 'c', published_at: '2025-12-18T00:00:00Z', category: '软件设计' },
  { id: 4, title: 'D 2025-06', slug: 'd', published_at: '2025-06-22T00:00:00Z', category: '' },
]

function mockList(list: unknown[]) {
  api.getPublicArticles.mockReset()
  api.getPublicArticles.mockResolvedValue({
    data: { data: { list, has_next: false } },
  })
}

function mountPage() {
  return mount(ArchivePage, {
    global: { stubs: { 'el-skeleton': { template: '<div class="skel" />' } } },
  })
}

describe('ArchivePage(P1-A)', () => {
  beforeEach(() => {
    mocks.route.query = {}
    mocks.push.mockReset()
    mockList(ARTICLES)
  })

  it('年份倒序、年内日期倒序分组(A1)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const years = wrapper.findAll('.year-label').map((n) => n.text())
    expect(years[0]).toContain('2026')
    expect(years[1]).toContain('2025')
    const titles2026 = wrapper.findAll('.archive-year')[0].findAll('h3').map((n) => n.text())
    expect(titles2026).toEqual(['A 2026-08', 'B 2026-01'])
  })

  it('行内不含摘要/卡片容器,密度为行列表', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.findAll('.archive-row').length).toBe(4)
    expect(wrapper.find('.archive-row p').exists()).toBe(false)
  })

  it('年份 Tab 过滤 + 总数文案 + ?year 同步(A2)', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.archive-tools .meta').text()).toContain('共 4 篇文章')

    const btn2025 = wrapper.findAll('.year-tabs button').find((b) => b.text() === '2025')!
    await btn2025.trigger('click')
    expect(mocks.push).toHaveBeenCalledWith({ query: { year: '2025' } })
    // 本地立即过滤
    expect(wrapper.findAll('.archive-row').length).toBe(2)
    expect(wrapper.find('.archive-tools .meta').text()).toContain('共 2 篇文章')

    // 全部:移除 query
    const btnAll = wrapper.findAll('.year-tabs button').find((b) => b.text() === '全部')!
    await btnAll.trigger('click')
    expect(mocks.push).toHaveBeenLastCalledWith({ query: {} })
    expect(wrapper.findAll('.archive-row').length).toBe(4)
  })

  it('直链 ?year=2025 打开即为筛选态(A2)', async () => {
    mocks.route.query = { year: '2025' }
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.findAll('.archive-row').length).toBe(2)
    expect(wrapper.find('.archive-tools .meta').text()).toContain('共 2 篇文章')
  })

  it('行点击进入文章详情', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('.archive-row').trigger('click')
    expect(mocks.push).toHaveBeenCalledWith('/article/a')
  })

  it('空态(A3)', async () => {
    mockList([])
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('还没有文章')
  })

  it('加载失败显示错误态与重试(A3)', async () => {
    api.getPublicArticles.mockReset()
    api.getPublicArticles.mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('归档加载失败')
    api.getPublicArticles.mockResolvedValue({ data: { data: { list: [], has_next: false } } })
    await wrapper.find('.retry-btn').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('还没有文章')
  })
})
