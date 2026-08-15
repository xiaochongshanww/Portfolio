import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import Home from '../src/views/Home.vue'

beforeAll(() => {
  if (typeof (globalThis as any).ResizeObserver === 'undefined') {
    (globalThis as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  }
})

vi.mock('../src/api', () => ({
  API: {
    search: vi.fn(() => Promise.resolve({ data: { data: { list: [] } } })),
    getPublicArticles: vi.fn(() =>
      Promise.resolve({ data: { data: { list: [] } } })
    ),
    getHotArticles: vi.fn(() =>
      Promise.resolve({ data: { data: { list: [] } } })
    ),
    approveArticle: vi.fn(() => Promise.resolve({ data: {} })),
    getPublicTaxonomy: vi.fn(() =>
      Promise.resolve({ data: { data: { categories: [], tags: [] } } })
    ),
    getRootCategories: vi.fn(() =>
      Promise.resolve({ data: { data: { categories: [] } } })
    ),
    getRootTags: vi.fn(() =>
      Promise.resolve({ data: { data: { tags: [] } } })
    ),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { page_size: '10' } }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({
    user: null,
    isAuthenticated: false,
    initAuth: vi.fn(),
  }),
}))

import { API } from '../src/api'

const linkStub = { template: '<a><slot /></a>' }

function mountHome() {
  return mount(Home, {
    global: {
      plugins: [createPinia()],
      stubs: {
        DesktopSidebar: { template: '<div class="stub-sidebar" />' },
        HomeHero: { template: '<div class="stub-hero"><slot /></div>' },
        ArticleCard: { template: '<article class="stub-card" />' },
        HomePagination: { template: '<div class="stub-pagination" />' },
        'el-alert': true,
        'el-button': linkStub,
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-segmented': { template: '<div class="seg" />' },
        'el-skeleton': true,
        'el-tag': { template: '<span class="tag"><slot /></span>' },
        'el-tooltip': { template: '<span><slot /></span>' },
      },
    },
  })
}

describe('Home', () => {
  beforeEach(() => {
    vi.mocked(API.search).mockClear()
    vi.mocked(API.getPublicArticles).mockClear()
  })

  it('renders the home page with mocked empty data', async () => {
    const wrapper = mountHome()
    expect(wrapper.find('.home-view').exists()).toBe(true)
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
    expect(vi.mocked(API.getPublicTaxonomy)).toHaveBeenCalled()
  })

  it('calls taxonomy and articles APIs on mount', async () => {
    const wrapper = mountHome()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getPublicTaxonomy)).toHaveBeenCalled()
    expect(vi.mocked(API.getPublicArticles)).toHaveBeenCalled()
  })
})
