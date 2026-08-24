import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const api = vi.hoisted(() => ({ getPublicProjects: vi.fn() }))
const mocks = vi.hoisted(() => ({
  route: { query: {} },
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../src/api', () => ({
  API: { getPublicProjects: (...a: unknown[]) => api.getPublicProjects(...a) },
}))
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}))

import ProjectsPage from '../src/views/ProjectsPage.vue'

const PROJECTS = [
  {
    id: 1,
    name: 'Structure Lab',
    slug: 'structure-lab',
    description: '交互式结构稳定性实验。',
    tag: '实验',
    tech_stack: ['Vue', 'Canvas'],
    status: 'active',
    is_current: true,
    preview_type: 'none',
    preview_data: null,
    link_url: '',
    updated_at: '2026-08-20T00:00:00Z',
  },
  {
    id: 2,
    name: 'Alert Hub',
    slug: 'alert-hub',
    description: '统一告警聚合。',
    tag: '内部工具',
    tech_stack: ['Python'],
    status: 'active',
    is_current: false,
    preview_type: 'none',
    preview_data: null,
    updated_at: '2026-07-01T00:00:00Z',
  },
  {
    id: 3,
    name: 'RAG Playground',
    slug: 'rag-play',
    description: '检索策略对比实验。',
    tag: '实验',
    tech_stack: ['Python', 'LLM'],
    status: 'paused',
    is_current: false,
    preview_type: 'image',
    preview_data: { url: '/img/rag.png' },
    updated_at: '2026-06-01T00:00:00Z',
  },
]

function mockList(list: unknown[]) {
  api.getPublicProjects.mockReset()
  api.getPublicProjects.mockResolvedValue({ data: { data: { list } } })
}

function mountPage() {
  return mount(ProjectsPage, {
    global: { stubs: { 'el-skeleton': { template: '<div class="skel" />' } } },
  })
}

describe('ProjectsPage(P2-B1)', () => {
  beforeEach(() => {
    mocks.push.mockReset()
    mockList(PROJECTS)
  })

  it('is_current 项目独占大区,其余进入轻卡区且不争视觉权重', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.project-copy h2').text()).toBe('Structure Lab')
    expect(wrapper.findAll('.project-card').length).toBe(2)
    // 大区显示状态与最近更新
    expect(wrapper.find('.project-copy .status').text()).toContain('开发中')
    expect(wrapper.find('.section-head .meta').text()).toContain('2026 年 8 月')
  })

  it('无 preview 的当前项目显示规范空态', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.preview-empty').text()).toBe('当前版本暂未开放在线体验')
  })

  it('image preview 渲染 lazy 图片', async () => {
    const withImg = [{ ...PROJECTS[0], preview_type: 'image', preview_data: { url: '/img/a.png' } }]
    mockList(withImg)
    const wrapper = mountPage()
    await flushPromises()
    const img = wrapper.find('.preview-stage img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('loading')).toBe('lazy')
  })

  it('轻卡点击进入详情;卡片显示 tag/技术栈', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const card = wrapper.findAll('.project-card')[0]
    expect(card.find('.tag').text()).toBe('内部工具')
    expect(card.find('.tech').text()).toContain('Python')
    await card.trigger('click')
    expect(mocks.push).toHaveBeenCalledWith('/projects/alert-hub')
  })

  it('空态与错误态', async () => {
    mockList([])
    let wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('项目正在整理中')

    api.getPublicProjects.mockReset()
    api.getPublicProjects.mockRejectedValue(new Error('boom'))
    wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('项目加载失败')
    expect(wrapper.find('.retry-btn').exists()).toBe(true)
  })
})
