import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ArticleManagement from '../src/views/admin/ArticleManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getArticles: vi.fn(),
    getCategories: vi.fn(),
    getUsers: vi.fn(),
    getCurrentUser: vi.fn(),
    approveArticle: vi.fn(),
    rejectArticle: vi.fn(),
    deleteArticle: vi.fn(),
    submitArticle: vi.fn(),
    unpublishArticle: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/admin/articles' }),
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: { template: '<a><slot /></a>' },
}))
vi.mock('../src/stores/user', () => ({
  useUserStore: () => ({
    user: { id: 1, role: 'admin', email: 'a@b.c' },
    isAuthenticated: true,
    isAdmin: true,
    canModerateContent: true,
  }),
}))

import { API } from '../src/api'

function mountPage() {
  return mount(ArticleManagement, {
    global: {
      plugins: [createPinia()],
      stubs: {
        // 新表格结构(2026):真渲染 el-table 默认插槽内的列模板
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, title: \'a\', slug: \'a\', status: \'draft\', author_id: 1, views_count: 0 }" /></td>',
        },
        'el-pagination': { template: '<div class="pager" />' },
        'el-dropdown': { template: '<div class="dd"><slot /><slot name="dropdown" /></div>' },
        'el-dropdown-menu': { template: '<div class="ddm"><slot /></div>' },
        'el-dropdown-item': { template: '<div class="ddi"><slot /></div>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-icon': true,
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('ArticleManagement', () => {
  beforeAll(() => {
    if (typeof window.matchMedia === 'undefined') {
      window.matchMedia = ((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as unknown as typeof window.matchMedia
    }
  })

  beforeEach(() => {
    vi.mocked(API.getArticles).mockReset()
    vi.mocked(API.getCategories).mockReset()
  })

  it('loads and renders articles', async () => {
    vi.mocked(API.getArticles).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    vi.mocked(API.getCategories).mockResolvedValue({
      data: { code: 0, data: { categories: [] } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticles)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
