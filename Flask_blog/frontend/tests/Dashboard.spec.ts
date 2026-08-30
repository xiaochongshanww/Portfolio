import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import Dashboard from '../src/views/admin/Dashboard.vue'

const api = vi.hoisted(() => ({
  getArticles: vi.fn(),
  getPublicArticles: vi.fn(),
  getUsers: vi.fn(),
  getCommentStats: vi.fn(),
  getPublicTaxonomy: vi.fn(),
  getPublicProjects: vi.fn(),
  getTaxonomyStats: vi.fn(),
}))

vi.mock('../src/api', () => ({
  API: {
    getArticles: (...a: unknown[]) => api.getArticles(...a),
    getPublicArticles: (...a: unknown[]) => api.getPublicArticles(...a),
    getUsers: (...a: unknown[]) => api.getUsers(...a),
    getCommentStats: (...a: unknown[]) => api.getCommentStats(...a),
    getPublicTaxonomy: (...a: unknown[]) => api.getPublicTaxonomy(...a),
    getPublicProjects: (...a: unknown[]) => api.getPublicProjects(...a),
    getTaxonomyStats: (...a: unknown[]) => api.getTaxonomyStats(...a),
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: { template: '<a><slot /></a>' },
}))
vi.mock('../src/stores/user', () => ({
  useUserStore: () => ({
    user: { id: 1, role: 'admin', email: 'a@b.c' },
    isAuthenticated: true,
    canModerateContent: true,
  }),
}))

import { API } from '../src/api'

beforeAll(() => {
  if (typeof (globalThis as any).ResizeObserver === 'undefined') {
    ;(globalThis as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  }
})

const okList = (total = 0, list: unknown[] = []) => ({
  data: { code: 0, data: { list, total } },
})

function mockAll() {
  api.getArticles.mockResolvedValue(okList(3, [
    { id: 1, title: 'RAG 深入', slug: 'rag', status: 'published', created_at: '2026-08-20T00:00:00Z', category: { name: 'AI 工程' } },
  ]))
  api.getPublicArticles.mockResolvedValue(okList(2))
  api.getUsers.mockResolvedValue(okList(1))
  api.getCommentStats.mockResolvedValue({
    data: { code: 0, data: { total: 12, pending: 2, approved: 9, rejected: 1 } },
  })
  api.getPublicTaxonomy.mockResolvedValue({
    data: { code: 0, data: { categories: [{ id: 1, name: 'AI' }] } },
  })
  api.getPublicProjects.mockResolvedValue({
    data: { code: 0, data: { list: [{ id: 1, status: 'active' }, { id: 2, status: 'paused' }] } },
  })
  api.getTaxonomyStats.mockResolvedValue({
    data: { code: 0, data: { categories: [], tags: [], summary: { unused_tags: 3 } } },
  })
}

function mountPage() {
  return mount(Dashboard, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-skeleton': { template: '<div class="skel" />' },
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('Dashboard(2026 Pattern)', () => {
  beforeEach(() => {
    for (const fn of Object.values(api)) fn.mockReset()
    mockAll()
  })

  it('renders metric row with counts from APIs', async () => {
    // 按参数路由:total=3 / pending=1
    api.getArticles.mockImplementation((params: { status?: string }) => {
      if (params?.status === 'pending') return Promise.resolve(okList(1))
      return Promise.resolve(okList(3))
    })
    const wrapper = mountPage()
    await flushPromises()
    const metrics = wrapper.findAll('.metric').map((m) => m.text())
    expect(metrics.length).toBe(4)
    expect(metrics[0]).toContain('文章')
    expect(metrics[0]).toContain('3')
    expect(metrics[0]).toContain('待审核 1')
    expect(metrics[1]).toContain('评论')
    expect(metrics[2]).toContain('专题')
    expect(metrics[3]).toContain('项目')
  })

  it('todo list shows pending review and unused tags with links', async () => {
    // 按参数路由:total=5 / pending=2 / recent list
    api.getArticles.mockImplementation((params: { status?: string; page_size?: number }) => {
      if (params?.status === 'pending') {
        return Promise.resolve(okList(2))
      }
      if (params?.page_size === 5) {
        return Promise.resolve(okList(1, [
          { id: 1, title: 'RAG 深入', slug: 'rag', status: 'published', created_at: '2026-08-20T00:00:00Z' },
        ]))
      }
      return Promise.resolve(okList(5))
    })
    const wrapper = mountPage()
    await flushPromises()
    const todos = wrapper.findAll('.kv-row').map((r) => r.text())
    console.log('TODOS:', JSON.stringify(todos))
    expect(todos.some((t) => t.includes('文章审核'))).toBe(true)
    expect(todos.some((t) => t.includes('2 篇待审核'))).toBe(true)
    expect(todos.some((t) => t.includes('标签清理'))).toBe(true)
  })

  it('single API failure does not break the dashboard', async () => {
    api.getCommentStats.mockRejectedValue(new Error('stats down'))
    api.getPublicTaxonomy.mockRejectedValue(new Error('taxonomy down'))
    const wrapper = mountPage()
    await flushPromises()
    // 评论/专题显示 0/占位,不崩溃
    expect(wrapper.find('.metric-row').exists()).toBe(true)
    expect(wrapper.text()).toContain('专题')
  })
})
