import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import Dashboard from '../src/views/admin/Dashboard.vue'

vi.mock('../src/api', () => ({
  API: {
    getArticles: vi.fn(),
    getPublicArticles: vi.fn(),
    getUsers: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ user: { role: 'admin' }, isAuthenticated: true }),
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

function mountPage() {
  return mount(Dashboard, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot name="header" /><slot /></div>' },
        'el-col': { template: '<div><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-row': { template: '<div><slot /></div>' },
        'el-skeleton': { template: '<div class="skel" />' },
        'v-chart': { template: '<div class="chart" />' },
      },
    },
  })
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.mocked(API.getArticles).mockReset()
    vi.mocked(API.getUsers).mockReset()
  })

  it('loads and renders dashboard', async () => {
    vi.mocked(API.getArticles).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    vi.mocked(API.getUsers).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticles)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
