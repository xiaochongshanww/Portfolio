import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const api = vi.hoisted(() => ({
  getPublicProjectBySlug: vi.fn(),
  getPublicArticles: vi.fn(),
}))
const mocks = vi.hoisted(() => ({
  route: { query: {}, params: {} },
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../src/api', () => ({
  API: {
    getPublicProjectBySlug: (...a: unknown[]) => api.getPublicProjectBySlug(...a),
    getPublicArticles: (...a: unknown[]) => api.getPublicArticles(...a),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}))

import ProjectDetailPage from '../src/views/ProjectDetailPage.vue'

const PROJECT = {
  id: 1,
  name: 'Structure Lab',
  slug: 'structure-lab',
  description: '把结构稳定性变成互动实验。',
  tag: '实验',
  status: 'active',
  is_current: true,
  preview_type: 'none',
  preview_data: null,
  link_url: '',
  repo_url: 'https://github.com/x/structure-lab',
  motivation: '为什么做第一段。\n\n为什么做第二段。',
  progress: '当前进度说明。',
  design_notes: '',
  related_article_slugs: ['good-post', 'missing-post'],
  changelog: [
    { date: '2026-08-20', title: '新增节点拖动', text: '支持拖动观察形变。' },
    { date: '2026-09-01', title: '下一步', text: '增加载荷工况。', next: true },
  ],
  updated_at: '2026-08-20T00:00:00Z',
}

const ARTICLES = [
  { id: 1, title: '结构相关的文章', slug: 'good-post', summary: 's1', tags: ['结构'], published_at: '2026-08-01T00:00:00Z' },
  { id: 2, title: '无关文章', slug: 'other', summary: 's2', tags: [], published_at: '2026-08-02T00:00:00Z' },
]

function mockData(project: unknown = PROJECT, articles: unknown[] = ARTICLES) {
  api.getPublicProjectBySlug.mockReset()
  api.getPublicArticles.mockReset()
  api.getPublicProjectBySlug.mockResolvedValue({ data: { data: project } })
  api.getPublicArticles.mockResolvedValue({ data: { data: { list: articles } } })
}

function mountPage(slug = 'structure-lab') {
  return mount(ProjectDetailPage, {
    props: { slug },
    global: { stubs: { 'el-skeleton': { template: '<div class="skel" />' } } },
  })
}

describe('ProjectDetailPage(P2-B2)', () => {
  beforeEach(() => {
    mocks.push.mockReset()
    mockData()
  })

  it('Identity + Live Status:状态/最近更新(updated_at)/Repo 链接', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.identity h1').text()).toBe('Structure Lab')
    const live = wrapper.find('.live-status').text()
    expect(live).toContain('开发中')
    expect(live).toContain('2026 年 8 月 20 日') // updated_at 而非 published
    expect(wrapper.find('.live-status a').text()).toContain('Repo')
    // 无 link_url 时显示规范空态文案
    expect(wrapper.find('.live-status .demo-none').text()).toContain('暂未开放在线体验')
  })

  it('相关文章:命中 slug 渲染,失效 slug 跳过', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const rows = wrapper.findAll('.feed-title')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toBe('结构相关的文章')
  })

  it('相关文章 slug 全部失效时区块整体隐藏(无死链)', async () => {
    mockData({ ...PROJECT, related_article_slugs: ['nope-1', 'nope-2'] })
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).not.toContain('相关技术文章')
  })

  it('Changelog 与 Next 分区;空文本区块隐藏', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('为什么做')
    expect(wrapper.text()).toContain('现在做到哪里')
    // design_notes 为空 → 该区块整体隐藏
    expect(wrapper.findAll('h2').map((h) => h.text())).not.toContain('关键设计决策')
    expect(wrapper.text()).toContain('Changelog')
    expect(wrapper.text()).toContain('Next')
    expect(wrapper.text()).toContain('增加载荷工况')
  })

  it('404 slug 渲染专门页面态', async () => {
    api.getPublicProjectBySlug.mockReset()
    api.getPublicProjectBySlug.mockRejectedValue({ response: { status: 404 } })
    const wrapper = mountPage('ghost')
    await flushPromises()
    expect(wrapper.text()).toContain('没有找到这个项目')
  })

  it('加载失败显示错误态并可重试', async () => {
    api.getPublicProjectBySlug.mockReset()
    api.getPublicProjectBySlug.mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('项目加载失败')
    mockData()
    await wrapper.find('.retry-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.identity h1').text()).toBe('Structure Lab')
  })
})
